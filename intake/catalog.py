"""The MFYN Artists Google Sheet: what the library knows about its music.

Tabs:
- Artists: one row per artist, with their Instagram handle (the artist library).
- Releases: one row per album in the library.
- Labels: one row per label, with its Instagram handle.
- Tags: one row per Bandcamp tag per release, for sorting and filtering.

Step 1 fills it in automatically, with Instagram handles marked "Suggested"
or "Not found". Step 3 is where handles are confirmed. The automation only
fills empty cells and adds tags; it never overwrites what someone typed.
"""
import datetime

from googleapiclient.discovery import build

from . import config, release_info, tags
from .table import Table

SUGGESTED, NOT_FOUND = "Suggested", "Not found"

ARTISTS = ["Artist", "Instagram", "Status", "Location", "Tags", "Website", "Other links",
           "Bandcamp page", "Bio", "Added"]
RELEASES = ["Album", "Artist", "Label", "Release date", "Tags", "Album link", "Credits",
            "Purchased", "Library folder", "Added"]
LABELS = ["Label", "Instagram", "Status", "Location", "Website", "Other links", "Bandcamp page", "Added"]
TAGS = ["Tag", "Artist", "Album"]


class Catalog:
    def __init__(self, creds):
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        sheet_id = self._find_or_create(drive, sheets)
        self.artists = Table(sheets, sheet_id, "Artists", ARTISTS, key="Artist", list_fields=("Tags",))
        self.releases = Table(sheets, sheet_id, "Releases", RELEASES, key=("Album", "Artist"), list_fields=("Tags",))
        self.labels = Table(sheets, sheet_id, "Labels", LABELS, key="Label")
        self.tags = Table(sheets, sheet_id, "Tags", TAGS, key=("Tag", "Artist", "Album"))

    @staticmethod
    def _find_or_create(drive, sheets):
        # drive.file only sees files this app created, so a name search is safe.
        q = (f"name = '{config.ARTISTS_SHEET}' and trashed = false "
             "and mimeType = 'application/vnd.google-apps.spreadsheet'")
        found = drive.files().list(q=q, fields="files(id)", pageSize=1).execute()["files"]
        if found:
            return found[0]["id"]
        return sheets.spreadsheets().create(body={
            "properties": {"title": config.ARTISTS_SHEET},
            "sheets": [{"properties": {"title": "Artists", "gridProperties": {"frozenRowCount": 1}}}],
        }, fields="spreadsheetId").execute()["spreadsheetId"]


def _with_status(table, record):
    """Upsert a row with an Instagram handle and keep its Status in step:
    "Suggested" once a handle is filled in, "Not found" while there's none.
    Only these two automatic values are ever replaced."""
    row = table.upsert(record)
    status = row.get("Status", "").strip()
    wanted = SUGGESTED if row.get("Instagram", "").strip() else NOT_FOUND
    if status in ("", SUGGESTED, NOT_FOUND) and status != wanted:
        index, _ = table.find(record)
        table.set(index, {"Status": wanted})


def read_release(browser, folder, album_url=None):
    """What's known about an album folder: its FLAC tags plus its Bandcamp page."""
    album = tags.album_info(folder)
    url = album_url or browser.find_album(album.page, album.title) or album.page
    if url:
        raw = browser.read_page(url)
    else:
        raw = release_info.RawPage(url="")
    release = release_info.parse(raw, album.album_artist, album.title, album.date)
    release.album = release.album or album.title or folder.name
    release.artist = release.artist or album.album_artist or ", ".join(album.artists)
    return album, release


def record(catalog, browser, folder, log, purchased=None, album_url=None):
    album, release = read_release(browser, folder, album_url)
    today = datetime.date.today().isoformat()
    seller = release.seller

    catalog.releases.upsert({
        "Album": release.album, "Artist": release.artist, "Label": release.label,
        "Release date": release.release_date, "Tags": release.tags, "Album link": release.album_link,
        "Credits": release.credits, "Purchased": purchased, "Library folder": folder.name, "Added": today,
    })
    for tag in release.tags:
        catalog.tags.upsert({"Tag": tag, "Artist": release.artist, "Album": release.album})

    single_artist = len(album.artists) <= 1
    for artist in album.artists or [release.artist]:
        row = {"Artist": artist, "Added": today}
        if single_artist:
            row["Tags"] = release.tags
            # The page's sidebar is the artist's own only on a self-release.
            if release.self_released:
                row.update({
                    "Instagram": seller.instagram, "Location": seller.location, "Website": seller.website,
                    "Other links": "\n".join(seller.other_links), "Bandcamp page": seller.page, "Bio": seller.bio,
                })
        _with_status(catalog.artists, row)

    if not release.self_released and release.label:
        _with_status(catalog.labels, {
            "Label": release.label, "Instagram": seller.instagram, "Location": seller.location,
            "Website": seller.website, "Other links": "\n".join(seller.other_links),
            "Bandcamp page": seller.page, "Added": today,
        })
    log.info("'%s': recorded %s (%s), %d tag(s)", folder.name, release.album, release.label, len(release.tags))
