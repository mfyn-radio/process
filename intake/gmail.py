"""Gmail access as mfyn@. The first run (--setup) signs in through the browser
and saves a token on this PC; later runs reuse it."""
import shutil

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from . import config

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def setup(client_file):
    """Copy the OAuth client file into place and sign in as mfyn@."""
    config.APP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(client_file, config.CLIENT_FILE)
    flow = InstalledAppFlow.from_client_secrets_file(config.CLIENT_FILE, SCOPES)
    creds = flow.run_local_server(
        port=0,
        login_hint="mfyn@nothingflatdigital.com",
        access_type="offline",
        prompt="consent",  # always return a refresh token, even on re-runs
    )
    config.TOKEN_FILE.write_text(creds.to_json())


def client():
    if not config.TOKEN_FILE.exists():
        raise SystemExit("Not signed in to Gmail yet. Run: python -m intake.acquire --setup <client_secret.json>")
    creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, SCOPES)
    if not creds.valid:
        creds.refresh(Request())
        config.TOKEN_FILE.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def label_id(service, name):
    for label in service.users().labels().list(userId="me").execute()["labels"]:
        if label["name"] == name:
            return label["id"]
    return service.users().labels().create(userId="me", body={"name": name}).execute()["id"]
