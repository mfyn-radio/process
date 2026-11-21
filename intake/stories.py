"""Album Stories: featured-album Instagram Stories from albums in MFYN_Library.

Make Episode Content (intake.content) makes one for every artist in an
episode. To make a one-off Story for any album in the library, run:

    python -m intake.stories                          # asks for the album and the featured track
    python -m intake.stories --album NAME --track N   # the album whose folder name contains NAME, track N
    python -m intake.stories --skip-handles           # don't stop to confirm Instagram handles

For a one-off you pick the album and the featured track; the rest is
automatic. See docs/featured-album-story.md.
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
        f"--sketch={config.STORY_SKETCH}", "--run",
        f"input={staging.parent}", f"output={out}", f"seconds={seconds}",
    ]
    log.info("Rendering the Story with Processing. A preview window opens while it works.")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        log.error("Processing exited with code %d", result.returncode)
    return Path(tmp), out / f"{folder.name}_story.mp4", out / f"{folder.name}_story.png"


def details(folder, tracks, featured, cat, seconds, ep):
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
        "episode": {"name": ep.name, "air_date": ep.air_date.isoformat(), "folder": ep.folder.name},
        "library_folder": folder.name,
        "clip_seconds": seconds,
        "made": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def story_path(ep, featured):
    """Where the Story featuring this track goes: MFYN_Stories\\<episode>\\Artist - Title.mp4."""
    return config.STORIES_DIR / ep.folder.name / f"{library.clean(f'{featured.artist} - {featured.title}')}.mp4"


def make(folder, tracks, index, ep, cat, episode_artist=""):
    """Render the Story for album `folder` featuring tracks[index] and file it
    under the episode. `episode_artist` is the artist as the episode's tracks
    name them, so a re-run knows they have their Story. Returns the .mp4, or
    None if it couldn't be made."""
    featured = tracks[index]
    target = story_path(ep, featured)
    if target.exists():     # finished output is final: never overwrite it
        log.info("%s is already in %s; leaving it as it is.", target.name, target.parent)
        return target
    tmp, mp4, png = render(folder, tracks, index, config.STORY_SECONDS)
    try:
        if not mp4.exists():
            log.error("No Story was made for %s. Scroll up for the sketch's own messages.", folder.name)
            return None
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(mp4, target)
        if png.exists():
            shutil.move(png, target.with_suffix(".png"))
        info = details(folder, tracks, featured, cat, config.STORY_SECONDS, ep)
        if episode_artist:
            info["episode_artist"] = episode_artist
        target.with_suffix(".json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    log.info("Made the Album Story %s", target.name)
    return target


# ---------- an episode's Stories (Make Episode Content) ----------
def in_library(track, folders):
    """The library album an episode track comes from, and the track's index
    in it: (folder, album tracks, index), or None if it can't be found.
    Bandcamp names album folders "Artist - Album", so only folders whose name
    holds the album's name are read."""
    if not track.album:
        return None
    album = library.clean(track.album).casefold()
    for folder in (f for f in folders if album in f.name.casefold()):
        tracks = album_tracks(folder)
        for i, t in enumerate(tracks):
            if t.album.casefold() == track.album.casefold() and t.title.casefold() == track.title.casefold():
                return folder, tracks, i
    return None


def for_episode(ep_tracks, folders, rng, done=()):
    """One Album Story per artist in the episode: for each artist, the album
    of a track you played (one of them at random, if you played several), and
    a random track from that album to feature. Returns a list of
    (folder, album tracks, featured index, the artist as the episode names
    them). Artists in `done` (casefolded) already have a Story and are left
    out; so are tracks whose album isn't in the library."""
    by_artist = {}
    for track in ep_tracks:
        by_artist.setdefault(track.artist.casefold(), []).append(track)
    picks = []
    for artist, played in by_artist.items():
        if artist in done:
            log.info("%s already has an Album Story for this episode.", played[0].artist)
            continue
        for track in rng.sample(played, len(played)):
            found = in_library(track, folders)
            if found:
                folder, tracks, _ = found
                picks.append((folder, tracks, rng.randrange(len(tracks)), track.artist))
                break
        else:
            log.warning("%s: no album of theirs from this episode is in %s, so they get no Album Story.",
                        played[0].artist, config.LIBRARY_DIR)
    return picks


def done_artists(ep):
    """The artists (casefolded) of the episode's tracks that already have an
    Album Story in MFYN_Stories, from the Stories' details files."""
    folder = config.STORIES_DIR / ep.folder.name
    done = set()
    for info in (folder.glob("*.json") if folder.is_dir() else []):
        try:
            done.add(json.loads(info.read_text(encoding="utf-8")).get("episode_artist", "").casefold())
        except (OSError, ValueError):
            continue
    return done - {""}


def main(argv=None, ask=input, say=print):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--album", help="the album whose library folder name contains this")
    parser.add_argument("--episode", help="file the Story under the episode whose folder name contains this "
                                         "(default: the newest)")
    parser.add_argument("--track", type=int, help="the featured track's number in the list")
    parser.add_argument("--skip-handles", action="store_true", help="don't stop to confirm Instagram handles")
    args = parser.parse_args(argv)
    reels.setup_logging(config.STORIES_LOG_FILE)

    if not config.LIBRARY_DIR.is_dir():
        log.error("Library %s not found. Is Google Drive for desktop running?", config.LIBRARY_DIR)
        return 1
    if not config.SHOW_ARCHIVE_DIR.is_dir():
        log.error("Show archive %s not found. Is Google Drive for desktop running?", config.SHOW_ARCHIVE_DIR)
        return 1
    ep = episode.find(config.SHOW_ARCHIVE_DIR, args.episode)
    if ep is None:
        log.error("No episode folder (named like 5_11_2026- Episode Name) found in %s", config.SHOW_ARCHIVE_DIR)
        return 1
    folder = pick_album(albums(config.LIBRARY_DIR), args.album, ask, say)
    if folder is None:
        return 0
    tracks = album_tracks(folder)

    say(f"\nEpisode: {ep.folder.name}")
    say(f"{folder.name}")
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

    if story_path(ep, featured).exists():
        log.info("%s.mp4 already exists in %s. Delete it to make it again.", story_path(ep, featured).stem,
                 story_path(ep, featured).parent)
        return 0

    try:
        cat = catalog.Catalog(google_auth.credentials())
    except (Exception, SystemExit) as e:
        log.warning("Couldn't open the %s sheet (%s). The Story is made without handles or the album link.",
                    config.ARTISTS_SHEET, e)
        cat = None
    if cat and not args.skip_handles:
        who = details(folder, tracks, featured, cat, config.STORY_SECONDS, ep)
        say("\nInstagram handles. Only ones that aren't confirmed yet are asked about.")
        handles.confirm(cat.artists, [who["artist"]], "artist", ask=ask)
        if who["label"] and who["label"] != "Self-released":
            handles.confirm(cat.labels, [who["label"]], "label", ask=ask)

    made = make(folder, tracks, index, ep, cat)
    if made is None:
        return 1
    log.info("\nDone: %s (and .png, .json) in %s", made.name, made.parent)
    return 0

if __name__ == "__main__":
    sys.exit(main())
