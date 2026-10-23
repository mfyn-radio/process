# Google Cloud setup

What lets the intake automation on the MFYN PC read and label mail in the
mfyn@ inbox.

**Status:** done. The project and client exist. The sign-in itself happens on
the PC, as part of [setting up step 1](../01-acquire.md#setting-it-up-on-the-pc).

## Project: mfyn-library-agent

- under the nothingflatdigital.com organization
- **Gmail API** enabled (the Google Drive API is enabled too, but no longer
  used: Drive for desktop syncs the library instead)
- consent screen **Audience: Internal**. Only nothingflatdigital.com accounts
  can use it, Google doesn't review it, and its login doesn't expire after
  7 days.

Permission requested at sign-in:

- `https://www.googleapis.com/auth/gmail.modify`: read purchase emails and add
  the `MFYN/…` labels. It can't delete mail permanently.

If you ever need to rebuild this from scratch: create the project under the
nothingflatdigital.com organization, enable the Gmail API, then configure
**Google Auth Platform** (or **APIs & Services → OAuth consent screen**) with
Audience **Internal**.

## Client: mfyn-intake-cli

A **Desktop app** client. Its JSON file is what `--setup` needs:
`client_secret_648160844206-jhea8g49optdpf94bqet5grgbf64915g.apps.googleusercontent.com.json`.
`--setup` keeps a copy in `%APPDATA%\mfyn-intake\`.

Treat this file like a password. Don't put it in the repo (`.gitignore`
already blocks `client_secret*.json`).

If the file is lost: in **mfyn-library-agent**, go to **Google Auth Platform →
Clients → Create client**, choose **Desktop app**, and download the JSON
straight away, because Google only offers it at creation. Leave "use this
client for an AI-powered agent" unticked.

## If it stops working

The saved token stays valid until one of these happens:

- the mfyn@ password is changed,
- access is revoked at <https://myaccount.google.com/permissions>,
- it goes unused for 6 months.

To fix it, run `python -m intake.acquire --setup <client JSON>` on the PC again.
