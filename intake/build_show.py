"""Build the show: from the episode's Bandcamp playlist to a Reaper project.

Double-click scripts\\build_show.cmd (or its desktop shortcut), or run:

    python -m intake.build_show
    python -m intake.build_show --link URL --date 3_12_2026 --name "Episode Name"

It asks for whatever isn't given, then:

1. reads the playlist on Bandcamp (in Chrome, as Acquire does), in its order;
2. finds every track in MFYN_Library by artist and title (album to break ties).
   If any track isn't there, it stops and lists them, and copies nothing:
   MFYN only plays music it owns;
3. copies the tracks, tags and all, into a working folder on the desktop named
   like the archive ("3_12_2026- Episode Name"), in Tracks\\, numbered in
   playlist order;
4. writes a Reaper project there (20261203_Episode Name.rpp) with a Voice over
   track, a Music bed track and one track per artist holding that artist's
   songs, placed one after the other in playlist order.

An existing working folder is never overwritten. See docs/02-create-show.md.
"""
import argparse
import datetime
import json
import logging
import re
import shutil
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import mutagen

from . import config, episode, library, reels, runlog

log = logging.getLogger("build_show")

PLAYLIST_URL = re.compile(r"^https://bandcamp\.com/[^/]+/playlist/[^/?#]+")
DATE = re.compile(r"^\s*(\d{1,2})[_\-/. ](\d{1,2})[_\-/. ](\d{4})\s*$")
# Reaper's source type for each audio file type.
SOURCE_TYPES = {".flac": "FLAC", ".mp3": "MP3", ".wav": "WAVE", ".aiff": "WAVE", ".ogg": "VORBIS", ".m4a": "VIDEO"}


@dataclass
class PlaylistTrack:
    number: int
    artist: str
    title: str
    album: str = ""
    url: str = ""


@dataclass
class Match:
    wanted: PlaylistTrack
    path: Path
    length: float


# --- the playlist ----------------------------------------------------------

def parse_playlist(blob):
    """(title, tracks) from the JSON in a Bandcamp playlist page's
    <div id="PlaylistPage" data-blob="...">."""
    data = json.loads(blob) if isinstance(blob, str) else blob
    tracklist = (data.get("appData") or {}).get("tracklist") or {}
    tracks = []
    for i, t in enumerate(tracklist.get("tracks") or [], start=1):
        album = t.get("album") or {}
        tracks.append(PlaylistTrack(i, (t.get("artistName") or "").strip(), (t.get("title") or "").strip(),
                                    (album.get("title") or "").strip(), t.get("url") or ""))
    title = (data.get("appData") or {}).get("title") or tracklist.get("title") or ""
    return title.strip(), tracks


def read_playlist(url):
    """The playlist's title and tracks, read in Chrome (Bandcamp blocks plain scripts)."""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    from .bandcamp import Browser

    browser = Browser(config.APP_DIR)
    try:
        driver = browser._chrome()
        driver.get(url)
        WebDriverWait(driver, 30).until(lambda d: d.find_elements(By.ID, "PlaylistPage"))
        blob = driver.find_element(By.ID, "PlaylistPage").get_attribute("data-blob")
    finally:
        browser.close()
    return parse_playlist(blob)


# --- the library -----------------------------------------------------------

def key(text):
    """Text as compared: accents, case, punctuation and spacing don't count."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    text = text.replace("ø", "o").replace("æ", "ae").replace("ß", "ss")
    return re.sub(r"[\W_]+", "", text)


def library_tracks(library_dir):
    """Every audio file in the library, with its tags. Unfinished downloads
    (".partial - " folders) are skipped."""
    found = []
    for path in sorted(library_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in episode.AUDIO:
            continue
        if any(part.startswith(library.PARTIAL_PREFIX) for part in path.relative_to(library_dir).parts):
            continue
        found.append(reels.read_track(path))
    return found


def match(wanted, tracks):
    """The library file for each playlist track, and the playlist tracks not found."""
    by_song = {}
    for t in tracks:
        by_song.setdefault((key(t.artist), key(t.title)), []).append(t)
    found, missing = [], []
    for w in wanted:
        candidates = by_song.get((key(w.artist), key(w.title)), [])
        if len(candidates) > 1 and w.album:
            same_album = [t for t in candidates if key(t.album) == key(w.album)]
            candidates = same_album or candidates
        if not candidates:
            missing.append(w)
            continue
        best = sorted(candidates, key=lambda t: (t.path.suffix.lower() != ".flac", str(t.path)))[0]
        found.append(Match(w, best.path, length_of(best.path)))
    return found, missing


def length_of(path):
    try:
        audio = mutagen.File(path)
        return float(audio.info.length) if audio and audio.info else 0.0
    except Exception:       # an unreadable file still gets a (short) item in Reaper
        return 0.0


# --- the working folder ----------------------------------------------------

def parse_date(text):
    m = DATE.match(text or "")
    if not m:
        return None
    day, month, year = (int(g) for g in m.groups())
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def folder_name(air_date, name):
    return f"{air_date.day}_{air_date.month}_{air_date.year}- {library.clean(name)}".rstrip("- ")


def file_name(m):
    w = m.wanted
    return f"{w.number:02d} - " + library.clean(f"{w.artist} - {w.title}") + m.path.suffix.lower()


def copy_tracks(matches, tracks_dir):
    tracks_dir.mkdir(parents=True)
    copied = []
    for m in matches:
        target = tracks_dir / file_name(m)
        shutil.copy2(m.path, target)
        copied.append(target)
    return copied


# --- the Reaper project ----------------------------------------------------

def quote(text):
    """An .rpp string value. Reaper quotes with ", ' or ` (whichever isn't in it)."""
    for q in '"\'`':
        if q not in text:
            return f"{q}{text}{q}"
    return '"' + text.replace('"', "'") + '"'


def artist_tracks(matches):
    """Reaper tracks, one per artist in order of first play: [(artist, [matches])]."""
    groups = {}
    for m in matches:
        groups.setdefault(key(m.wanted.artist), (m.wanted.artist, []))[1].append(m)
    return list(groups.values())


def project_text(matches, files):
    """The .rpp: Voice over and Music bed tracks first, then a track per artist
    with their songs placed back to back in playlist order. Files are relative
    to the project, so the folder can move (e.g. into MFYN_Show_Archive)."""
    position, placed = 0.0, {}
    for m, f in zip(matches, files):
        placed[id(m)] = (position, f)
        position += m.length
    lines = ['<REAPER_PROJECT 0.1 "7.0" 0', "  SAMPLERATE 44100 0 0"]
    for name in (config.BUILD_VOICE_TRACK, config.BUILD_BED_TRACK):
        lines += ["  <TRACK", f"    NAME {quote(name)}", "  >"]
    for artist, songs in artist_tracks(matches):
        lines += ["  <TRACK", f"    NAME {quote(artist)}"]
        for m in songs:
            start, f = placed[id(m)]
            lines += [
                "    <ITEM",
                f"      POSITION {start:.6f}",
                f"      LENGTH {m.length:.6f}",
                f"      NAME {quote(f.stem)}",
                f"      <SOURCE {SOURCE_TYPES.get(f.suffix.lower(), 'WAVE')}",
                f"        FILE {quote(str(Path('Tracks') / f.name).replace('/', chr(92)))}",
                "      >",
                "    >",
            ]
        lines.append("  >")
    lines.append(">")
    return "\n".join(lines) + "\n"


# --- the run ---------------------------------------------------------------

def ask_until(ask, question, check):
    while True:
        answer = check(ask(question).strip())
        if answer is not None:
            return answer


def main(argv=None, ask=input, say=print, read=read_playlist):
    return runlog.track("Build Show", lambda run: _main(argv, ask, say, read, run))


def _main(argv, ask, say, read, run):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--link", help="the episode's Bandcamp playlist")
    parser.add_argument("--date", help="the air date, day_month_year (3_12_2026)")
    parser.add_argument("--name", help="the episode name")
    args = parser.parse_args(argv)
    reels.setup_logging(config.BUILD_SHOW_LOG_FILE)

    link = args.link or ask_until(ask, "Bandcamp playlist link: ",
                                  lambda a: a if PLAYLIST_URL.match(a) else say("  That isn't a Bandcamp playlist link."))
    air_date = parse_date(args.date) if args.date else None
    if air_date is None:
        air_date = ask_until(ask, "Air date (day_month_year, e.g. 3_12_2026): ",
                             lambda a: parse_date(a) or say("  Write it as day_month_year, e.g. 3_12_2026."))
    name = (args.name or ask("Episode name: ")).strip()

    if not config.LIBRARY_DIR.is_dir():
        log.error("Library %s not found. Is Google Drive for desktop running?", config.LIBRARY_DIR)
        return 1
    work = config.WORK_DIR / folder_name(air_date, name)
    if work.exists():
        log.error("%s already exists. Rename or move it, then run this again.", work)
        return 1

    say("\nReading the playlist...")
    title, wanted = read(link)
    if not wanted:
        log.error("No tracks found on %s", link)
        return 1
    say(f"{title}: {len(wanted)} track(s). Looking for them in MFYN_Library...")
    matches, missing = match(wanted, library_tracks(config.LIBRARY_DIR))
    if missing:
        log.error("These %d track(s) aren't in MFYN_Library, so nothing was copied:", len(missing))
        for w in missing:
            log.error("  %02d %s - %s%s", w.number, w.artist, w.title, f" ({w.album})" if w.album else "")
        log.error("Buy or add them (Acquire puts purchases in the library), then run this again.")
        run.summary = f"{len(missing)} of {len(wanted)} track(s) not in the library"
        return 1

    files = copy_tracks(matches, work / "Tracks")
    project = work / f"{air_date:%Y%m%d}_{library.clean(name) or 'MFYN'}.rpp"
    project.write_text(project_text(matches, files), encoding="utf-8")
    artists = len(artist_tracks(matches))
    log.info("\nDone: %d track(s) by %d artist(s) in %s", len(files), artists, work)
    log.info("Open %s in Reaper.", project.name)
    run.add(work.name, runlog.OK, f"{len(files)} track(s), {artists} artist track(s)")
    run.summary = f"{work.name}: {len(files)} track(s)"
    return 0


if __name__ == "__main__":
    sys.exit(main())
