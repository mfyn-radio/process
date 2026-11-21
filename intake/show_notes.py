"""Step 2c, Show notes: the facts the show notes start from.

The /show-prep skill (.claude/skills/show-prep) runs this, makes sure each
artist has been researched (the /research skill), and writes "Show Notes.md"
in the episode folder. It only reads: the episode's tracks, the MFYN Artists
sheet, and whether each artist has a research file yet.

    python -m intake.show_notes                   # the newest episode in MFYN_Show_Archive
    python -m intake.show_notes --episode NAME    # the episode whose folder name contains NAME
    python -m intake.show_notes --no-sheet        # tags only, without the sheet

Prints the facts as JSON. See docs/02c-show-notes.md.
"""
import argparse
import sys

from . import config, episode, reels, research

NOTES_FILE = "Show Notes.md"


def facts(ep, tracks, cat):
    """The episode's running order, grouped by artist and album, with what the
    sheet knows about each. `cat` may be None: then only the tags are given."""
    artists = {}
    running_order = []
    for i, t in enumerate(tracks, 1):
        running_order.append({"position": i, "artist": t.artist, "title": t.title, "album": t.album,
                              "file": t.path.name})
        artist = artists.setdefault(t.artist, {"name": t.artist, "albums": {}})
        album = artist["albums"].setdefault(t.album, {"title": t.album, "year": t.year, "sheet": {},
                                                      "label": {}, "tracks": []})
        album["tracks"].append({"position": i, "title": t.title, "track_number": t.track_number})

    result = []
    for artist in artists.values():
        entry = {"name": artist["name"], "research_file": str(research.research_file(artist["name"])),
                 "research_exists": research.research_file(artist["name"]).exists(), "sheet": {}}
        if cat:
            entry["sheet"] = research.artist_row(cat, artist["name"])
            for album in artist["albums"].values():
                album["sheet"] = research.release_row(cat, album["title"], artist["name"])
                album["label"] = research.label_row(cat, album["sheet"])
        entry["albums"] = list(artist["albums"].values())
        result.append(entry)

    return {
        "episode": {"name": ep.name, "air_date": ep.air_date.isoformat(), "folder": ep.folder.name},
        "notes_file": str(ep.folder / NOTES_FILE),
        "notes_exist": (ep.folder / NOTES_FILE).exists(),
        "sheet_read": cat is not None,
        "running_order": running_order,
        "artists": result,
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

    cat = None if args.no_sheet else research.open_catalog()
    research.print_json(facts(ep, tracks, cat))
    return 0


if __name__ == "__main__":
    sys.exit(main())
