"""The MFYN Catalog base on Airtable: what the library knows about its music.
See docs/airtable.md. (Until 21 Nov 2026 this was the MFYN Artists Google
Sheet, which is kept as it was, as a backup.)

Tables:
- Artists: one record per artist, with their Instagram handle (the artist library).
- Releases: one record per album in the library, linked to its artists and label.
- Labels: one record per label, with its Instagram handle, linked to its artists.
- Events: one record per event on the Event Calendar Google calendar, written by the
  Event Calendar automation (docs/event-calendar.md), linked to library artists on the bill.
- Episodes: one record per episode with a YouTube playlist.
- Playlist entries: one record per track of an episode's YouTube playlist proposal,
  for review, written by the YouTube playlist step (docs/youtube-playlist.md).
- Locations: one record per place ("Antwerp, Belgium"), with City and Country,
  linked to the artists, labels, venues and events there.
- Venues: one record per venue, linked to its location and its events.

Tags are a multi-select field on Artists, Releases and Events, so the
sheet's Tags tab (one row per tag) isn't needed.

Step 1 fills it in automatically, with Instagram handles marked "Suggested"
or "Not found". Step 2a is where handles are confirmed. The automation only
fills empty fields and adds tags and links; it never overwrites what someone typed.
"""
import datetime

from googleapiclient.discovery import build

from . import airtable, config, release_info, tags
from .airtable import Link

SUGGESTED, NOT_FOUND = "Suggested", "Not found"
# Set when handles are confirmed in step 2a.
CONFIRMED, NO_INSTAGRAM = "Confirmed", "No Instagram"
STATUSES = [SUGGESTED, NOT_FOUND, CONFIRMED, NO_INSTAGRAM]

ARTISTS = ["Artist", "Instagram", "Status", "Location", "Tags", "Website", "Other links",
           "Bandcamp page", "Bio", "Added"]
RELEASES = ["Album", "Artist", "Label", "Release date", "Tags", "Album link", "Credits",
            "Purchased", "Library folder", "Added"]
LABELS = ["Label", "Instagram", "Status", "Location", "Website", "Other links", "Bandcamp page", "Added"]
TAGS = ["Tag", "Artist", "Album"]   # the old sheet's Tags tab
EPISODES = ["Episode", "Added"]
PLAYLISTS = ["Episode", "#", "Artist", "Track", "Album", "Tier", "Use", "Link", "Video", "Uploader", "Note",
             "Bandcamp", "Playlist", "Added"]
EVENTS = ["Date", "Start", "End", "Title", "Venue", "City", "Country", "Acts", "Tags", "Link", "Post",
          "Location tag", "Event id", "Added"]
LOCATIONS = ["Name", "City", "Country", "Notes"]
VENUES = ["Name", "Notes"]

US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
    "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
    "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi", "missouri",
    "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island",
    "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming"}
DC = {"d.c.", "dc", "district of columbia"}
COUNTRIES = {
    "netherlands", "belgium", "luxembourg", "germany", "france", "united kingdom", "uk", "ireland",
    "spain", "portugal", "italy", "switzerland", "austria", "denmark", "norway", "sweden", "finland",
    "iceland", "poland", "czechia", "czech republic", "slovakia", "hungary", "slovenia", "croatia",
    "serbia", "romania", "bulgaria", "greece", "estonia", "latvia", "lithuania", "ukraine", "turkey",
    "united states", "usa", "us", "canada", "mexico", "brazil", "argentina", "chile", "australia",
    "new zealand", "japan", "china", "south korea", "indonesia", "south africa"}


def place(city="", country=""):
    """A Locations record for a city and country, as {"Name", "City", "Country"}:
    "Antwerp, Belgium". A US state stands for the United States, and a country
    on its own is a location too. None if there's nothing to go on."""
    city, country = (city or "").strip(), (country or "").strip()
    if country.casefold() in US_STATES:
        country = "United States"
    elif country.casefold() in DC:
        city, country = f"{city}, D.C." if city else "Washington, D.C.", "United States"
    if not country and city.casefold() in COUNTRIES:
        city, country = "", city
    if not (city or country):
        return None
    return {"Name": ", ".join(p for p in (city, country) if p), "City": city, "Country": country}


def place_of(location):
    """The Locations record for a location as Bandcamp writes it:
    "Ghent, Belgium", "Austin, Texas", "Washington, D.C.", "Belgium"."""
    city, _, country = (location or "").strip().rpartition(",")
    if not city:
        city, country = country, ""
    return place(city, country)


def located(row):
    found = place_of(row.get("Location"))
    return [found] if found else []


def event_place(row):
    found = place(row.get("City"), row.get("Country"))
    return [found] if found else []


def event_venue(row):
    venue = (row.get("Venue") or "").strip()
    if not venue:
        return []
    return [{"Name": venue, "Linked location": event_place(row)}]


# Catalog attribute: (Airtable table, columns, key, multi-select fields, links, primary field).
# The primary field is the one Airtable shows for a record and links match on.
TABLES = {
    "artists": ("Artists", ARTISTS, "Artist", ("Tags",),
                {"Linked location": Link("locations", create=True, build=located)}, "Artist"),
    "labels": ("Labels", LABELS, "Label", (),
               {"Linked artists": Link("artists"),
                "Linked location": Link("locations", create=True, build=located)}, "Label"),
    "releases": ("Releases", RELEASES, ("Album", "Artist"), ("Tags",),
                 {"Linked artists": Link("artists"), "Linked label": Link("labels")}, "Album"),
    "events": ("Events", EVENTS, "Event id", ("Tags",),
               {"Linked artists": Link("artists", source="Acts", split=True),
                "Linked venue": Link("venues", create=True, build=event_venue),
                "Linked location": Link("locations", create=True, build=event_place)}, "Title"),
    "episodes": ("Episodes", EPISODES, "Episode", (), {}, "Episode"),
    "playlists": ("Playlist entries", PLAYLISTS, ("Episode", "#"), (),
                  {"Linked episode": Link("episodes", source="Episode", create=True),
                   "Linked artist": Link("artists", source="Artist"),
                   "Linked release": Link("releases", source="Album")}, "Track"),
    "locations": ("Locations", LOCATIONS, "Name", (), {}, "Name"),
    "venues": ("Venues", VENUES, "Name", (), {"Linked location": Link("locations", create=True)}, "Name"),
}
# Another field a link may match on: "Rotterdam" with no country finds "Rotterdam, Netherlands".
FALLBACK = {"locations": ("City", "Country")}
# Read when the catalog is opened, as the sheet's tabs were; the rest are read
# on first use, to save API calls.
EAGER = ("artists", "releases", "labels")


class Catalog:
    """The base's tables as attributes: catalog.artists, .releases, .labels,
    .events, .episodes, .playlists, .locations, .venues. `creds` (the Google sign-in) isn't needed
    any more and is ignored."""

    def __init__(self, creds=None, client=None):
        self.client = client or airtable.connect()
        self._tables = {}
        for name in EAGER:
            self.table(name)

    def table(self, name):
        if name not in self._tables:
            title, columns, key, lists, links, primary = TABLES[name]
            self._tables[name] = airtable.AirtableTable(
                self.client, title, columns, key, lists, links, resolve=self.table, primary=primary,
                fallback=FALLBACK.get(name))
        return self._tables[name]

    def __getattr__(self, name):
        if name in TABLES:
            return self.table(name)
        raise AttributeError(name)


class SheetCatalog:
    """The old MFYN Artists Google Sheet, read by the one-off copy to Airtable."""

    def __init__(self, creds):
        drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        self.sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        self.id = find_or_create(drive, self.sheets, config.ARTISTS_SHEET, "Artists")

    def rows(self, tab):
        """The tab's rows as dicts, or [] if there's no such tab. Writes nothing."""
        meta = self.sheets.spreadsheets().get(spreadsheetId=self.id, fields="sheets.properties.title").execute()
        if tab not in [s["properties"]["title"] for s in meta["sheets"]]:
            return []
        values = self.sheets.spreadsheets().values().get(
            spreadsheetId=self.id, range=f"'{tab}'").execute().get("values", [])
        if not values:
            return []
        header = values[0]
        return [dict(zip(header, r + [""] * (len(header) - len(r)))) for r in values[1:]]


def find_or_create(drive, sheets, title, first_tab):
    """The id of the Google Sheet with this title, made (with first_tab) if there isn't one."""
    # drive.file only sees files this app created, so a name search is safe.
    q = (f"name = '{title}' and trashed = false "
         "and mimeType = 'application/vnd.google-apps.spreadsheet'")
    found = drive.files().list(q=q, fields="files(id)", pageSize=1).execute()["files"]
    if found:
        return found[0]["id"]
    return sheets.spreadsheets().create(body={
        "properties": {"title": title},
        "sheets": [{"properties": {"title": first_tab, "gridProperties": {"frozenRowCount": 1}}}],
    }, fields="spreadsheetId").execute()["spreadsheetId"]


def _with_status(table, record):
    """Upsert a row with an Instagram handle and keep its Status in step:
    "Suggested" once a handle is filled in, "Not found" while there's none.
    Only these two automatic values are ever replaced."""
    if table.find(record)[1] is None:   # a new row gets its Status in the same call
        record = dict(record, Status=SUGGESTED if (record.get("Instagram") or "").strip() else NOT_FOUND)
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

    # Artists and the label first, so the release can link to them.
    artists = album.artists or [release.artist]
    single_artist = len(album.artists) <= 1
    for artist in artists:
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

    label = None
    if not release.self_released and release.label:
        label = release.label
        _with_status(catalog.labels, {
            "Label": label, "Instagram": seller.instagram, "Location": seller.location,
            "Website": seller.website, "Other links": "\n".join(seller.other_links),
            "Bandcamp page": seller.page, "Added": today, "Linked artists": artists,
        })

    catalog.releases.upsert({
        "Album": release.album, "Artist": release.artist, "Label": release.label,
        "Release date": release.release_date, "Tags": release.tags, "Album link": release.album_link,
        "Credits": release.credits, "Purchased": purchased, "Library folder": folder.name, "Added": today,
        "Linked artists": artists, "Linked label": [label] if label else [],
    })
    log.info("'%s': recorded %s (%s), %d tag(s)", folder.name, release.album, release.label, len(release.tags))
