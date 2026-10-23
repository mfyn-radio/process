import json
import logging
import shutil
from pathlib import Path

from mutagen.flac import FLAC

from intake import catalog, release_info
from intake.table import Table, merge

BLANK = Path(__file__).parent / "blank.flac"


def album_folder(tmp_path, artists, title="Album", page="https://seller.bandcamp.com"):
    """An album folder of tagged FLACs, like Bandcamp's."""
    folder = tmp_path / title
    folder.mkdir()
    for i, artist in enumerate(artists, 1):
        path = folder / f"{i:02} track.flac"
        shutil.copy(BLANK, path)
        tags = FLAC(path)
        tags["artist"], tags["album"], tags["date"] = artist, title, "2026"
        tags["comment"] = f"Visit {page}"
        tags.save()
    return folder


def ld(album, artist, seller, **extra):
    return json.dumps({
        "@type": "MusicAlbum", "@id": f"https://seller.bandcamp.com/album/{album.lower()}",
        "name": album, "byArtist": {"name": artist},
        "publisher": {"@id": "https://seller.bandcamp.com", "name": seller,
                      "foundingLocation": {"name": "Brooklyn, New York"}, "description": "Their bio."},
        "datePublished": "30 Oct 2026 00:00:00 GMT", "keywords": ["ambient", "drone", "Brooklyn"],
        "creditText": "Mastered by someone", **extra,
    })


class MemoryTable(Table):
    """A Table kept in memory instead of a Google Sheet."""

    def __init__(self, columns, key, list_fields=(), rows=()):
        self.tab, self.columns, self.list_fields = "t", columns, list_fields
        self.key = key if isinstance(key, tuple) else (key,)
        self.header = list(columns)
        self.rows = [dict({c: "" for c in columns}, **r) for r in rows]

    def _append_row(self, values):
        pass

    def _write_cells(self, data):
        pass


class MemoryCatalog:
    def __init__(self, artists=()):
        self.artists = MemoryTable(catalog.ARTISTS, "Artist", ("Tags",), artists)
        self.releases = MemoryTable(catalog.RELEASES, ("Album", "Artist"), ("Tags",))
        self.labels = MemoryTable(catalog.LABELS, "Label")
        self.tags = MemoryTable(catalog.TAGS, ("Tag", "Artist", "Album"))


class FakeBrowser:
    def __init__(self, page):
        self.page = page
        self.visited = []

    def find_album(self, seller_page, title):
        return f"https://seller.bandcamp.com/album/{title.lower()}"

    def read_page(self, url):
        self.visited.append(url)
        return self.page


def page(ld_json, links=()):
    return release_info.RawPage(
        url="https://seller.bandcamp.com/album/x", ld_json=[ld_json],
        seller_links=list(links) or ["https://instagram.com/seller", "https://seller.net",
                                     "https://open.spotify.com/a", "https://soundcloud.com/seller"],
    )


def test_merge_only_fills_empty_cells_and_adds_tags():
    existing = {"Artist": "A", "Instagram": "@mine", "Location": "", "Tags": "ambient, Drone"}
    changes = merge(existing, {"Instagram": "@scraped", "Location": "Berlin", "Tags": ["drone", "noise"]},
                    list_fields=("Tags",))
    assert changes == {"Location": "Berlin", "Tags": "ambient, Drone, noise"}


def test_self_released_album_fills_artist(tmp_path):
    cat = MemoryCatalog()
    folder = album_folder(tmp_path, ["Solo", "Solo"], title="Bites")
    catalog.record(cat, FakeBrowser(page(ld("Bites", "Solo", "Solo"))), folder, logging.getLogger(),
                   purchased="2026-10-23")

    [artist] = cat.artists.rows
    assert artist["Instagram"] == "@seller" and artist["Status"] == "Suggested"
    assert artist["Location"] == "Brooklyn, New York" and artist["Bio"] == "Their bio."
    assert artist["Website"] == "https://seller.net"
    assert artist["Other links"] == "https://soundcloud.com/seller"   # no Spotify
    assert artist["Tags"] == "ambient, drone, Brooklyn"

    [release] = cat.releases.rows
    assert (release["Album"], release["Artist"], release["Label"]) == ("Bites", "Solo", "Self-released")
    assert release["Release date"] == "2026-10-30" and release["Purchased"] == "2026-10-23"
    assert release["Library folder"] == "Bites" and release["Credits"] == "Mastered by someone"
    assert [r["Tag"] for r in cat.tags.rows] == ["ambient", "drone", "Brooklyn"]
    assert cat.labels.rows == []


def test_label_release_puts_instagram_on_the_label(tmp_path):
    cat = MemoryCatalog()
    folder = album_folder(tmp_path, ["Steven Hess + Rutger Zuydervelt"], title="Reconstruct")
    catalog.record(cat, FakeBrowser(page(ld("Reconstruct", "Steven Hess + Rutger Zuydervelt", "Room40"))),
                   folder, logging.getLogger())

    [artist] = cat.artists.rows
    assert artist["Instagram"] == "" and artist["Status"] == "Not found"
    assert artist["Bio"] == ""   # the sidebar is the label's, not the artist's
    assert artist["Tags"] == "ambient, drone, Brooklyn"
    [label] = cat.labels.rows
    assert (label["Label"], label["Instagram"], label["Status"]) == ("Room40", "@seller", "Suggested")
    assert cat.releases.rows[0]["Label"] == "Room40"


def test_compilation_adds_each_artist_without_details(tmp_path):
    cat = MemoryCatalog(artists=[{"Artist": "Known", "Instagram": "@known", "Status": "Confirmed"}])
    folder = album_folder(tmp_path, ["Known", "New One"], title="Comp")
    catalog.record(cat, FakeBrowser(page(ld("Comp", "Various Artists", "Some Label"))), folder,
                   logging.getLogger())

    rows = {r["Artist"]: r for r in cat.artists.rows}
    assert rows["Known"]["Instagram"] == "@known" and rows["Known"]["Status"] == "Confirmed"
    assert rows["New One"]["Status"] == "Not found" and rows["New One"]["Tags"] == ""


def test_typed_values_survive_a_second_album(tmp_path):
    cat = MemoryCatalog(artists=[{"Artist": "Solo", "Instagram": "@real", "Status": "Confirmed",
                                  "Bio": "My own note", "Tags": "favourite"}])
    folder = album_folder(tmp_path, ["Solo"], title="Second")
    catalog.record(cat, FakeBrowser(page(ld("Second", "Solo", "Solo"))), folder, logging.getLogger())

    [artist] = cat.artists.rows
    assert (artist["Instagram"], artist["Status"], artist["Bio"]) == ("@real", "Confirmed", "My own note")
    assert artist["Tags"] == "favourite, ambient, drone, Brooklyn"
    assert artist["Location"] == "Brooklyn, New York"   # was empty, so it's filled


def test_page_without_structured_data_uses_the_sidebar(tmp_path):
    raw = release_info.RawPage(
        url="https://seller.bandcamp.com/album/x", seller_name="Solo", location="Leeds, UK",
        bio="Sidebar bio", tags=["noise"], seller_links=["https://instagram.com/solo_"],
    )
    release = release_info.parse(raw, fallback_artist="Solo", fallback_album="X")
    assert release.label == "Self-released" and release.tags == ["noise"]
    assert (release.seller.location, release.seller.bio, release.seller.instagram) == ("Leeds, UK", "Sidebar bio", "@solo_")


def test_column_letter():
    from intake.table import column_letter
    assert [column_letter(i) for i in (0, 4, 25, 26, 27)] == ["A", "E", "Z", "AA", "AB"]
