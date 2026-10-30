"""Step 2c, Show notes: the facts the show notes start from.

The /show-prep skill (.claude/skills/show-prep) runs this, researches the
artists and albums on the web, and writes "Show Notes.md" in the episode folder.
It only reads: the episode's tracks and the MFYN Artists sheet.

    python -m intake.show_notes                   # the newest episode in MFYN_Show_Archive
    python -m intake.show_notes --episode NAME    # the episode whose folder name contains NAME
    python -m intake.show_notes --no-sheet        # tags only, without the sheet

Prints the facts as JSON. See docs/02c-show-notes.md.
"""
import argparse
import json
import sys

from . import catalog, config, episode, google_auth, reels

NOTES_FILE = "Show Notes.md"


def _row(table, record):
    _, row = table.find(record)
    return {k: v for k, v in (row or {}).items() if str(v).strip()}


def _release(cat, album, artist):
    """The Releases row for an album, preferring the one by this artist."""
    rows = [r for r in cat.releases.rows if album and r.get("Album", "").casefold() == album.casefold()]
    row = next((r for r in rows if r.get("Artist", "").casefold() == artist.casefold()), rows[0] if rows else {})
    return {k: v for k, v in row.items() if str(v).strip()}


def facts(ep, tracks, cat):
    """The episode's running order, grouped by artist and album, with what the
    sheet knows about each. `cat` may be None: then only the tags are given."""
    artists = {}
    running_order = []
    for i, t in enumerate(tracks, 1):
        running_order.append({"position": i, "artist": t.artist, "title": t.title, "album": t.album,
                              "file": t.path.name})
        artist = artists.setdefault(t.artist, {"name": t.artist, "sheet": {}, "albums": {}})
        album = artist["albums"].setdefault(t.album, {"title": t.album, "year": t.year, "sheet": {},
                                                      "label": {}, "tracks": []})
        album["tracks"].append({"position": i, "title": t.title, "track_number": t.track_number})

    if cat:
        for artist in artists.values():
            artist["sheet"] = _row(cat.artists, {"Artist": artist["name"]})
            for album in artist["albums"].values():
                album["sheet"] = _release(cat, album["title"], artist["name"])
                label = album["sheet"].get("Label", "")
                if label and label != "Self-released":
                    album["label"] = _row(cat.labels, {"Label": label})

    return {
        "episode": {"name": ep.name, "air_date": ep.air_date.isoformat(), "folder": ep.folder.name},
        "notes_file": str(ep.folder / NOTES_FILE),
        "notes_exist": (ep.folder / NOTES_FILE).exists(),
        "sheet_read": cat is not None,
        "running_order": running_order,
        "artists": [dict(a, albums=list(a["albums"].values())) for a in artists.values()],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", help="the episode whose folder name contains this")
    parser.add_argument("--no-sheet", action="store_true", help="don't read the MFYN Artists sheet")
    args = parser.parse_args(argv)

    if not config.SHOW_ARCHIVE_DIR.is_dir():
        print(f"Show archive {config.SHOW_ARCHIVE_DIR} not found. Is Google Drive for desktop running?",
              file=sys.stderr)
        return 1
    ep = episode.find(config.SHOW_ARCHIVE_DIR, args.episode)
    if ep is None:
        print(f"No episode folder (named like 5_11_2026- Episode Name) found in {config.SHOW_ARCHIVE_DIR}",
              file=sys.stderr)
        return 1
    tracks = [reels.read_track(p) for p in ep.tracks()]
    if not tracks:
        print(f"'{ep.folder.name}' has no audio files in its Tracks folder.", file=sys.stderr)
        return 1

    cat = None
    if not args.no_sheet:
        try:
            cat = catalog.Catalog(google_auth.credentials())
        except (Exception, SystemExit) as e:
            print(f"Couldn't open the {config.ARTISTS_SHEET} sheet ({e}). Going on with the tags only.",
                  file=sys.stderr)

    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(facts(ep, tracks, cat), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
