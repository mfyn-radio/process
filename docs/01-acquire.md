# Step 1: Acquire

Getting a purchased album from Bandcamp into the MFYN library.

See also: [decisions and how we got here](01-acquire-decisions.md) ·
[troubleshooting](01-acquire-troubleshooting.md) ·
[process overview](README.md)

| | |
|---|---|
| **Trigger** | The hourly run finds a new Bandcamp purchase email in the mfyn@nothingflatdigital.com inbox |
| **Input** | An album bought on Bandcamp. MFYN only uses music it owns. |
| **Output** | One folder per album in `MFYN_Library`, with FLAC tracks and cover art |
| **Runs on** | The MFYN Windows PC, hourly, from Task Scheduler |
| **Status** | Live on the MFYN PC since 2026-10-23 (Task Scheduler task `MFYN Acquire`) |
| **Code** | [`intake/acquire.py`](../intake/acquire.py), started by [`scripts/run_acquire.cmd`](../scripts/run_acquire.cmd) |

## What it does

1. Find unprocessed purchase emails in the mfyn@ inbox.
2. Open the email's download link in Chrome and choose **FLAC**.
3. Wait for Bandcamp to prepare the zip, and let Chrome download it.
4. Unzip it into `MFYN_Library\Artist - Album` and delete the zip.
5. Label the email `MFYN/Downloaded` so it is never processed twice.
6. Record the release, its artists and its label in the
   [MFYN Artists sheet](#the-mfyn-artists-sheet), with Instagram handles
   suggested from Bandcamp.

Purchases from [excluded pages](#excluded-purchases) are skipped and labelled
`MFYN/Excluded`.

## Why it runs on the PC, in Chrome

Bandcamp shows a "Client Challenge" (bot protection) instead of the download
page to anything that isn't a real browser. That rules out plain scripts and
GitHub Actions. A normal Chrome window on the MFYN PC gets the real page.
The approach is based on [bcdl](https://github.com/corbin-zip/bcdl). The
[decision log](01-acquire-decisions.md) has the full story.

Receipt links work without signing in to Bandcamp, so no Bandcamp password is
stored anywhere. Chrome only opens when there's something to download.

Writing into `H:\My Drive\MFYN_Library` means Google Drive for desktop does the
uploading. The PC needs to be on, signed in, and running Drive for desktop.

## Details

### Identifying purchase emails

- From: `noreply@bandcamp.com`
- Subject: `Thank you!`
- Body starts with: `Thanks for purchasing from …`

The inbox gets lots of other Bandcamp mail (new releases, artist messages,
Bandcamp Friday promos). Those must be ignored.

Gmail can group several purchases into one thread (five on one Bandcamp
Friday), so each **message** is handled on its own, not each thread.

### Excluded purchases

Purchases from these Bandcamp pages never go in the library. Their emails are
labelled `MFYN/Excluded` instead.

- **Music for Your Neighbors - Archive**: past episodes of the show, not music.

The list is `EXCLUDED_SELLERS` in [`intake/config.py`](../intake/config.py).

### The MFYN Artists sheet

The **MFYN Artists** Google Sheet in mfyn@'s Drive is what the library knows
about its music: who the artists are, their Instagram handles for tagging,
and each release's label, date and tags. The automation creates it on first
use and fills it in after every album. Nobody reviews it at this point.

**Artists** is the artist library: one row per artist.

| Column | Comes from |
|---|---|
| Artist | the FLAC `ARTIST` tag |
| Instagram | the artist's Bandcamp page, as `@handle` |
| Status | see below |
| Location | Bandcamp, e.g. `Brooklyn, New York` |
| Tags | every Bandcamp tag across their releases |
| Website | their Bandcamp page's links |
| Other links | SoundCloud, YouTube, TikTok, X, Bluesky, Facebook… for crediting in captions. Not Spotify or Apple Music. |
| Bandcamp page | |
| Bio | their Bandcamp bio. Notes for you and the show; paraphrase it in captions. |
| Added | the date the row was added |

**Releases** has one row per album in the library: Album, Artist, Label,
Release date, Tags, Album link, Credits, Purchased (the receipt date), Library
folder, Added.

- **Label** is whoever sold the album on Bandcamp, or `Self-released` when
  the artist sold it.
- **Release date** comes from the album page, written as `2026-10-30` so it
  sorts.

**Labels** has one row per label: Label, Instagram, Status, Location, Website,
Other links, Bandcamp page, Added. A label's Instagram is suggested and
confirmed the same way as an artist's, so posts can tag both.

**Tags** has one row per Bandcamp tag per release (Tag, Artist, Album). Sort
or filter this tab to see, say, every *ambient* artist, or add a pivot table
to count the library by tag. Bandcamp tags mix genres with places like
*Brooklyn*; they're kept as Bandcamp has them.

#### Status

| Status | Meaning |
|---|---|
| `Suggested` | A handle was found on Bandcamp, not yet checked |
| `Not found` | No Instagram link was found |
| *(set in step 2a)* | Confirmed or corrected when Reels are made |

#### How it's filled in

- **The automation only fills empty cells and adds tags.** It never
  overwrites anything typed in the sheet, so corrections and your own notes
  are safe. The one exception is `Status`, which follows the Instagram cell
  while it still says `Suggested` or `Not found`.
- **Which Bandcamp page:** the album page, linked from the receipt's download
  page. In a backlog or `--artists` run, the album is looked up on the
  seller's page (from the `Visit https://….bandcamp.com` comment in each
  FLAC).
- **Self-release:** the page's sidebar is the artist's own, so it fills the
  artist's Instagram, location, links and bio.
- **Label release:** the sidebar is the label's, so it fills the **Labels**
  row instead. The artist gets their tags, but their Instagram is left
  `Not found` for you to fill in.
- **Compilations (several artists):** each artist gets a row with just their
  name. Tags and details stay on the release.
- **Matching:** names are matched ignoring case. A collaboration like `A + B`
  is one row.
- **If the sheet can't be reached:** downloads still go ahead. `--artists`
  fills in what was missed.
- Columns are found by their header, so you can reorder columns or add your
  own. Don't rename the built-in ones.

### Library location

- Path: `H:\My Drive\MFYN_Library`. Set the `MFYN_LIBRARY` environment
  variable to use a different one.
- Owner: mfyn@nothingflatdigital.com
- Drive folder ID: `1Anmx1Om4RZdmwujyu8fEb-lUJnEULKG5`

### Folder naming

- `Artist - Album`, taken from the name Bandcamp gives the zip.
- A single track bought now and then: `Artist - Track`.
- Characters Windows doesn't allow in names (`\ / : * ? " < > |`) become `_`.
- If the folder already exists, the album isn't added again. The download
  is thrown away and the email is still labelled `MFYN/Downloaded`.

### Pre-orders

Some emails say `Releases <date>`. The album can't be downloaded until then.
The email is left unlabelled and retried after the release date.

### Failures

- If one album fails (for example, Bandcamp is down), its email stays
  unlabelled and is retried on the next run. The other albums carry on.
- Albums are unzipped into a folder named `.partial - Artist - Album`, which
  is renamed once complete. If a run is interrupted, the half-finished folder
  is replaced on the next try, so a folder without the prefix is always
  complete.
- Everything is logged to `%APPDATA%\mfyn-intake\acquire.log` (it rolls
  over at 1 MB and keeps three older files).
- The run exits with an error if any album failed, which shows in Task
  Scheduler's last result.

### Scope

- **New purchases only.** Purchases from 2026-10-23 onwards.
- **Backlog:** `--backlog` also handles older purchase emails still in the
  inbox.

## Setting it up on the PC

One time only. Needs Python 3.10 or newer and Google Chrome, both already
installed.

1. **Get the code.** Install Git (`winget install Git.Git`), then:
   ```
   cd %USERPROFILE%
   git clone https://github.com/mfyn-radio/process.git mfyn-process
   cd mfyn-process
   python -m pip install -r requirements.txt
   ```
   Git asks you to sign in to GitHub the first time.
2. **Sign in to Google as mfyn@.** Use the client JSON from
   [Google Cloud setup](setup/google-cloud.md):
   ```
   python -m intake.acquire --setup %USERPROFILE%\Downloads\client_secret_648160844206-jhea8g49optdpf94bqet5grgbf64915g.apps.googleusercontent.com.json
   ```
   A browser opens. Sign in as **mfyn@nothingflatdigital.com** and approve.
   The token is saved in `%APPDATA%\mfyn-intake\`, never in the repo.
3. **Test it** with a dry run, then one real album:
   ```
   python -m intake.acquire --dry-run --backlog
   python -m intake.acquire --message-id <id>
   ```
4. **Schedule it hourly:**
   ```
   schtasks /Create /TN "MFYN Acquire" /SC HOURLY /TR "\"%USERPROFILE%\mfyn-process\scripts\run_acquire.cmd\""
   ```
   It runs while you're signed in to Windows. To run it straight away:
   `schtasks /Run /TN "MFYN Acquire"`.

To update the code later: `cd %USERPROFILE%\mfyn-process` then `git pull`.

## Running it by hand

From the repo folder (`cd %USERPROFILE%\mfyn-process`):

```
python -m intake.acquire [--backlog] [--dry-run] [--message-id ID] [--artists]
```

- `--dry-run` lists what would be downloaded without opening Chrome,
  downloading or labelling anything.
- `--backlog` includes purchases from before 2026-10-23.
- `--message-id` handles just one purchase email, whatever its date. This is
  the Gmail API ID (16 hex characters, like `1a0dacaede35264f`), not the ID in
  the Gmail web address. Ask Claude to look it up.
- `--artists` fills in the MFYN Artists sheet from every album already in the
  library, then stops. It's safe to repeat. Use it after setup, after a
  backlog run, or after a code update that adds columns.

## Day to day

Nothing to do: buy on Bandcamp, and within the hour the album is in
`MFYN_Library` and the receipt is labelled `MFYN/Downloaded`. If it isn't, see
[troubleshooting](01-acquire-troubleshooting.md#an-album-didnt-arrive).

Keep the PC on and signed in, with Drive for desktop running.

## Open questions

- The `Status` values step 2a writes when a handle is confirmed (designed with
  step 2a).
- Bandcamp's page layout was read from what's known of it, not confirmed. If
  fields stay empty after `--artists`, the page reading needs adjusting.
- Multi-item purchases (more than one album on one receipt) are untested.
- The ~30 purchases from before 2026-10-23 haven't been downloaded yet. Run
  `--dry-run --backlog` first to see the list.
