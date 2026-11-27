"""Build the show: from the episode's Bandcamp playlist to a Reaper project.

Double-click scripts\\build_show.cmd (or its desktop shortcut), or run:

    python -m intake.build_show
    python -m intake.build_show --link URL
    python -m intake.build_show --link URL --folder 2026_December

It asks for whatever isn't given, then:

1. reads the playlist on Bandcamp (in Chrome, as Acquire does), in its order;
2. finds every track in MFYN_Library by artist and title (album to break ties).
   If any are missing, it runs Acquire, which downloads new purchases as FLAC
   into the library, and looks again. If some are still missing (not bought
   yet), it stops, lists them and copies nothing: MFYN only plays music it owns;
3. makes the episode's folder in the workspace, named year_Month from the
   playlist's title ("MFYN - December 2026" -> MFYN_Workspace\\2026_December;
   you add the day yourself), and copies the tracks, tags and all, into its
   Tracks folder, numbered in playlist order;
4. writes a Reaper project there (2026_December.rpp) with a Voice over track,
   a Music bed track and one track per artist holding that artist's songs,
   placed one after the other in playlist order. If MFYN_Template.rpp is in
   the workspace, the project starts from it: its master FX and its Voice over
   and Music bed tracks (with their FX) are kept; any other tracks are dropped.

A folder that already has Tracks or a Reaper project is never touched. See docs/02-create-show.md.
"""
import argparse
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

def is_used(folder):
    """A folder Build Show has already filled (or you've started working in)."""
    tracks = folder / "Tracks"
    return any(folder.glob("*.rpp")) or (tracks.is_dir() and any(tracks.iterdir()))


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
MONTH_YEAR = re.compile(r"\b(" + "|".join(MONTHS) + r")\b\D{0,3}(\d{4})\b", re.IGNORECASE)


def month_folder(title):
    """The episode folder's name, year and month, from the playlist's title:
    "MFYN - December 2026" -> "2026_December". None if the title has no month and year."""
    m = MONTH_YEAR.search(title or "")
    if not m:
        return None
    return f"{m.group(2)}_{MONTHS[[x.casefold() for x in MONTHS].index(m.group(1).casefold())]}"


def folder_answer(answer):
    """A folder name typed in: "2026_December" or "december 2026"."""
    answer = answer.strip()
    return month_folder(answer) or (library.clean(answer) if re.fullmatch(r"\d{4}_\w+", answer) else None)


def file_name(m):
    w = m.wanted
    return f"{w.number:02d} - " + library.clean(f"{w.artist} - {w.title}") + m.path.suffix.lower()


def copy_tracks(matches, tracks_dir):
    tracks_dir.mkdir(parents=True, exist_ok=True)
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


def top_level(text):
    """A template project split into its top-level chunks: (header, tracks, rest),
    where header is the opening <REAPER_PROJECT line, tracks are the <TRACK
    blocks (as lists of lines) and rest is every other line inside the project
    (settings, <MASTERFXLIST, ...), the closing ">" left out."""
    lines = text.splitlines()
    header, tracks, rest, depth, current = lines[0], [], [], 0, None
    for line in lines[1:]:
        stripped = line.strip()
        opens, closes = stripped.startswith("<"), stripped == ">"
        if depth == 0 and closes:
            break                       # the project's own closing ">"
        if depth == 0 and opens and stripped[1:].split()[0:1] == ["TRACK"]:
            current = []
            tracks.append(current)
        (current if current is not None else rest).append(line)
        depth += 1 if opens else -1 if closes else 0
        if depth == 0:
            current = None
    return header, tracks, rest


def track_name(block):
    for line in block[1:]:
        if line.strip().startswith("NAME "):
            from .reaper import value
            return value(line.strip()[5:])
    return ""


def project_text(matches, files, template=None):
    """The .rpp: Voice over and Music bed tracks first, then a track per artist
    with their songs placed back to back in playlist order. Files are relative
    to the project, so the folder can move (e.g. into MFYN_Show_Archive).
    A template's settings, master FX and Voice over and Music bed tracks are kept."""
    position, placed = 0.0, {}
    for m, f in zip(matches, files):
        placed[id(m)] = (position, f)
        position += m.length
    if template:
        header, kept, rest = top_level(template)
        kept = {track_name(t).casefold(): t for t in kept}
        lines = [header] + rest
    else:
        kept, lines = {}, ['<REAPER_PROJECT 0.1 "7.0" 0', "  SAMPLERATE 44100 0 0"]
    for name in (config.BUILD_VOICE_TRACK, config.BUILD_BED_TRACK):
        lines += kept.get(name.casefold()) or ["  <TRACK", f"    NAME {quote(name)}", "  >"]
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

def describe(w):
    return f"{w.number:02d} {w.artist} - {w.title}" + (f" ({w.album})" if w.album else "")


def acquire():
    """One Acquire run (new purchases into the library), with its own log file.
    Our log handlers are set aside meanwhile, so nothing prints twice."""
    from . import acquire as acquire_step

    root = logging.getLogger()
    ours = list(root.handlers)
    for h in ours:
        root.removeHandler(h)
    try:
        return acquire_step.main([])
    except SystemExit as e:           # e.g. the Google sign-in needs redoing
        log.error("Acquire stopped: %s", e.code)
        return 1
    finally:
        for h in list(root.handlers):
            root.removeHandler(h)
            h.close()
        for h in ours:
            root.addHandler(h)


def ask_until(ask, question, check):
    while True:
        answer = check(ask(question).strip())
        if answer is not None:
            return answer


def main(argv=None, ask=input, say=print, read=read_playlist, get=None):
    return runlog.track("Build Show", lambda run: _main(argv, ask, say, read, get or acquire, run))


def _main(argv, ask, say, read, acquire, run):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--link", help="the episode's Bandcamp playlist")
    parser.add_argument("--folder", help="the folder to make in the workspace (default: year_Month from the playlist title)")
    parser.add_argument("--no-acquire", action="store_true", help="don't run Acquire for missing tracks")
    args = parser.parse_args(argv)
    reels.setup_logging(config.BUILD_SHOW_LOG_FILE)

    link = args.link or ask_until(ask, "Bandcamp playlist link: ",
                                  lambda a: a if PLAYLIST_URL.match(a) else say("  That isn't a Bandcamp playlist link."))

    if not config.LIBRARY_DIR.is_dir():
        log.error("Library %s not found. Is Google Drive for desktop running?", config.LIBRARY_DIR)
        return 1

    say("\nReading the playlist...")
    title, wanted = read(link)
    if not wanted:
        log.error("No tracks found on %s", link)
        return 1
    name = args.folder or month_folder(title) or ask_until(
        ask, f"The playlist title ({title!r}) has no month. Folder name (e.g. 2026_December): ",
        lambda a: folder_answer(a) or say("  Write it as year_Month, e.g. 2026_December."))
    work = config.WORK_DIR / name
    if work.exists() and is_used(work):
        log.error("%s already has tracks or a Reaper project, so it's left alone. "
                  "Rename it (e.g. to %s_3), then run this again.", work, name)
        return 1
    say(f"{title}: {len(wanted)} track(s). Looking for them in MFYN_Library...")
    matches, missing = match(wanted, library_tracks(config.LIBRARY_DIR))
    if missing and not args.no_acquire:
        say(f"{len(missing)} track(s) aren't in MFYN_Library yet:")
        for w in missing:
            say(f"  {describe(w)}")
        say("Running Acquire to download new purchases...")
        acquire()
        matches, missing = match(wanted, library_tracks(config.LIBRARY_DIR))
    if missing:
        log.error("These %d track(s) aren't in MFYN_Library, so nothing was copied:", len(missing))
        for w in missing:
            log.error("  %s", describe(w))
        log.error("Buy them on Bandcamp, then run this again: it downloads them. (Bought before %s? "
                  "Run python -m intake.acquire --backlog once.)", f"{config.START_DATE:%d %b %Y}")
        run.summary = f"{len(missing)} of {len(wanted)} track(s) not in the library"
        return 1

    work.mkdir(parents=True, exist_ok=True)
    files = copy_tracks(matches, work / "Tracks")
    project = work / f"{work.name}.rpp"
    template = config.BUILD_TEMPLATE.read_text(encoding="utf-8", errors="replace") \
        if config.BUILD_TEMPLATE.is_file() else None
    project.write_text(project_text(matches, files, template), encoding="utf-8")
    if template is None:
        log.info("No %s in the workspace, so the project has no FX yet.", config.BUILD_TEMPLATE.name)
    artists = len(artist_tracks(matches))
    log.info("\nDone: %d track(s) by %d artist(s) in %s", len(files), artists, work)
    log.info("Open %s in Reaper.", project.name)
    run.add(work.name, runlog.OK, f"{len(files)} track(s), {artists} artist track(s)")
    run.summary = f"{work.name}: {len(files)} track(s)"
    return 0


if __name__ == "__main__":
    sys.exit(main())
