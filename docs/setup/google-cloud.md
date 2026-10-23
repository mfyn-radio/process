# Google Cloud setup

One-time setup that lets the intake automation read the mfyn@ inbox and write
to the `MFYN_Library` folder in mfyn@'s Drive, without anyone signed in.

Takes about 15 minutes. You need a Windows PC with Python installed.

## 1. Create the project

1. Go to <https://console.cloud.google.com> and sign in with your
   nothingflatdigital.com admin account.
2. Create a new project named **mfyn-intake**. Under *Organization*, choose
   **nothingflatdigital.com**. This is what makes the "Internal" option in
   step 3 available.

## 2. Turn on the APIs

In the new project, go to **APIs & Services → Library** and enable:

- **Gmail API**
- **Google Drive API**

## 3. Configure the consent screen

Go to **Google Auth Platform** (sometimes shown as **OAuth consent screen**).

1. **Branding:** App name `MFYN Intake`. Use admin@ as the support and
   contact email.
2. **Audience:** choose **Internal**.
   - Only nothingflatdigital.com accounts can use it.
   - Google doesn't need to review it.
   - Its login doesn't expire after 7 days, as it would for an External app
     in testing.
3. **Data Access:** add these scopes:
   - `https://www.googleapis.com/auth/gmail.modify`: read purchase emails
     and add the `MFYN/Downloaded` label. It can't delete mail permanently.
   - `https://www.googleapis.com/auth/drive`: write album folders into the
     existing `MFYN_Library` folder.

## 4. Create the client

1. Go to **Clients → Create client**.
2. Application type: **Desktop app**. Name: `mfyn-intake-cli`.
3. Download the JSON file, for example to
   `C:\Users\<you>\Downloads\client_secret.json`.

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
