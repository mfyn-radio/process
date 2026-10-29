"""Step 2, Create the show: a Bandcamp playlist becomes an episode folder.

Double-click scripts\\create_show.cmd (or its desktop shortcut) and paste the
playlist link, or run:

    python -m intake.create_show LINK                    # then Make Reels
    python -m intake.create_show LINK --date 12_11_2026  # air date (default: today)
    python -m intake.create_show LINK --name "Episode"   # instead of "Normal Show N"
    python -m intake.create_show LINK --no-reels         # stop once the tracks are copied
    python -m intake.create_show LINK --dry-run          # show what would happen, change nothing

See docs/02-create-show.md.
"""
import argparse
import datetime
import logging
import logging.handlers
import re
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

import mutagen

from . import bandcamp, config, episode, library, playlist, reels

log = logging.getLogger("create_show")

# New episodes are named "D_M_YYYY- Normal Show", then "Normal Show 1", "Normal Show 2"…
# until you rename them.
PLACEHOLDER = "Normal Show"
PLACEHOLDER_NAME = re.compile(re.escape(PLACEHOLDER) + r"(?: (\d+))?", re.I)


def norm(text):
    """Text for comparing names: Windows-safe, no punctuation, any case."""
    text = unicodedata.normalize("NFKC", library.clean(text or "")).casefold()
    return " ".join(re.sub(r"[\W_]+", " ", text).split())


def tag_title(path):
    try:
        tags = mutagen.File(path, easy=True) or {}
        return (tags.get("title") or [""])[0]
    except Exception:
        return ""


def audio_in(folder):
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in episode.AUDIO)


def album_folders(library_dir, track):
    """Library folders that could hold the track, best guesses first."""
    folders = [p for p in library_dir.iterdir() if p.is_dir() and not p.name.startswith(library.PARTIAL_PREFIX)]
    artist, album = norm(track.artist), norm(track.album)
    exact = [f for f in folders if album and norm(f.name) == f"{artist} {album}"]
    both = [f for f in folders if album and album in norm(f.name) and artist in norm(f.name)]
    # Compilations are filed under the label or "Various Artists", not the track's artist.
    by_album = [f for f in folders if album and norm(f.name).endswith(album)]
    by_artist = [f for f in folders if norm(f.name).startswith(artist)]
    return list(dict.fromkeys(exact + both + by_album + by_artist))


def find_file(library_dir, track):
    """The track's file in the library, or None."""
    title = norm(track.title)
    # Bandcamp names files "Artist - Album - 01 Title.flac", or "Artist - Title.flac" for a single.
    by_name = re.compile(r"(?:^|.* )(?:\d+ )?" + re.escape(title))
    for folder in album_folders(library_dir, track):
        files = audio_in(folder)
        for path in files:
            if norm(tag_title(path)) == title:
                return path
        for path in files:
            if by_name.fullmatch(norm(path.stem)):
                return path
    return None


def placeholder_number(name):
    match = PLACEHOLDER_NAME.fullmatch(name)
    return None if match is None else int(match.group(1) or 0)


def episode_folder(archive_dir, air_date, name=None):
    """Where the episode goes. Without a name it's the next "Normal Show N",
    or an existing one whose Tracks folder is still empty."""
    if name:
        return archive_dir / f"{air_date.day}_{air_date.month}_{air_date.year}- {library.clean(name)}"
    numbered = [(placeholder_number(e.name), e) for e in episode.all_in(archive_dir)]
    numbered = sorted((n, e) for n, e in numbered if n is not None)
    empty = [e for _, e in numbered if not e.tracks()]
    if empty:
        return empty[-1].folder
    number = numbered[-1][0] + 1 if numbered else 0
    title = PLACEHOLDER if number == 0 else f"{PLACEHOLDER} {number}"
    return archive_dir / f"{air_date.day}_{air_date.month}_{air_date.year}- {title}"


def parse_date(text):
    match = re.fullmatch(r"(\d{1,2})_(\d{1,2})_(\d{4})", text.strip())
    if not match:
        raise argparse.ArgumentTypeError("use day_month_year, e.g. 12_11_2026")
    day, month, year = map(int, match.groups())
    try:
        return datetime.date(year, month, day)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e))


def read_playlist(url, ask=input):
    """The playlist's tracks, read in Create Show's own Chrome profile. If
    Bandcamp won't show it because it's private, you're asked to sign in to
    Bandcamp in that window once; the profile stays signed in after that."""
    with tempfile.TemporaryDirectory(prefix="mfyn-") as tmp:
        browser = bandcamp.Browser(Path(tmp), profile_dir=config.CHROME_PROFILE_DIR)
        try:
            ld_json, blobs, page = browser.read_playlist(url)
            if playlist.is_private(page):
                browser.open(config.BANDCAMP_LOGIN)
                ask("\nThe playlist is private, and this Chrome window isn't signed in to Bandcamp.\n"
                    "Sign in as music_for_your_neighbors in the Chrome window, then press Enter here. ")
                ld_json, blobs, page = browser.read_playlist(url)
        finally:
            browser.close()
    tracks = playlist.parse(ld_json, blobs)
    if not tracks and playlist.is_private(page):
        log.error("Bandcamp still won't show the playlist. Check that the Chrome window was signed in "
                  "as music_for_your_neighbors, the account that owns it, then try again.")
    elif not tracks:
        saved = config.APP_DIR / "playlist-page.html"
        saved.write_text(page, encoding="utf-8")
        log.error("Couldn't find any tracks on the playlist page. A copy of it is in %s", saved)
    return tracks


def setup_logging():
    config.APP_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(config.CREATE_SHOW_LOG_FILE, maxBytes=1 << 20, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(message)s"))
    for handler in (file_handler, console):
        logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


def main(argv=None, ask=input, read=read_playlist):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("link", nargs="?", help="the Bandcamp playlist link (asked for if left out)")
    parser.add_argument("--date", type=parse_date, help="air date as day_month_year (default: today)")
    parser.add_argument("--name", help=f"episode name (default: the next '{PLACEHOLDER} N')")
    parser.add_argument("--no-reels", action="store_true", help="don't go on to Make Reels")
    parser.add_argument("--dry-run", action="store_true", help="don't create or copy anything")
    args = parser.parse_args(argv)
    setup_logging()

    for folder in (config.LIBRARY_DIR, config.SHOW_ARCHIVE_DIR):
        if not folder.is_dir():
            log.error("%s not found. Is Google Drive for desktop running?", folder)
            return 1
    link = (args.link or ask("Paste the Bandcamp playlist link: ")).strip().strip('"')
    if not link:
        return 1

    log.info("Reading the playlist…")
    tracks = read(link, ask)
    if not tracks:
        return 1
    found = {i: find_file(config.LIBRARY_DIR, t) for i, t in enumerate(tracks)}
    print(f"\n{len(tracks)} track(s) on the playlist:")
    for i, track in enumerate(tracks):
        path = found[i]
        print(f"  {i + 1:2}. {track}\n      " + (f"-> {path.parent.name}\\{path.name}" if path else "NOT IN THE LIBRARY"))
    missing = [tracks[i] for i, p in found.items() if p is None]
    if missing:
        log.error("\n%d track(s) aren't in %s. Nothing was created. If an album hasn't been downloaded "
                  "yet, run Acquire (or wait for the hourly run) and try again.", len(missing), config.LIBRARY_DIR)
        for track in missing:
            log.error("  missing: %s", track)
        return 1

    target = episode_folder(config.SHOW_ARCHIVE_DIR, args.date or datetime.date.today(), args.name)
    tracks_dir = target / "Tracks"
    print(f"\nEpisode folder: {target}")
    if args.dry_run:
        return 0
    tracks_dir.mkdir(parents=True, exist_ok=True)
    for path in dict.fromkeys(found.values()):
        copy = tracks_dir / path.name
        if copy.exists() and copy.stat().st_size == path.stat().st_size:
            continue
        shutil.copy2(path, copy)
        log.info("Copied %s", path.name)
    log.info("'%s' is ready with %d track(s).", target.name, len(set(found.values())))

    if args.no_reels:
        return 0
    print("\nStep 3, Make Reels")
    for handler in logging.getLogger().handlers[:]:  # Make Reels sets up its own
        logging.getLogger().removeHandler(handler)
    return reels.main(["--episode", target.name], ask=ask)


if __name__ == "__main__":
    sys.exit(main())
