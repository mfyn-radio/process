"""Turning a Bandcamp album page into the details the MFYN Artists sheet keeps.

The page's structured data (JSON-LD) is used first; what Bandcamp shows in
the page's sidebar fills any gaps. The sidebar belongs to whoever sells the
album: the artist for a self-release, otherwise the label.
"""
import datetime
import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

SELF_RELEASED = "Self-released"

# instagram.com paths that aren't accounts.
NOT_ACCOUNTS = {"p", "reel", "reels", "explore", "accounts", "stories", "tv", "bandcamp"}
HANDLE = re.compile(r"instagram\.com/([A-Za-z0-9._]{1,30})", re.I)

SOCIAL = ("soundcloud.com", "youtube.com", "youtu.be", "tiktok.com", "twitter.com", "x.com",
          "bsky.app", "facebook.com", "threads.net", "mixcloud.com", "twitch.tv", "linktr.ee")
SKIPPED = ("spotify.com", "music.apple.com", "itunes.apple.com", "instagram.com", "bandcamp.com",
           "bcbits.com", "google.com", "apple.com")


@dataclass
class RawPage:
    """What the browser read off a Bandcamp page."""
    url: str
    ld_json: list = field(default_factory=list)
    seller_links: list = field(default_factory=list)  # the sidebar's links to other sites
    seller_name: str | None = None
    location: str | None = None
    bio: str | None = None
    tags: list = field(default_factory=list)


@dataclass
class Seller:
    name: str | None = None
    page: str | None = None
    location: str | None = None
    bio: str | None = None
    instagram: str | None = None
    website: str | None = None
    other_links: list = field(default_factory=list)


@dataclass
class Release:
    album: str | None = None
    artist: str | None = None
    label: str | None = None
    release_date: str | None = None
    tags: list = field(default_factory=list)
    album_link: str | None = None
    credits: str | None = None
    seller: Seller = field(default_factory=Seller)

    @property
    def self_released(self):
        return self.label == SELF_RELEASED


def handle_from_links(hrefs):
    """The first Instagram account among some links, as @handle."""
    for href in hrefs:
        match = HANDLE.search(href or "")
        if match and match.group(1).lower().strip(".") not in NOT_ACCOUNTS:
            return "@" + match.group(1).strip(".")
    return None


def _host(href):
    host = urlparse(href or "").netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _is(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)


def split_links(hrefs):
    """(website, other links) from a page's links to other sites. Instagram is
    kept separately, and Spotify and Apple Music are left out."""
    website, others = None, []
    for href in hrefs:
        host = _host(href)
        if not host or _is(host, SKIPPED):
            continue
        if _is(host, SOCIAL):
            if href not in others:
                others.append(href)
        elif website is None:
            website = href
    return website, others


def _album_ld(ld_json):
    for text in ld_json:
        try:
            data = json.loads(text)
        except (TypeError, ValueError):
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and item.get("@type") in ("MusicAlbum", "MusicRecording", "Product"):
                return item
    return {}


def _name(value):
    if isinstance(value, dict):
        return (value.get("name") or "").strip() or None
    return (value or "").strip() or None


def _date(value):
    """Bandcamp writes dates like '30 Oct 2026 00:00:00 GMT'."""
    for fmt in ("%d %b %Y %H:%M:%S %Z", "%d %b %Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%B %d, %Y"):
        try:
            return datetime.datetime.strptime(value.strip(), fmt).date().isoformat()
        except (AttributeError, ValueError):
            continue
    return None


def _list(value):
    if isinstance(value, str):
        value = value.split(",")
    return [v.strip() for v in value or [] if isinstance(v, str) and v.strip()]


def parse(raw, fallback_artist=None, fallback_album=None, fallback_date=None):
    ld = _album_ld(raw.ld_json)
    publisher = ld.get("publisher") if isinstance(ld.get("publisher"), dict) else {}
    artist = _name(ld.get("byArtist")) or fallback_artist
    seller_name = _name(publisher) or raw.seller_name
    if seller_name and artist and seller_name.casefold() != artist.casefold():
        label = seller_name
    else:
        label = SELF_RELEASED

    website, others = split_links(raw.seller_links)
    seller = Seller(
        name=seller_name,
        page=publisher.get("@id") or f"{urlparse(raw.url).scheme}://{urlparse(raw.url).netloc}",
        location=_name(publisher.get("foundingLocation")) or raw.location,
        bio=((publisher.get("description") or raw.bio or "").strip()[:2000]) or None,
        instagram=handle_from_links(raw.seller_links),
        website=website,
        other_links=others,
    )
    is_album_page = "/album/" in raw.url or "/track/" in raw.url
    return Release(
        album=_name(ld.get("name")) if is_album_page else fallback_album,
        artist=artist,
        label=label,
        release_date=_date(ld.get("datePublished")) or (fallback_date if not is_album_page else None),
        tags=_list(ld.get("keywords")) or raw.tags,
        album_link=(ld.get("@id") or raw.url) if is_album_page else None,
        credits=(ld.get("creditText") or "").strip()[:2000] or None,
        seller=seller,
    )
