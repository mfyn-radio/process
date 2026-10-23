# Step 1: Acquire

Getting a purchased album from Bandcamp into the MFYN library in Google Drive.

| | |
|---|---|
| **Trigger** | A Bandcamp purchase email arrives at mfyn@nothingflatdigital.com |
| **Input** | An album bought on Bandcamp. MFYN only uses music it owns. |
| **Output** | One folder per album in `MFYN_Library`, with FLAC tracks and cover art |
| **Runs as** | mfyn@nothingflatdigital.com (owns both the inbox and the library) |
| **Automation** | Scheduled job, see [Google Cloud setup](setup/google-cloud.md) for access |

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

## Open questions

- How long Bandcamp's emailed download links stay valid (affects the batch run).
- How often the job checks the inbox.
