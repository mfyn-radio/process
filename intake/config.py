"""Settings for the intake automation. See docs/01-acquire.md."""
import datetime
import os
from pathlib import Path

# Synced to MFYN_Library in mfyn@'s My Drive by Google Drive for desktop.
LIBRARY_DIR = Path(os.environ.get("MFYN_LIBRARY", r"H:\My Drive\MFYN_Library"))

# Step 2 ends with the finished episode here, as "D_M_YYYY- Episode Name\Tracks".
SHOW_ARCHIVE_DIR = Path(os.environ.get("MFYN_SHOW_ARCHIVE", r"H:\My Drive\MFYN_Show_Archive"))
# Make Episode Content (step 2a) writes each episode's video posts here, for review, then Publishing.
# (MFYN_Reels is an archive for now; nothing writes to it.)
POSTS_DIR = Path(os.environ.get("MFYN_POSTS", r"H:\My Drive\MFYN_Posts"))
POST_SECONDS = 30

# The ON AIR video post sketch, in this repo. Processing's command-line runner is found
# automatically; set MFYN_PROCESSING to its full path if it isn't.
POST_SKETCH = Path(__file__).resolve().parent.parent / "processing" / "MFYN_VideoPost_OnAir"

# Make Episode Content writes each episode's Album Stories here, for review, then Publishing.
STORIES_DIR = Path(os.environ.get("MFYN_STORIES", r"H:\My Drive\MFYN_Stories"))
STORY_SECONDS = 30
STORY_SKETCH = Path(__file__).resolve().parent.parent / "processing" / "MFYN_Story_Album"

# The archive cover, made for each episode in MFYN_Show_Archive. Numbering
# starts at No. 3 with the 5 November 2026 episode and counts up by one per
# later episode, in air-date order. Earlier episodes get no automatic cover.
ARCHIVE_SKETCH = Path(__file__).resolve().parent.parent / "processing" / "MFYN_Archive"
ARCHIVE_FIRST_DATE = datetime.date(2026, 11, 5)
ARCHIVE_FIRST_NUMBER = 3
PROCESSING = os.environ.get("MFYN_PROCESSING", "")

# Google sign-in and logs live outside the repo, on this PC only.
APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "mfyn-intake"
CLIENT_FILE = APP_DIR / "client_secret.json"
TOKEN_FILE = APP_DIR / "token.json"
LOG_FILE = APP_DIR / "acquire.log"
REELS_LOG_FILE = APP_DIR / "reels.log"
STORIES_LOG_FILE = APP_DIR / "stories.log"
EVENTS_LOG_FILE = APP_DIR / "events.log"
CONTENT_LOG_FILE = APP_DIR / "content.log"
PLAYLIST_LOG_FILE = APP_DIR / "playlist.log"
BUILD_SHOW_LOG_FILE = APP_DIR / "build_show.log"

# The catalog: artists and their Instagram handles, releases, labels, events and
# playlists, in an Airtable base (docs/airtable.md).
CATALOG = "MFYN Catalog"
# The Airtable personal access token, in a text file next to this repo's code
# (never committed: it's in .gitignore). AIRTABLE_TOKEN overrides it.
AIRTABLE_TOKEN_FILE = Path(os.environ.get(
    "MFYN_AIRTABLE_TOKEN_FILE", Path(__file__).resolve().parent.parent / "airtable_token.txt"))
# The base's id, saved by `python -m intake.airtable_setup`.
AIRTABLE_FILE = APP_DIR / "airtable.json"
# Airtable's free plan allows 1,000 API calls a month, so one run stops after this many.
AIRTABLE_MAX_CALLS = int(os.environ.get("MFYN_AIRTABLE_MAX_CALLS", "150"))
# The Google Sheet the catalog was kept in until 21 Nov 2026, in mfyn@'s Drive. Kept as a
# backup; only the copy to Airtable reads it.
ARTISTS_SHEET = "MFYN Artists"
# What the automations have done, for the status page. Also made on first use.
RUN_LOG_SHEET = "MFYN Run Log"

# Added to a purchase email once it has been handled.
DONE_LABEL = "MFYN/Downloaded"
EXCLUDED_LABEL = "MFYN/Excluded"

# Bandcamp pages whose purchases never go in the library. Matched against
# "Thanks for purchasing from <seller>!" in the receipt, ignoring case.
EXCLUDED_SELLERS = [
    "Music for Your Neighbors - Archive",  # past episodes of the show, not music
]

# Only purchases on or after this date are picked up automatically.
# Older ones need a backlog run (--backlog).
START_DATE = datetime.date(2026, 10, 23)

# Matches Bandcamp purchase receipts, not their release or promo emails.
PURCHASE_QUERY = 'from:noreply@bandcamp.com subject:"Thank you!" "Thanks for purchasing"'

AUDIO_FORMAT = "flac"

# Event Calendar: events from the posts saved to one Instagram collection go on
# a Google calendar of their own. See docs/event-calendar.md.
# The collection's address, as Chrome events it when you open it, e.g.
# https://www.instagram.com/<account>/saved/events/17900000000000000/
INSTAGRAM_COLLECTION_URL = os.environ.get("MFYN_INSTAGRAM_COLLECTION", "")
# Chrome keeps the Instagram sign-in in this profile, separate from Acquire's.
# It's outside AppData because the Microsoft Store Python redirects what it
# writes there, so Chrome wouldn't find the same folder.
INSTAGRAM_PROFILE_DIR = Path.home() / "mfyn-chrome-instagram"
# Posts already read, and the calendar's id.
EVENTS_STATE_FILE = APP_DIR / "events.json"
EVENT_CALENDAR = "Event Calendar"
# "Your artist is playing": events with a library artist on the bill get this
# Google Calendar colour (11 is Tomato, red) and an email to this address.
ALERT_COLOR = "11"
ALERT_EMAIL = os.environ.get("MFYN_ALERT_EMAIL", "mfyn@nothingflatdigital.com")
# Only events in these countries go on the calendar.
EVENT_COUNTRIES = ("Netherlands", "Belgium")
# Times on flyers are local times here (an IANA name, e.g. Europe/Amsterdam).
EVENT_TIMEZONE = os.environ.get("MFYN_TIMEZONE", "Europe/Amsterdam")
# Each run opens at most this many new posts, slowly, so Instagram doesn't
# take Chrome for a bot.
EVENTS_POSTS_PER_RUN = 15
# Flyers are read by Claude Code on the PC (`claude -p`), on MFYN's Claude
# subscription. Empty means Claude Code's own default model; set
# MFYN_CLAUDE_MODEL (e.g. "opus") to choose one.
EVENTS_MODEL = os.environ.get("MFYN_CLAUDE_MODEL", "")

# YouTube playlist (docs/youtube-playlist.md): an episode's running order comes
# from its Reaper project; this Reaper track is the host's voice and is skipped.
REAPER_VOICE_TRACK = "voice"

# Build Show (intake.build_show): each episode gets a folder named YYYY_MM_DD in
# the workspace, and its Reaper project starts from MFYN_Template.rpp there, if
# present. The project gets these two tracks before the artists'; the YouTube
# playlist skips both when it reads the running order.
WORK_DIR = Path(os.environ.get("MFYN_WORK_DIR", r"C:\Users\admin\OneDrive\Desktop\MFYN_Workspace"))
BUILD_TEMPLATE = WORK_DIR / "MFYN_Template.rpp"
BUILD_VOICE_TRACK = "Voice over"
BUILD_BED_TRACK = "Music bed"
# Search results per YouTube search (each search costs 100 of the 10,000 daily quota units).
PLAYLIST_SEARCH_RESULTS = 10
# The playlists are made public, so the Instagram Story link works for everyone.
PLAYLIST_PRIVACY = os.environ.get("MFYN_PLAYLIST_PRIVACY", "public")

# Wishlist (docs/wishlist.md): your public Bandcamp wishlist, with each release's
# tags and location, in a Google Sheet you can filter on your phone.
# The fan page, as https://bandcamp.com/<username>.
BANDCAMP_FAN_PAGE = os.environ.get("MFYN_BANDCAMP_FAN", "https://bandcamp.com/music_for_your_neighbors")
WISHLIST_SHEET = "MFYN Wishlist"
# Album pages already read, so each one is opened only once.
WISHLIST_STATE_FILE = APP_DIR / "wishlist.json"
WISHLIST_LOG_FILE = APP_DIR / "wishlist.log"
# Each run opens at most this many new album pages, a few seconds apart.
WISHLIST_PAGES_PER_RUN = 100
