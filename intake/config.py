"""Settings for the intake automation. See docs/01-acquire.md."""
import datetime
import os
from pathlib import Path

# Synced to MFYN_Library in mfyn@'s My Drive by Google Drive for desktop.
LIBRARY_DIR = Path(os.environ.get("MFYN_LIBRARY", r"H:\My Drive\MFYN_Library"))

# Google sign-in and logs live outside the repo, on this PC only.
APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "mfyn-intake"
CLIENT_FILE = APP_DIR / "client_secret.json"
TOKEN_FILE = APP_DIR / "token.json"
LOG_FILE = APP_DIR / "acquire.log"

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
