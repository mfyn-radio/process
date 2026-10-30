"""Research: what MFYN has found out about each artist, kept so it's never redone.

The /research skill (.claude/skills/research) keeps one file per artist in
MFYN_Research, with a section per album and the sources. This gives it the
facts to start from, and the file to add to. It only reads.

    python -m intake.research --artist NAME     # what the sheet knows, and the artist's research file
    python -m intake.research --artist NAME --no-sheet

Prints JSON. See docs/research.md.
"""
import argparse
import json
import sys

from . import catalog, config, google_auth, library


def research_file(artist):
    """The artist's research file: MFYN_Research\\<Artist>.md."""
    return config.RESEARCH_DIR / f"{library.clean(artist) or '_'}.md"


def _filled(row):
    return {k: v for k, v in (row or {}).items() if str(v).strip()}


def artist_row(cat, artist):
    _, row = cat.artists.find({"Artist": artist})
    return _filled(row)


def release_row(cat, album, artist):
    """The Releases row for an album, preferring the one by this artist."""
    rows = [r for r in cat.releases.rows if album and r.get("Album", "").casefold() == album.casefold()]
    row = next((r for r in rows if r.get("Artist", "").casefold() == artist.casefold()), rows[0] if rows else {})
    return _filled(row)


def label_row(cat, release):
    label = release.get("Label", "")
    if not label or label == "Self-released":
        return {}
    _, row = cat.labels.find({"Label": label})
    return _filled(row)


def artist_facts(cat, artist):
    """What the sheet knows about an artist and all their releases. `cat` may be None."""
    facts = {"name": artist, "research_file": str(research_file(artist)),
             "research_exists": research_file(artist).exists(), "sheet": {}, "releases": []}
    if cat:
        facts["sheet"] = artist_row(cat, artist)
        for row in cat.releases.rows:
            if row.get("Artist", "").casefold() == artist.casefold():
                release = _filled(row)
                facts["releases"].append({"sheet": release, "label": label_row(cat, release)})
    return facts


def open_catalog():
    """The MFYN Artists sheet, or None (with a note on stderr) if it can't be opened."""
    try:
        return catalog.Catalog(google_auth.credentials())
    except (Exception, SystemExit) as e:
        print(f"Couldn't open the {config.ARTISTS_SHEET} sheet ({e}). Going on without it.", file=sys.stderr)
        return None


def print_json(data):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--artist", required=True, help="the artist's name, as in the sheet or the tags")
    parser.add_argument("--no-sheet", action="store_true", help="don't read the MFYN Artists sheet")
    args = parser.parse_args(argv)

    cat = None if args.no_sheet else open_catalog()
    print_json(dict(artist_facts(cat, args.artist), sheet_read=cat is not None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
