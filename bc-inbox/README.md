# BC Inbox

A private listening queue for MFYN on the phone: the weekly rising-artists
top 10 and Bandcamp "New release from" emails in one list, ranked by region,
with Bandcamp's player inline and two buttons, **Add to wishlist** and
**Not for me**. The plan is the
[BC Inbox project plan](https://claude.ai/artifact/H7X3EsQfuSBWzfmEJf3VDT).

It is a Google Apps Script web app that runs as mfyn@nothingflatdigital.com,
so it can read that account's Gmail and Drive with no server and no cost.
Only mfyn@ can open it (`"access": "MYSELF"`).

## Where it stands

**Milestone 1, the spike.** The page fetches one Bandcamp release
server-side, reads its embed ID and location, and shows the embedded player.
It answers two questions before anything else is built:

1. Does Bandcamp's player play inside an Apps Script page on Android Chrome?
2. Does Bandcamp answer page fetches from Google's servers (`UrlFetchApp`)?

If either is no, the fallback is a static page plus a Cloudflare Worker (see
the plan). Add `?url=<release link>` to the web app's address to try
another release.

## Files

| File | What |
|---|---|
| `Code.js` | Server: `doGet`, `loadRelease`, and the parsing functions |
| `index.html` | The page |
| `appsscript.json` | Scopes and web app settings |
| `test/` | Parser tests: `node --test bc-inbox/test/*.test.js` |

`.claspignore` keeps the tests out of Apps Script. `.clasp.json` (the link to
the Apps Script project) is per account and not committed.

## Deploying from the PC

Needs Node.js and clasp (`npm install -g @google/clasp`) on the PC, and the
Apps Script API switched on for mfyn@ at
https://script.google.com/home/usersettings.

In `C:\Users\admin\mfyn-process\bc-inbox`:

```
clasp login                                   (sign in as mfyn@)
clasp create --type webapp --title "BC Inbox" --rootDir .
clasp push
clasp deploy --description "milestone 1"
```

The first time, open the web app URL signed in as mfyn@ and allow access.
After a change: `clasp push`, then
`clasp deploy --deploymentId <id>` to update the same URL.

On the phone, open the URL in Chrome signed in as mfyn@. If Chrome is signed
in to several Google accounts and the page errors, open it in a window where
only mfyn@ is signed in: Apps Script web apps can mix up accounts.
