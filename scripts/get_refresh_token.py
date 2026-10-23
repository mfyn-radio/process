"""One-time helper: authorize MFYN Intake as mfyn@ and print the values to store in GitHub.

Usage: py scripts\\get_refresh_token.py path\\to\\client_secret.json
See docs/setup/google-cloud.md.
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
]


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    secrets_path = sys.argv[1]

    flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
    creds = flow.run_local_server(
        port=0,
        login_hint="mfyn@nothingflatdigital.com",
        access_type="offline",
        prompt="consent",  # always return a refresh token, even on re-runs
    )

    with open(secrets_path) as f:
        client = json.load(f)["installed"]

    print()
    print("GOOGLE_CLIENT_ID     =", client["client_id"])
    print("GOOGLE_CLIENT_SECRET =", client["client_secret"])
    print("GOOGLE_REFRESH_TOKEN =", creds.refresh_token)


if __name__ == "__main__":
    main()
