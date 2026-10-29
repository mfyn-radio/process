"""Episodes in MFYN_Show_Archive, named "D_M_YYYY- Episode Name"."""
import datetime
import re
from dataclasses import dataclass
from pathlib import Path

NAME = re.compile(r"^(\d{1,2})_(\d{1,2})_(\d{4})\s*(?:-\s*(.*))?$")
AUDIO = (".flac", ".mp3", ".wav", ".m4a", ".aiff", ".ogg")  # what the Reel sketch reads


@dataclass
class Episode:
    folder: Path
    air_date: datetime.date
    name: str

    @property
    def tracks_dir(self):
        return self.folder / "Tracks"

    def tracks(self):
        if not self.tracks_dir.is_dir():
            return []
        return sorted(p for p in self.tracks_dir.iterdir() if p.is_file() and p.suffix.lower() in AUDIO)


def parse(folder):
    """The episode a folder holds, or None if its name isn't an episode name."""
    match = NAME.match(folder.name.strip())
    if not match:
        return None
    day, month, year, name = match.groups()
    try:
        air_date = datetime.date(int(year), int(month), int(day))
    except ValueError:
        return None
    return Episode(folder, air_date, (name or "").strip())


def all_in(archive_dir):
    episodes = [parse(p) for p in archive_dir.iterdir() if p.is_dir()]
    return sorted((e for e in episodes if e), key=lambda e: e.air_date)


def find(archive_dir, wanted=None):
    """The newest episode, or the one whose folder name is (or else contains) `wanted`."""
    episodes = all_in(archive_dir)
    exact = [e for e in episodes if wanted and e.folder.name.casefold() == wanted.strip().casefold()]
    if exact:
        return exact[0]
    if wanted:
        episodes = [e for e in episodes if wanted.casefold() in e.folder.name.casefold()]
    return episodes[-1] if episodes else None
