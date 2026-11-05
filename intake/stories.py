"""Make Album Story: a featured-album Instagram Story from an album in MFYN_Library.

Double-click scripts\\make_story.cmd (or its desktop shortcut), or run:

    python -m intake.stories                          # asks for the album and the featured track
    python -m intake.stories --album NAME --track N   # the album whose folder name contains NAME, track N
    python -m intake.stories --skip-handles           # don't stop to confirm Instagram handles

You pick the album and the featured track; the rest is automatic. See
docs/featured-album-story.md.
"""
import argparse
import datetime
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import catalog, config, episode, google_auth, handles, library, reels

log = logging.getLogger("stories")

IMAGES = (".jpg", ".jpeg", ".png")


# ---------- finding the album and its tracks ----------
def albums(library_dir):
    """Album folders in the library that have audio in them, by name."""
    found = []
    for folder in sorted(p for p in library_dir.iterdir() if p.is_dir()):
        if folder.name.startswith(library.PARTIAL_PREFIX):
            continue
        if any(f.suffix.lower() in episode.AUDIO for f in folder.rglob("*") if f.is_file()):
            found.append(folder)
    return found


def matching(folders, text):
    text = text.strip().casefold()
    return [f for f in folders if text in f.name.casefold()] if text else []


def track_order(track):
    """The order the Story sketch lists tracks in: track number, then file name."""
    digits = "".join(c for c in track.track_number.split("/")[0] if c.isdigit())
    return (int(digits) if digits else 0, track.path.name)


def album_tracks(folder):
    files = [f for f in folder.rglob("*") if f.is_file() and f.suffix.lower() in episode.AUDIO]
    return sorted((reels.read_track(f) for f in files), key=track_order)


def featured_txt(tracks, index):
    """What to write in featured.txt so the sketch features tracks[index]:
    its track number when that's unambiguous, otherwise its position."""
    number = track_order(tracks[index])[0]
    if number and [track_order(t)[0] for t in tracks].count(number) == 1:
        return str(number)
    return str(index + 1)


def choose(options, label, ask, say):
    """Ask for a number from 1 to len(options); returns the index, or None to stop."""
    while True:
        answer = ask(f"{label} [1-{len(options)}, Enter to stop]: ").strip()
        if answer == "":
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        say(f"  Please type a number from 1 to {len(options)}.")


def pick_album(folders, wanted, ask, say):
    while True:
        text = wanted if wanted is not None else ask("\nAlbum (type part of its name, Enter to stop): ")
        wanted = None
        if not text.strip():
            return None
        found = matching(folders, text)
        if len(found) == 1:
            return found[0]
        if not found:
            say(f"  No album in the library matches '{text.strip()}'.")
            continue
        shown = found[:20]
        for i, f in enumerate(shown, 1):
            say(f"  {i:2}. {f.name}")
        if len(found) > len(shown):
            say(f"  ... and {len(found) - len(shown)} more; type more of the name to narrow it down.")
        index = choose(shown, "Which album?", ask, say)
        if index is not None:
            return shown[index]


# ---------- rendering ----------
def render(folder, tracks, featured_index, seconds):
    """Run the Album sketch on a copy of the album. Returns the temporary
    folder (for the caller to delete) and where the .mp4 and .png should be."""
    tmp = tempfile.mkdtemp(prefix="mfyn-story-")
    staging = Path(tmp) / "input" / folder.name
    out = Path(tmp) / "output"
    staging.mkdir(parents=True)
    out.mkdir()
    for t in tracks:
        shutil.copy2(t.path, staging / t.path.name)
    for img in folder.rglob("*"):
        if img.is_file() and img.suffix.lower() in IMAGES and not (staging / img.name).exists():
            shutil.copy2(img, staging / img.name)
    (staging / "featured.txt").write_text(featured_txt(tracks, featured_index), encoding="utf-8")
    cmd = reels.processing_command() + [
        f"--sketch={config.ALBUM_SKETCH}", "--run",
        f"input={staging.parent}", f"output={out}", f"seconds={seconds}",
    ]
    log.info("Rendering the Story with Processing. A preview window opens while it works.")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        log.error("Processing exited with code %d", result.returncode)
    return Path(tmp), out / f"{folder.name}_story.mp4", out / f"{folder.name}_story.png"


def details(folder, tracks, featured, cat, seconds):
    """What Publishing needs for the Story: the link for the sticker, handles,
    credits. Handles are as of now; look them up again before posting."""
    first = tracks[0]
    album = first.album or folder.name
    artist_name = first.artist
    artist, release, label = {}, {}, {}
    if cat:
        release = next((r for r in cat.releases.rows if album and r.get("Album", "").casefold() == album.casefold()), {})
        artist_name = release.get("Artist") or artist_name
        _, artist = cat.artists.find({"Artist": artist_name})
        artist = artist or {}
        if release.get("Label") and release["Label"] != "Self-released":
            _, label = cat.labels.find({"Label": release["Label"]})
            label = label or {}
    return {
        "artist": artist_name,
        "album": album,
        "featured_track": {"number": featured.track_number, "title": featured.title, "file": featured.path.name},
        "year": first.year,
        "label": release.get("Label", ""),
        "release_date": release.get("Release date", ""),
        "album_link": release.get("Album link", ""),
        "tags": release.get("Tags", ""),
        "artist_instagram": artist.get("Instagram", ""),
        "artist_instagram_status": artist.get("Status", ""),
        "label_instagram": label.get("Instagram", ""),
        "label_instagram_status": label.get("Status", ""),
        "library_folder": folder.name,
        "clip_seconds": seconds,
        "made": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def main(argv=None, ask=input, say=print):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--album", help="the album whose library folder name contains this")
    parser.add_argument("--track", type=int, help="the featured track's number in the list")
    parser.add_argument("--skip-handles", action="store_true", help="don't stop to confirm Instagram handles")
    args = parser.parse_args(argv)
    reels.setup_logging(config.STORIES_LOG_FILE)

    if not config.LIBRARY_DIR.is_dir():
        log.error("Library %s not found. Is Google Drive for desktop running?", config.LIBRARY_DIR)
        return 1
    folder = pick_album(albums(config.LIBRARY_DIR), args.album, ask, say)
    if folder is None:
        return 0
    tracks = album_tracks(folder)

    say(f"\n{folder.name}")
    for i, t in enumerate(tracks, 1):
        say(f"  {i:2}. {t.title}")
    if args.track is not None:
        if not 1 <= args.track <= len(tracks):
            log.error("--track %d: the album has %d track(s).", args.track, len(tracks))
            return 1
        index = args.track - 1
    else:
        index = choose(tracks, "Featured track", ask, say)
        if index is None:
            return 0
    featured = tracks[index]

    out_dir = config.STORIES_DIR / folder.name
    name = library.clean(f"{folder.name} - {featured.title}")
    if (out_dir / f"{name}.mp4").exists():
        log.info("%s.mp4 already exists in %s. Delete it to make it again.", name, out_dir)
        return 0

    try:
        cat = catalog.Catalog(google_auth.credentials())
    except (Exception, SystemExit) as e:
        log.warning("Couldn't open the %s sheet (%s). The Story is made without handles or the album link.",
                    config.ARTISTS_SHEET, e)
        cat = None
    if cat and not args.skip_handles:
        who = details(folder, tracks, featured, cat, config.STORY_SECONDS)
        say("\nInstagram handles. Only ones that aren't confirmed yet are asked about.")
        handles.confirm(cat.artists, [who["artist"]], "artist", ask=ask)
        if who["label"] and who["label"] != "Self-released":
            handles.confirm(cat.labels, [who["label"]], "label", ask=ask)

    tmp, mp4, png = render(folder, tracks, index, config.STORY_SECONDS)
    try:
        if not mp4.exists():
            log.error("No Story was made for %s. Scroll up for the sketch's own messages.", folder.name)
            return 1
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(mp4, out_dir / f"{name}.mp4")
        if png.exists():
            shutil.move(png, out_dir / f"{name}.png")
        (out_dir / f"{name}.json").write_text(
            json.dumps(details(folder, tracks, featured, cat, config.STORY_SECONDS), indent=2, ensure_ascii=False),
            encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    log.info("\nDone: %s.mp4 (and .png, .json) in %s", name, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
