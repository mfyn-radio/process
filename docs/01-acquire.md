# Step 1: Acquire

Getting a purchased album from Bandcamp into the MFYN library in Google Drive.

| | |
|---|---|
| **Trigger** | A Bandcamp purchase email arrives at mfyn@nothingflatdigital.com |
| **Input** | An album bought on Bandcamp. MFYN only uses music it owns. |
| **Output** | One folder per album in `MFYN_Library`, with FLAC tracks and cover art |
| **Runs as** | mfyn@nothingflatdigital.com (owns both the inbox and the library) |
| **Automation** | GitHub Actions, hourly: [`acquire.yml`](../.github/workflows/acquire.yml) runs [`intake/acquire.py`](../intake/acquire.py) |
| **Access** | [Google Cloud setup](setup/google-cloud.md) |

## What it does

1. Find unprocessed purchase emails in the mfyn@ inbox.
2. Follow the email's download link and choose **FLAC**.
3. Wait for Bandcamp to prepare the zip, then download it.
4. Unzip it into `MFYN_Library/Artist - Album` and delete the zip.
5. Label the email `MFYN/Downloaded` so it is never processed twice.

## Details

### Identifying purchase emails

- From: `noreply@bandcamp.com`
- Subject: `Thank you!`
- Body starts with: `Thanks for purchasing from …`

The inbox gets lots of other Bandcamp mail (new releases, artist messages,
Bandcamp Friday promos). Those must be ignored.

Gmail can group several purchases into one thread (five on one Bandcamp
Friday), so each **message** is handled on its own, not each thread.

### Library location

- Path on desktop: `H:\My Drive\MFYN_Library`
- Owner: mfyn@nothingflatdigital.com
- Drive folder ID: `1Anmx1Om4RZdmwujyu8fEb-lUJnEULKG5`

### Folder naming

- Albums: `Artist - Album`
- A single track bought now and then: `Artist - Track`
- Characters Drive or Windows don't allow in names (`\ / : * ? " < > |`) are
  removed or replaced.
- If the folder already exists, the album is skipped.

### Pre-orders

Some emails say `Releases <date>`. The album can't be downloaded until then.
The email is left unlabelled and retried after the release date.

### Scope

- **New purchases only.** The job runs automatically from the day it goes live.
- **Backlog:** a manual batch run reprocesses older purchase emails still in
  the inbox. If Bandcamp's emailed links for old purchases have stopped
  working, the batch run falls back to the Bandcamp collection page.

### Failures

- If one album fails (for example, Bandcamp is down), its email stays
  unlabelled and is retried on the next run. The other albums carry on.
- Albums upload into a folder named `.partial - Artist - Album`, which is
  renamed once every file is in. If a run is interrupted, the half-finished
  folder is replaced on the next try, so a folder without the prefix is always
  complete.
- A run with any failure shows as failed in GitHub Actions, and GitHub emails
  you about it.

## Running it

The job runs every hour, at 17 minutes past. To run it by hand:

1. Go to **Actions → Acquire Bandcamp purchases** in the GitHub repo.
2. Click **Run workflow**.
3. Optionally tick:
   - **Backlog**: also download purchases from before 2026-10-23.
   - **Dry run**: list what would be downloaded without downloading,
     uploading or labelling anything.
   - **Message ID**: handle just one purchase email, whatever its date. This
     is the Gmail API ID (16 hex characters, like `1a12586490c98e61`), not
     the ID in the Gmail web address. Ask Claude to look it up.

From a terminal with the three `GOOGLE_*` values set as environment variables:

```
pip install -r requirements.txt
python -m intake.acquire [--backlog] [--dry-run] [--message-id ID]
```

## Open questions

- How long Bandcamp's emailed download links stay valid (affects the batch run).
