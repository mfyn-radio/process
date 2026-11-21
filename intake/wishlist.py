"""Wishlist: your public Bandcamp wishlist in a Google Sheet, with each
release's tags and location, so it can be filtered on a phone.
See docs/wishlist.md.

Chrome opens the wishlist on the fan page, then each new item's album page
(once; what it read is kept in wishlist.json). The Wishlist tab is rewritten
on every run, newest first. Only the Notes column is yours: what you type
there stays with its release.
"""
import argparse
import datetime
import json
import logging
import logging.handlers
import random
import time

from googleapiclient.discovery import build

from . import config, google_auth, release_info, runlog
from .bandcamp import Browser
from .catalog import find_or_create, place_of

log = logging.getLogger("wishlist")

TAB = "Wishlist"
COLUMNS = ["Artist", "Release", "Tags", "City", "Country", "Location", "Wishlisted", "Bandcamp link", "Notes"]
YOURS = ["Notes"]   # kept from the sheet on each rewrite


def pause(low=2.0, high=5.0):
    time.sleep(random.uniform(low, high))


def wishlisted(value):
    """Bandcamp's "21 Nov 2026 14:23:11 GMT" as "2026-11-21"."""
    try:
        return datetime.datetime.strptime((value or "").strip(), "%d %b %Y %H:%M:%S %Z").date().isoformat()
    except ValueError:
        return ""


def items(raw_items):
    """Bandcamp's wishlist items as {Artist, Release, Wishlisted, Bandcamp link}, newest
    first and without duplicates."""
    seen, found = set(), []
    for item in raw_items:
        link = (item.get("item_url") or "").split("?")[0]
        if not link or link in seen:
            continue
        seen.add(link)
        found.append({
            "Artist": (item.get("band_name") or "").strip(),
            "Release": (item.get("item_title") or "").strip(),
            "Wishlisted": wishlisted(item.get("added")),
            "Bandcamp link": link,
        })
    return found


def page_info(raw):
    """What the wishlist keeps from an album page: its tags and location."""
    release = release_info.parse(raw)
    return {"tags": release.tags, "location": release.seller.location or ""}


def row(item, info, yours=None):
    info = info or {}
    place = place_of(info.get("location")) or {}
    return dict(item, **{
        "Tags": ", ".join(info.get("tags") or []),
        "City": place.get("City", ""),
        "Country": place.get("Country", ""),
        "Location": info.get("location", ""),
    }, **{k: (yours or {}).get(k, "") for k in YOURS})


def load_state(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {"pages": {}}


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")


def read_pages(browser, wanted, state, limit):
    """Read up to `limit` album pages not read yet; returns how many were read
    and how many failed."""
    pages = state.setdefault("pages", {})
    todo = [item for item in wanted if item["Bandcamp link"] not in pages][:limit]
    failed = 0
    for n, item in enumerate(todo, 1):
        try:
            info = page_info(browser.read_page(item["Bandcamp link"]))
            info["read"] = datetime.date.today().isoformat()
            pages[item["Bandcamp link"]] = info
            log.info("(%d/%d) %s - %s: %s; %s", n, len(todo), item["Artist"], item["Release"],
                     info["location"] or "no location", ", ".join(info["tags"]) or "no tags")
        except Exception as e:
            failed += 1
            log.warning("(%d/%d) couldn't read %s: %s", n, len(todo), item["Bandcamp link"], e)
        if n < len(todo):
            pause()
    return len(todo) - failed, failed


class Sheet:
    """The Wishlist tab of the MFYN Wishlist Google Sheet."""

    def __init__(self, sheets, sheet_id):
        self.sheets, self.id = sheets, sheet_id

    @classmethod
    def open(cls, creds):
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return cls(sheets, find_or_create(drive, sheets, config.WISHLIST_SHEET, TAB))

    def _values(self):
        return self.sheets.spreadsheets().values()

    def yours(self):
        """{link: {"Notes": ...}} from the rows on the sheet now."""
        rows = self._values().get(spreadsheetId=self.id, range=f"'{TAB}'").execute().get("values", [])
        if not rows or "Bandcamp link" not in rows[0]:
            return {}
        header = rows[0]
        found = {}
        for values in rows[1:]:
            r = dict(zip(header, values + [""] * (len(header) - len(values))))
            if r.get("Bandcamp link"):
                found[r["Bandcamp link"]] = {k: r.get(k, "") for k in YOURS}
        return found

    def write(self, rows):
        values = [COLUMNS] + [[r.get(c, "") for c in COLUMNS] for r in rows]
        self._values().clear(spreadsheetId=self.id, range=f"'{TAB}'").execute()
        self._values().update(spreadsheetId=self.id, range=f"'{TAB}'!A1", valueInputOption="RAW",
                              body={"values": values}).execute()


def setup_logging():
    config.APP_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(config.WISHLIST_LOG_FILE, maxBytes=1 << 20, backupCount=3, encoding="utf-8")
    console = logging.StreamHandler()
    for handler in (file_handler, console):
        handler.setFormatter(fmt)
        logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


def main(argv=None):
    return runlog.track("Wishlist", lambda run: _main(argv, run))


def _main(argv, run):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fan", default=config.BANDCAMP_FAN_PAGE,
                        help="the Bandcamp fan page, https://bandcamp.com/<username> (default: MFYN_BANDCAMP_FAN)")
    parser.add_argument("--pages", type=int, default=config.WISHLIST_PAGES_PER_RUN,
                        help=f"album pages to read this run (default {config.WISHLIST_PAGES_PER_RUN})")
    parser.add_argument("--dry-run", action="store_true", help="read the wishlist but don't write the sheet")
    args = parser.parse_args(argv)
    setup_logging()
    if args.dry_run:
        run.runs = run.last_run = None
    if not args.fan:
        log.error("Set MFYN_BANDCAMP_FAN to your fan page, https://bandcamp.com/<username>. See docs/wishlist.md.")
        return 1

    state = load_state(config.WISHLIST_STATE_FILE)
    browser = Browser(config.APP_DIR)
    try:
        wanted = items(browser.wishlist(args.fan))
        if not wanted:
            log.error("The wishlist on %s is empty, or hidden from visitors. See docs/wishlist.md.", args.fan)
            return 1
        read, failed = read_pages(browser, wanted, state, args.pages)
    finally:
        save_state(config.WISHLIST_STATE_FILE, state)
        browser.close()

    pages = state["pages"]
    left = sum(1 for item in wanted if item["Bandcamp link"] not in pages)
    summary = f"{len(wanted)} on the wishlist, {read} album page(s) read" + (
        f", {left} still to read" if left else "") + (f", {failed} failed" if failed else "")
    if args.dry_run:
        log.info("Dry run: %s. Nothing written.", summary)
        return 0
    sheet = Sheet.open(google_auth.credentials())
    yours = sheet.yours()
    sheet.write([row(item, pages.get(item["Bandcamp link"]), yours.get(item["Bandcamp link"])) for item in wanted])
    log.info("%s sheet updated: %s", config.WISHLIST_SHEET, summary)
    run.summary = summary
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
