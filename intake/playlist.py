"""Reading the tracks off a Bandcamp playlist page, in playlist order.

The page's structured data (JSON-LD) is used first. If it has no track
list, the data Bandcamp embeds for its own scripts (`data-blob` and similar
attributes) is searched for the longest list of tracks.
"""
import html
import json
from dataclasses import dataclass

TITLE_KEYS = ("track_title", "title", "name", "item_title")
ARTIST_KEYS = ("artist", "band_name", "artist_name", "byArtist", "item_artist")
ALBUM_KEYS = ("album_title", "album", "inAlbum", "album_name")
URL_KEYS = ("track_url", "item_url", "url", "@id")


@dataclass
class PlaylistTrack:
    artist: str
    title: str
    album: str = ""
    url: str = ""

    def __str__(self):
        return f"{self.artist} - {self.title}" + (f" ({self.album})" if self.album else "")


def _text(value):
    if isinstance(value, dict):
        value = value.get("name") or value.get("title")
    return value.strip() if isinstance(value, str) else ""


def _first(item, keys):
    for key in keys:
        if _text(item.get(key)):
            return _text(item.get(key))
    return ""


def _track(item):
    """The track a dict describes, or None if it isn't one."""
    if not isinstance(item, dict):
        return None
    if isinstance(item.get("item"), dict):  # a JSON-LD ListItem
        item = item["item"]
    title, artist = _first(item, TITLE_KEYS), _first(item, ARTIST_KEYS)
    if not (title and artist):
        return None
    url = next((item[k] for k in URL_KEYS if isinstance(item.get(k), str) and "/track/" in item[k]), "")
    return PlaylistTrack(artist=artist, title=title, album=_first(item, ALBUM_KEYS), url=url)


def _from_ld(data):
    """Tracks from a schema.org MusicPlaylist (or anything with a `track` list)."""
    for item in data if isinstance(data, list) else [data]:
        if not isinstance(item, dict):
            continue
        listed = item.get("track")
        if isinstance(listed, dict):
            listed = listed.get("itemListElement")
        if isinstance(listed, list):
            ordered = sorted(listed, key=lambda e: e.get("position", 0) if isinstance(e, dict) else 0)
            tracks = [t for t in map(_track, ordered) if t]
            if tracks:
                return tracks
    return []


def _track_lists(data, path=""):
    """Every list in some JSON whose entries are mostly tracks, with its key path."""
    if isinstance(data, dict):
        for key, value in data.items():
            yield from _track_lists(value, f"{path}/{key}")
    elif isinstance(data, list):
        tracks = [t for t in map(_track, data) if t]
        if tracks and len(tracks) * 2 >= len(data):
            yield path, tracks
        for value in data:
            yield from _track_lists(value, path)


def _from_blob(data):
    lists = list(_track_lists(data))
    if not lists:
        return []
    # A playlist page also carries other lists (recommendations, the owner's
    # collection), so prefer ones that are clearly the playlist's.
    def rank(found):
        path, tracks = found
        return ("playlist" in path.lower(), "track" in path.lower(), len(tracks))
    return max(lists, key=rank)[1]


def _load(text):
    try:
        return json.loads(html.unescape(text))
    except (TypeError, ValueError):
        return None


def is_private(page):
    """Whether Bandcamp refused to show the playlist because it isn't public.
    (It answers with a "Sorry, that something isn't here" page.)"""
    return "private_viewing" in (page or "") or "Endpoints::AccessError" in (page or "")


def parse(ld_json=(), blobs=()):
    """The playlist's tracks, from the page's JSON-LD scripts and embedded data attributes."""
    for text in ld_json:
        tracks = _from_ld(_load(text))
        if tracks:
            return tracks
    for text in blobs:
        tracks = _from_blob(_load(text))
        if tracks:
            return tracks
    return []
