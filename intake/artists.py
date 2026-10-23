"""The MFYN Artists sheet: one row per artist, with their Instagram handle.

Step 1 adds a row for each new artist, with a handle suggested from their
Bandcamp page and Status "Suggested" (or "Not found"). Step 3 is where the
handle gets confirmed.
"""
import datetime
import re

from googleapiclient.discovery import build

from . import config, tags

TAB = "Artists"
HEADER = ["Artist", "Instagram", "Status", "Bandcamp page", "Added"]
SUGGESTED, NOT_FOUND = "Suggested", "Not found"

# instagram.com paths that aren't accounts.
NOT_ACCOUNTS = {"p", "reel", "reels", "explore", "accounts", "stories", "tv", "bandcamp"}
HANDLE = re.compile(r"instagram\.com/([A-Za-z0-9._]{1,30})", re.I)


def handle_from_links(hrefs):
    """The first Instagram account among a page's links, as @handle."""
    for href in hrefs:
        match = HANDLE.search(href or "")
        if match and match.group(1).lower().strip(".") not in NOT_ACCOUNTS:
            return "@" + match.group(1).strip(".")
    return None


class Sheet:
    def __init__(self, creds):
        self._drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        self._sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        self.id = self._find_or_create()

    def _find_or_create(self):
        # drive.file only sees files this app created, so a name search is safe.
        q = (f"name = '{config.ARTISTS_SHEET}' and trashed = false "
             "and mimeType = 'application/vnd.google-apps.spreadsheet'")
        found = self._drive.files().list(q=q, fields="files(id)", pageSize=1).execute()["files"]
        if found:
            return found[0]["id"]
        sheet_id = self._sheets.spreadsheets().create(body={
            "properties": {"title": config.ARTISTS_SHEET},
            "sheets": [{"properties": {"title": TAB, "gridProperties": {"frozenRowCount": 1}}}],
        }, fields="spreadsheetId").execute()["spreadsheetId"]
        self._sheets.spreadsheets().values().update(
            spreadsheetId=sheet_id, range=f"{TAB}!A1", valueInputOption="RAW", body={"values": [HEADER]},
        ).execute()
        return sheet_id

    def known(self):
        rows = self._sheets.spreadsheets().values().get(
            spreadsheetId=self.id, range=f"{TAB}!A2:A",
        ).execute().get("values", [])
        return {row[0].casefold() for row in rows if row}

    def add(self, artist, handle, page):
        row = [artist, handle or "", SUGGESTED if handle else NOT_FOUND, page or "",
               datetime.date.today().isoformat()]
        self._sheets.spreadsheets().values().append(
            spreadsheetId=self.id, range=f"{TAB}!A1", valueInputOption="RAW",
            insertDataOption="INSERT_ROWS", body={"values": [row]},
        ).execute()


def record(sheet, browser, folder, log):
    """Add any of an album's artists that aren't in the sheet yet."""
    artists, page = tags.album_info(folder)
    known = sheet.known()
    new = [a for a in artists if a.casefold() not in known]
    if not new:
        return
    # The Bandcamp page belongs to whoever sold the album. Only use its
    # Instagram link when the album has a single artist; on a compilation
    # it's the label's, not each artist's.
    handle = None
    if page and len(artists) == 1:
        handle = handle_from_links(browser.links(page))
    for artist in new:
        sheet.add(artist, handle, page)
        log.info("new artist '%s': Instagram %s", artist, handle or "not found")
