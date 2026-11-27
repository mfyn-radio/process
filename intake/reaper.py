"""An episode's running order, read from its Reaper project (.rpp).

The project is the true order: the show notes are written before the show,
and the Tracks folder misses tracks played straight from MFYN_Library. Each
item on a Reaper track is one play; they're put in order by their POSITION
(seconds from the start). The host's voice track ("voice" or "Voice over"),
the "Music bed" track and muted items are skipped,
and a track split into several items in a row counts once.

The file paths saved in the project often no longer work (the episode folder
was renamed, or a track was swapped from .mp3 to .flac), so each file is found
again by its name, in the episode's Tracks folder or the album's folder in
MFYN_Library, and its tags are read. If it can't be found, the artist and
title come from the item's name, "Artist - Album - NN Title".
"""
import re
from dataclasses import dataclass
from pathlib import PureWindowsPath

from . import config, episode, reels

TRACK_NUMBER = re.compile(r"^\d{1,3}[ ._-]+")


@dataclass
class Play:
    position: float
    artist: str
    title: str
    album: str = ""
    source: str = ""       # the item's file name, as saved in the project


def project_for(ep):
    """The episode's Reaper project: the .rpp whose name starts with the air
    date (20261105_...), else the only .rpp in the folder, else None."""
    projects = sorted(p for p in ep.folder.glob("*.rpp") if p.is_file())
    dated = [p for p in projects if p.name.startswith(f"{ep.air_date:%Y%m%d}")]
    if dated:
        return max(dated, key=lambda p: p.stat().st_mtime)
    return projects[0] if len(projects) == 1 else None


def value(rest):
    """The first value on an .rpp line: "quoted", 'quoted', `quoted` or a bare word."""
    rest = rest.strip()
    if rest[:1] in "\"'`":
        end = rest.find(rest[0], 1)
        return rest[1:end] if end > 0 else rest[1:]
    return rest.split()[0] if rest else ""


def items(text):
    """(track name, track muted, item) for every item in the project, where
    item is a dict with position, mute, name and file."""
    stack, track, track_muted, item = [], None, False, None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("<"):
            kind = line[1:].split()[0] if len(line) > 1 else ""
            stack.append(kind)
            if kind == "TRACK":
                track, track_muted = "", False
            elif kind == "ITEM":
                item = {"position": 0.0, "mute": False, "name": "", "file": ""}
            continue
        if line == ">":
            kind = stack.pop() if stack else ""
            if kind == "ITEM" and item is not None:
                yield track, track_muted, item
                item = None
            elif kind == "TRACK":
                track = None
            continue
        if not stack or " " not in line:
            continue
        key, rest = line.split(" ", 1)
        here = stack[-1]
        if here == "TRACK":
            if key == "NAME":
                track = value(rest)
            elif key == "MUTESOLO":
                track_muted = value(rest) == "1"
        elif here == "ITEM" and item is not None:
            if key == "POSITION":
                try:
                    item["position"] = float(value(rest))
                except ValueError:
                    pass
            elif key == "MUTE":
                item["mute"] = value(rest) == "1"
            elif key == "NAME":
                item["name"] = value(rest)
        elif here == "SOURCE" and item is not None and key == "FILE" and not item["file"]:
            item["file"] = value(rest)


def _folders(ep, saved):
    """Where a project's file may be now: the episode's Tracks folder, and the
    library folder named in its saved path."""
    folders = [ep.tracks_dir]
    parent = saved.parent.name
    if parent and parent.casefold() != "tracks":
        folders.append(config.LIBRARY_DIR / parent)
    return [f for f in folders if f.is_dir()]


def find_file(ep, saved_path):
    """The audio file a project item used, found again by name. Reaper item
    names and Windows can cut long names short, so a name that starts the
    other one counts too."""
    saved = PureWindowsPath(saved_path)
    stem = saved.stem.casefold()
    if not stem:
        return None
    for folder in _folders(ep, saved):
        audio = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in episode.AUDIO]
        exact = [p for p in audio if p.stem.casefold() == stem]
        if exact:
            return exact[0]
        close = [p for p in audio if p.stem.casefold().startswith(stem) or stem.startswith(p.stem.casefold())]
        if len(close) == 1:
            return close[0]
    return None


def from_name(name):
    """Artist, album and title from a Bandcamp-style file name:
    "Artist - Album - NN Title". Album names may hold " - " too."""
    stem = name
    if "." in stem and stem.rsplit(".", 1)[1].lower() in {a.lstrip(".") for a in episode.AUDIO}:
        stem = stem.rsplit(".", 1)[0]
    parts = [p.strip() for p in stem.split(" - ")]
    if len(parts) >= 3:
        return parts[0], " - ".join(parts[1:-1]), TRACK_NUMBER.sub("", parts[-1])
    if len(parts) == 2:
        return parts[0], "", TRACK_NUMBER.sub("", parts[1])
    return "", "", TRACK_NUMBER.sub("", stem)


def running_order(ep, project=None):
    """The plays in the episode's project, in the order they aired."""
    project = project or project_for(ep)
    if project is None:
        return []
    plays = []
    skipped = {n.casefold() for n in (config.REAPER_VOICE_TRACK, config.BUILD_VOICE_TRACK, config.BUILD_BED_TRACK)}
    for track, track_muted, item in items(project.read_text(encoding="utf-8", errors="replace")):
        if track is None or track.strip().casefold() in skipped or track_muted or item["mute"]:
            continue
        name = item["name"] or PureWindowsPath(item["file"]).name
        found = find_file(ep, item["file"] or name)
        if found:
            t = reels.read_track(found)
            artist, album, title = t.artist, t.album, t.title
        else:
            artist, album, title = from_name(name)
        if not title:
            continue
        plays.append(Play(item["position"], artist or "Unknown Artist", title, album,
                          PureWindowsPath(item["file"]).name or name))
    return merge_splits(sorted(plays, key=lambda p: p.position))


def merge_splits(plays):
    """One play per track: an item split in Reaper (an edit, a fade) shows up
    as several items of the same track in a row."""
    merged = []
    for play in plays:
        last = merged[-1] if merged else None
        if last and (last.artist.casefold(), last.title.casefold()) == (play.artist.casefold(), play.title.casefold()):
            continue
        merged.append(play)
    return merged
