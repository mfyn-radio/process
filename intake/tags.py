"""Reading FLAC tags from albums in the library."""
import re

from mutagen.flac import FLAC

# Bandcamp writes "Visit https://<page>.bandcamp.com" into each track's comment.
PAGE_URL = re.compile(r"https?://[A-Za-z0-9.-]+\.bandcamp\.com\b")


def first(tags, *keys):
    for key in keys:
        values = tags.get(key)
        if values and values[0].strip():
            return values[0].strip()
    return None


def album_info(folder):
    """The distinct track artists of an album folder, and its Bandcamp page."""
    artists, page = [], None
    for path in sorted(folder.rglob("*.flac")):
        tags = FLAC(path)
        artist = first(tags, "artist", "albumartist")
        if artist and artist not in artists:
            artists.append(artist)
        if page is None:
            match = PAGE_URL.search(first(tags, "comment", "description") or "")
            page = match.group(0) if match else None
    return artists, page
