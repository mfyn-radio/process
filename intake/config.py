"""Settings for the intake automation. See docs/01-acquire.md."""
import datetime
import os
from pathlib import Path

# Synced to MFYN_Library in mfyn@'s My Drive by Google Drive for desktop.
LIBRARY_DIR = Path(os.environ.get("MFYN_LIBRARY", r"H:\My Drive\MFYN_Library"))

# Step 2 ends with the finished episode here, as "D_M_YYYY- Episode Name\Tracks".
SHOW_ARCHIVE_DIR = Path(os.environ.get("MFYN_SHOW_ARCHIVE", r"H:\My Drive\MFYN_Show_Archive"))
# Step 2a writes each episode's Reels here, for review, then Publishing.
REELS_DIR = Path(os.environ.get("MFYN_REELS", r"H:\My Drive\MFYN_Reels"))
REEL_SECONDS = 30

# The Reel sketch, in this repo. Processing's command-line runner is found
# automatically; set MFYN_PROCESSING to its full path if it isn't.
REEL_SKETCH = Path(__file__).resolve().parent.parent / "processing" / "MFYN_Reel"

# Make Album Story writes each featured-album Story here, for review, then Publishing.
STORIES_DIR = Path(os.environ.get("MFYN_STORIES", r"H:\My Drive\MFYN_Stories"))
STORY_SECONDS = 30
ALBUM_SKETCH = Path(__file__).resolve().parent.parent / "processing" / "MFYN_Album"

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

# Google Sheet of artists and their Instagram handles, in mfyn@'s Drive.
# Created by the automation on first use.
ARTISTS_SHEET = "MFYN Artists"

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

# Show calendar: events from the posts saved to one Instagram collection go on
# a Google calendar of their own. See docs/show-calendar.md.
# The collection's address, as Chrome shows it when you open it, e.g.
# https://www.instagram.com/<account>/saved/shows/17900000000000000/
INSTAGRAM_COLLECTION_URL = os.environ.get("MFYN_INSTAGRAM_COLLECTION", "")
# Chrome keeps the Instagram sign-in in this profile, separate from Acquire's.
INSTAGRAM_PROFILE_DIR = APP_DIR / "chrome-instagram"
# Posts already read, and the calendar's id.
EVENTS_STATE_FILE = APP_DIR / "events.json"
SHOW_CALENDAR = "MFYN Shows"
# Times on flyers are local times here (an IANA name, e.g. Europe/Amsterdam).
SHOW_TIMEZONE = os.environ.get("MFYN_TIMEZONE", "Europe/Amsterdam")
# Each run opens at most this many new posts, slowly, so Instagram doesn't
# take Chrome for a bot.
EVENTS_POSTS_PER_RUN = 15
# Flyers are read by Claude Code on the PC (`claude -p`), on MFYN's Claude
# subscription. Empty means Claude Code's own default model; set
# MFYN_CLAUDE_MODEL (e.g. "opus") to choose one.
EVENTS_MODEL = os.environ.get("MFYN_CLAUDE_MODEL", "")
