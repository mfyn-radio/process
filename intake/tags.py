"""Reading FLAC tags from albums in the library."""
import re
from dataclasses import dataclass, field

from mutagen.flac import FLAC

# Bandcamp writes "Visit https://<page>.bandcamp.com" into each track's comment.
PAGE_URL = re.compile(r"https?://[A-Za-z0-9.-]+\.bandcamp\.com\b")


def first(tags, *keys):
    for key in keys:
        values = tags.get(key)
        if values and values[0].strip():
            return values[0].strip()
    return None


@dataclass
class Album:
    title: str | None = None
    album_artist: str | None = None
    date: str | None = None
    page: str | None = None  # the seller's Bandcamp page
    artists: list = field(default_factory=list)  # distinct track artists, in order


def album_info(folder):
    album = Album()
    for path in sorted(folder.rglob("*.flac")):
        tags = FLAC(path)
        artist = first(tags, "artist", "albumartist")
        if artist and artist not in album.artists:
            album.artists.append(artist)
        album.title = album.title or first(tags, "album")
        album.album_artist = album.album_artist or first(tags, "albumartist")
        album.date = album.date or first(tags, "date")
        if album.page is None:
            match = PAGE_URL.search(first(tags, "comment", "description") or "")
            album.page = match.group(0) if match else None
    if not album.album_artist and len(album.artists) == 1:
        album.album_artist = album.artists[0]
    return album
