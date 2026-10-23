# Step 1: Acquire

Getting a purchased album from Bandcamp into the MFYN library.

See also: [decisions and how we got here](01-acquire-decisions.md) ·
[troubleshooting](01-acquire-troubleshooting.md) ·
[process overview](README.md)

| | |
|---|---|
| **Trigger** | A Bandcamp purchase email arrives at mfyn@nothingflatdigital.com |
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

### Library location

- Path: `H:\My Drive\MFYN_Library`. Set the `MFYN_LIBRARY` environment
  variable to use a different one.
- Owner: mfyn@nothingflatdigital.com
- Drive folder ID: `1Anmx1Om4RZdmwujyu8fEb-lUJnEULKG5`

### Folder naming

- `Artist - Album`, taken from the name Bandcamp gives the zip.
- A single track bought now and then: `Artist - Track`.
- Characters Windows doesn't allow in names (`\ / : * ? " < > |`) become `_`.
- If the folder already exists, the album isn't added again.

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
- Everything is logged to `%APPDATA%\mfyn-intake\acquire.log`.

### Scope

- **New purchases only.** Purchases from 2026-10-23 onwards.
- **Backlog:** `--backlog` also handles older purchase emails still in the
  inbox.

## Setting it up on the PC

One time only. Needs Python and Google Chrome, both already installed.

1. **Get the code.** Install Git (`winget install Git.Git`), then:
   ```
   cd %USERPROFILE%
   git clone https://github.com/mfyn-radio/process.git mfyn-process
   cd mfyn-process
   python -m pip install -r requirements.txt
   ```
   Git asks you to sign in to GitHub the first time.
2. **Sign in to Gmail as mfyn@.** Use the client JSON from
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
python -m intake.acquire [--backlog] [--dry-run] [--message-id ID]
```

- `--dry-run` lists what would be downloaded without opening Chrome,
  downloading or labelling anything.
- `--backlog` includes purchases from before 2026-10-23.
- `--message-id` handles just one purchase email, whatever its date. This is
  the Gmail API ID (16 hex characters, like `1a0dacaede35264f`), not the ID in
  the Gmail web address. Ask Claude to look it up.

## Day to day

Nothing to do: buy on Bandcamp, and within the hour the album is in
`MFYN_Library` and the receipt is labelled `MFYN/Downloaded`. If it isn't, see
[troubleshooting](01-acquire-troubleshooting.md#an-album-didnt-arrive).

Keep the PC on and signed in, with Drive for desktop running.

## Open questions

- Multi-item purchases (more than one album on one receipt) are untested.
- The ~30 purchases from before 2026-10-23 haven't been downloaded yet. Run
  `--dry-run --backlog` first to see the list.
