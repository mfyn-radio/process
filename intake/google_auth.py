"""Google sign-in as mfyn@. The first run (--setup) signs in through the
browser and saves a token on this PC; later runs reuse it."""
import json
import shutil

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from . import config

SCOPES = [
    # Read purchase emails and label them.
    "https://www.googleapis.com/auth/gmail.modify",
    # Only the files this app creates: the MFYN Artists sheet.
    "https://www.googleapis.com/auth/drive.file",
]


def setup(client_file):
    """Copy the OAuth client file into place and sign in as mfyn@."""
    config.APP_DIR.mkdir(parents=True, exist_ok=True)
    if str(client_file) != str(config.CLIENT_FILE):
        shutil.copyfile(client_file, config.CLIENT_FILE)
    flow = InstalledAppFlow.from_client_secrets_file(config.CLIENT_FILE, SCOPES)
    creds = flow.run_local_server(
        port=0,
        login_hint="mfyn@nothingflatdigital.com",
        access_type="offline",
        prompt="consent",  # always return a refresh token, even on re-runs
    )
    config.TOKEN_FILE.write_text(creds.to_json())


def credentials():
    setup_hint = f"Run: python -m intake.acquire --setup {config.CLIENT_FILE}"
    if not config.TOKEN_FILE.exists():
        raise SystemExit(f"Not signed in to Google yet. {setup_hint}")
    granted = set(json.loads(config.TOKEN_FILE.read_text()).get("scopes") or [])
    if not set(SCOPES) <= granted:
        raise SystemExit(f"The saved Google sign-in is missing newer permissions. {setup_hint}")
    creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, SCOPES)
    if not creds.valid:
        creds.refresh(Request())
        config.TOKEN_FILE.write_text(creds.to_json())
    return creds
