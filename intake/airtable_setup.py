"""Set up the MFYN Catalog base on Airtable, and copy the MFYN Artists sheet
into it once. See docs/airtable.md.

    python -m intake.airtable_setup                     # find the base, add missing tables and fields
    python -m intake.airtable_setup --workspace wsp...  # make the base first, if there isn't one
    python -m intake.airtable_setup --copy              # then copy the sheet's rows across
    python -m intake.airtable_setup --copy --dry-run    # only count what would be copied

Running it again is safe: tables, fields and records that are already there
are left alone (records only get their empty fields filled, as always). The
sheet is only read, never changed.
"""
import argparse
import json
import logging
import re
import sys

from . import airtable, catalog, config

TEXT, LONG = "singleLineText", "multilineText"
LONG_FIELDS = {"Bio", "Credits", "Other links", "Note"}
# The setup and the copy use about 30 calls; this leaves room for a retry.
SETUP_CALLS = 300

log = logging.getLogger("airtable_setup")


def field_spec(name, tags=()):
    if name == "Tags":
        # A multi-select needs at least one option to be made; the rest are added as they come.
        return {"name": name, "type": "multipleSelects",
                "options": {"choices": [{"name": t} for t in (sorted(set(tags)) or ["rotterdam"])]}}
    if name == "Status":
        return {"name": name, "type": "singleSelect", "options": {"choices": [{"name": s} for s in catalog.STATUSES]}}
    return {"name": name, "type": LONG if name in LONG_FIELDS else TEXT}


def table_fields(attr, extra=(), tags=()):
    title, columns, _, _, _, primary = catalog.TABLES[attr]
    names = [primary] + [c for c in list(columns) + list(extra) if c != primary]
    return title, [field_spec(n, tags) for n in names]


def find_base(client):
    params = {}
    while True:
        page = client.request("GET", "meta/bases", params)
        for base in page.get("bases", []):
            if base["name"].strip().casefold() == config.CATALOG.casefold():
                return base["id"]
        if not page.get("offset"):
            return None
        params["offset"] = page["offset"]


def ensure_schema(client, workspace=None, extra=None, tags=()):
    """The base's id, with every table and field the catalog needs. `extra`
    holds columns typed by hand in the sheet, {catalog attribute: [names]}."""
    extra = extra or {}
    base = find_base(client)
    if base is None:
        if not workspace:
            raise SystemExit(
                f"There's no '{config.CATALOG}' base yet. Either make an empty base with that name in "
                "Airtable and run this again, or run it with --workspace and the id from the workspace's "
                "address in Airtable (it starts with wsp).")
        first = [table_fields(a, extra.get(a, ()), tags) for a in catalog.TABLES]
        made = client.request("POST", "meta/bases", body={
            "name": config.CATALOG, "workspaceId": workspace,
            "tables": [{"name": t, "fields": f} for t, f in first]})
        base = made["id"]
        log.info("Made the %s base (%s)", config.CATALOG, base)
    client.base = base

    tables = {t["name"]: t for t in client.request("GET", f"meta/bases/{base}/tables")["tables"]}
    for attr in catalog.TABLES:
        title, fields = table_fields(attr, extra.get(attr, ()), tags)
        if title not in tables:
            tables[title] = client.request("POST", f"meta/bases/{base}/tables", body={"name": title, "fields": fields})
            log.info("Added the %s table", title)
            continue
        have = {f["name"] for f in tables[title]["fields"]}
        for spec in fields:
            if spec["name"] not in have:
                made = client.request("POST", f"meta/bases/{base}/tables/{tables[title]['id']}/fields", body=spec)
                tables[title]["fields"].append(made)
                log.info("Added %s to %s", spec["name"], title)

    # Links last, once every table they point at is there. Airtable adds the
    # field going the other way by itself (Artists gets "Releases", and so on).
    tables = {t["name"]: t for t in client.request("GET", f"meta/bases/{base}/tables")["tables"]}
    for attr, (title, _, _, _, links, _) in catalog.TABLES.items():
        have = {f["name"] for f in tables[title]["fields"]}
        for name, link in links.items():
            if name in have:
                continue
            target = tables[catalog.TABLES[link.target][0]]["id"]
            client.request("POST", f"meta/bases/{base}/tables/{tables[title]['id']}/fields", body={
                "name": name, "type": "multipleRecordLinks", "options": {"linkedTableId": target}})
            log.info("Added %s to %s", name, title)

    config.AIRTABLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.AIRTABLE_FILE.write_text(json.dumps({"base": base}))
    return base


SEPARATORS = re.compile(r"\s*(?:,|&|/|\+|\bx\b|\band\b|\bwith\b|\bfeat\.?|\bvs\.?)\s*", re.IGNORECASE)


def release_artists(cat, credit):
    """The Artists records a release's artist credit names: the whole credit,
    or else each name in a split or collaboration that's already an artist."""
    if cat.artists.id_for(credit):
        return [credit]
    return [part for part in SEPARATORS.split(credit or "") if part and cat.artists.id_for(part)]


def as_tags(row):
    if "Tags" in row:
        row = dict(row, Tags=[t.strip() for t in row["Tags"].split(",") if t.strip()])
    return row


SHEET_TABS = {"artists": "Artists", "labels": "Labels", "releases": "Releases", "events": "Events",
              "playlists": "Playlists"}


def read_sheet(sheet):
    rows = {attr: [r for r in sheet.rows(tab) if any(v.strip() for v in r.values())]
            for attr, tab in SHEET_TABS.items()}
    extra = {attr: sorted({c for r in rs for c in r if c and c not in catalog.TABLES[attr][1]})
             for attr, rs in rows.items()}
    tags = {t.strip() for rs in rows.values() for r in rs for t in r.get("Tags", "").split(",") if t.strip()}
    return rows, {a: e for a, e in extra.items() if e}, tags


def copy(cat, rows, extra):
    """Copy the sheet's rows into the base. Returns {table: records}."""
    for attr, names in extra.items():   # columns typed by hand come along too
        cat.table(attr).add_columns(names)
    cat.artists.upsert_many([as_tags(r) for r in rows["artists"]])
    cat.labels.upsert_many(rows["labels"])
    by_label = {}
    releases = []
    for r in rows["releases"]:
        artists = release_artists(cat, r.get("Artist", ""))
        label = r.get("Label", "")
        has_label = bool(label and cat.labels.id_for(label))
        releases.append(dict(as_tags(r), **{"Linked artists": artists,
                                            "Linked label": [label] if has_label else []}))
        if has_label:
            by_label.setdefault(label, []).extend(artists)
    cat.releases.upsert_many(releases)
    cat.labels.upsert_many([{"Label": label, "Linked artists": names} for label, names in by_label.items()])
    cat.events.upsert_many([as_tags(r) for r in rows["events"]])
    if rows["playlists"]:
        cat.playlists.upsert_many(rows["playlists"])
    return {catalog.TABLES[a][0]: len(cat.table(a).rows) for a in ("artists", "labels", "releases", "events",
                                                                   "episodes", "playlists")}


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workspace", help="Airtable workspace id (wsp...), to make the base if there isn't one")
    parser.add_argument("--copy", action="store_true", help=f"copy the {config.ARTISTS_SHEET} sheet into the base")
    parser.add_argument("--dry-run", action="store_true", help="with --copy: only count what would be copied")
    args = parser.parse_args(argv)

    rows = extra = None
    tags = ()
    if args.copy:
        from . import google_auth
        rows, extra, tags = read_sheet(catalog.SheetCatalog(google_auth.credentials()))
        for attr, rs in rows.items():
            log.info("Sheet %s: %d row(s)%s", SHEET_TABS[attr], len(rs),
                     f", extra columns {extra[attr]}" if attr in extra else "")
        if args.dry_run:
            return 0

    client = airtable.Client(airtable.read_token(), max_calls=SETUP_CALLS)
    base = ensure_schema(client, args.workspace, extra, tags)
    log.info("The %s base is %s, saved in %s", config.CATALOG, base, config.AIRTABLE_FILE)
    if args.copy:
        counts = copy(catalog.Catalog(client=client), rows, extra)
        log.info("In the base now: %s", ", ".join(f"{n} {t}" for t, n in counts.items()))
    log.info("Airtable calls used: %d", client.calls)
    return 0


if __name__ == "__main__":
    sys.exit(main())
