"""Gmail and Drive clients, authorized as mfyn@ via the refresh token in GitHub secrets."""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
]


def _credentials():
    return Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )


def gmail():
    return build("gmail", "v1", credentials=_credentials(), cache_discovery=False)


def drive():
    return build("drive", "v3", credentials=_credentials(), cache_discovery=False)
