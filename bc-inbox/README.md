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

- **Milestone 1, the spike: passed** (25 Nov 2026). Bandcamp's player plays
  inside the Apps Script page, and Google's servers can fetch Bandcamp pages,
  so Apps Script stays; no Cloudflare fallback.
- **Milestone 2, release emails.** The page lists Bandcamp "New release from"
  emails from mfyn@'s Gmail: cover, artist, title, the account you follow,
  date, album or track, and a pre-order badge for "just announced" releases.
  Merch, messages, receipts and login emails are left out. **Play** fetches
  that release page and shows the player under it (one at a time).

- **Milestone 3, location and region.** Each release's page is looked up
  once, server-side, for its location, player and tags (cached: 6 hours in
  `CacheService`, then for good in script properties; at most 8 releases per
  call, 0.4 s apart). The list is grouped by the region picked at the top
  (default **BeNe**): the artist's location matches first, then releases where
  only the label's location matches, then everything else, each newest first.
  Nothing is filtered out. Changing the region reorders at once, with no
  fetching. A location marked "(label)" came from a label's page, not the
  artist's.

- **Milestone 4, the weekly top 10.** The page reads the newest
  `rising-artists-YYYY-MM-DD.csv` in the `MFYN_Rising_Artists` folder of
  mfyn@'s Drive (Drive read-only) and pins that week's picks on top, in the
  run's order, with fit notes, IG handle and next BeNe show. **Load top 10 CSV**
  takes a CSV by hand instead. A pick's Bandcamp link may be an artist page:
  then the suggested track is tried on that site, else the newest release.
  A release in both the top 10 and the emails shows once, as top 10. Picks
  from earlier weeks drop into the main list, ranked by region like the rest.

The first load reads the last 30 days. After that, **Check for new** reads
only emails since the last check; the list is kept in the browser
(`localStorage`). **Reload 30 days** starts over. `?url=<release link>` on the
web app's address still plays any one release.

Gmail is read through the Gmail API advanced service with only the
`gmail.readonly` scope, so the script can't send, label, archive or delete
email.

## Files

| File | What |
|---|---|
| `Code.js` | Server: `doGet`, `getReleaseEmails` (Gmail), `enrichItems` (release pages, cached), `getTopTen` / `topTenFromCsv` (Drive), `loadRelease` |
| `Parse.js` | Pure parsing: release emails, release pages, merging. No Apps Script calls |
| `TopTen.js` | The weekly CSV: parsing, newest file, artist-page links → a release |
| `Region.js` | Region presets, location → country, ranking. The page gets the ranking functions from here too |
| `index.html` | The page |
| `appsscript.json` | Scopes and web app settings |
| `test/` | Parser tests: `node --test bc-inbox/test/*.test.js`. `test/fixtures/emails.json` holds trimmed real Bandcamp emails, one per subject kind |

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
`clasp deploy --deploymentId <id> --description "..."` to update the same
URL. A change of scopes (as in milestone 2, which adds Gmail read-only) asks
for permission again on the next open.

On the phone, open the URL in Chrome signed in as mfyn@. If Chrome is signed
in to several Google accounts and the page errors, open it in a window where
only mfyn@ is signed in: Apps Script web apps can mix up accounts.
