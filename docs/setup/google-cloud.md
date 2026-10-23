# Google Cloud setup

One-time setup that lets the intake automation read the mfyn@ inbox and write
to the `MFYN_Library` folder in mfyn@'s Drive, without anyone signed in.

Takes about 10 minutes. You need a Windows PC with Python installed.

## 1–3. Project, APIs and consent screen (already done)

These already exist in the Google Cloud project **mfyn-library-agent**:

- under the nothingflatdigital.com organization
- **Gmail API** and **Google Drive API** enabled
- consent screen **Audience: Internal**. Only nothingflatdigital.com accounts
  can use it, Google doesn't review it, and its login doesn't expire after
  7 days.

The automation asks for these permissions when you sign in (step 5). An
Internal app doesn't need them listed under **Data Access**.

- `https://www.googleapis.com/auth/gmail.modify`: read purchase emails and add
  the `MFYN/Downloaded` label. It can't delete mail permanently.
- `https://www.googleapis.com/auth/drive`: write album folders into the
  existing `MFYN_Library` folder.

If you ever need to rebuild this from scratch: create the project under the
nothingflatdigital.com organization, enable both APIs, then configure
**Google Auth Platform** (or **APIs & Services → OAuth consent screen**) with
Audience **Internal**.

## 4. Create the client

The client must be a **Desktop app**. The project already has a client named
`mfyn-library-agent`. If it's a Desktop app and you still have its JSON file,
use that file and skip to step 5. Otherwise:

1. In **mfyn-library-agent**, go to **Google Auth Platform → Clients → Create client**.
2. Application type: **Desktop app**. Name: `mfyn-intake-cli`.
3. Download the JSON file straight away, because Google only offers it at
   creation. For example, save it to `C:\Users\<you>\Downloads\client_secret.json`.

Treat this file like a password. Don't put it in the repo (`.gitignore`
already blocks `client_secret*.json`).

## 5. Get the long-lived token

On your PC, from a checkout of this repo:

```
py -m pip install google-auth-oauthlib
py scripts\get_refresh_token.py C:\Users\<you>\Downloads\client_secret.json
```

A browser window opens.

1. Sign in as **mfyn@nothingflatdigital.com**, not admin@.
2. Approve the access.
3. The script prints three values: the client ID, client secret and refresh
   token. Copy them.

## 6. Store the values in GitHub

In the `mfyn-radio/process` repo on GitHub, go to **Settings → Secrets and
variables → Actions → New repository secret** and add:

| Name | Value |
|---|---|
| `GOOGLE_CLIENT_ID` | the client ID |
| `GOOGLE_CLIENT_SECRET` | the client secret |
| `GOOGLE_REFRESH_TOKEN` | the refresh token |

Then delete the downloaded JSON file, or move it somewhere safe.

## If it stops working

The token stays valid until one of these happens:

- the mfyn@ password is changed,
- access is revoked at <https://myaccount.google.com/permissions>,
- it goes unused for 6 months.

To fix it, repeat step 5 and update `GOOGLE_REFRESH_TOKEN` in GitHub.
