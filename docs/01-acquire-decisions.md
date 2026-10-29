# Step 1: decisions and how we got here

Built on 2026-10-23. This is the record of what was decided for
[step 1](01-acquire.md), what was tried, and why it ended up as it is.

## Requirements (from the start)

- The trigger is buying an album on Bandcamp. Only owned music is used.
- Bandcamp doesn't download anything after a purchase, so the download itself
  should be automatic.
- Format: **FLAC**, for better metadata. Keep the cover art.
- Destination: `H:\My Drive\MFYN_Library` (mfyn@'s My Drive).
- Unzip each album into `Artist - Album` and delete the zip.
- Mostly albums. A single track is bought occasionally.
- **New purchases only.** Older purchases can be handled by a manual batch
  run later.
- Check **hourly**.

## Decisions

### Use the purchase email as the trigger

Bandcamp has no API for buyers. The options were:

- **watch the receipt emails** (chosen):
  - every purchase sends one;
  - its download link works without signing in to Bandcamp.
- log in and scrape the Bandcamp collection: needs a Bandcamp login, and
  breaks more easily.

What a receipt looks like:

- from `noreply@bandcamp.com`, subject `Thank you!`;
- body starting "Thanks for purchasing from …";
- a link `https://bandcamp.com/download?from=receipt&payment_id=…&sig=…`.

Gmail groups several receipts into one thread, so the job works per message.
Pre-orders say `Releases <date>` and wait until then.

### Google access through the existing `mfyn-library-agent` project

An earlier chat had already created this Google Cloud project, with an
**Internal** audience and the Gmail and Drive APIs enabled. We reused it, and
added a new Desktop client, `mfyn-intake-cli`, because the old client's JSON
file couldn't be found.

The "use this client for an AI-powered agent" option was left unticked: the
job is a plain script.

### Exclude Music for Your Neighbors - Archive

Purchases from that Bandcamp page are past episodes of the show, not music.
They're skipped and labelled `MFYN/Excluded`.

### First attempt: GitHub Actions (abandoned)

The first version ran hourly on GitHub Actions:

- Gmail and the Drive API, using secrets stored in GitHub;
- plain HTTP requests to Bandcamp;
- uploads straight to Drive.

Signing in to Google worked: a dry run found the inbox. But a real run got a
**"Client Challenge"** page from Bandcamp instead of the download page.

That's Bandcamp's bot protection. A test from the MFYN PC with a plain Python
request got the same challenge, so it isn't about where the request comes
from: Bandcamp only serves the page to real browsers. Getting around the
protection wasn't an option.

The GitHub workflow, the GitHub secrets and the Drive-scope token were
removed.

### Run on the MFYN PC, in a real Chrome window (chosen)

[bcdl](https://github.com/corbin-zip/bcdl) showed the way: it drives a real
browser with Selenium. A test confirmed that a Selenium-driven Chrome on the
MFYN PC gets the real download page.

So the job runs on the PC, hourly, from Task Scheduler:

- reads Gmail as mfyn@ (`gmail.modify` only);
- opens each receipt link in Chrome, picks FLAC, and lets Chrome download;
- unzips into the Drive-synced `MFYN_Library` folder. Drive for desktop does
  the uploading, so the Drive API isn't needed.

The trade-off: the PC must be on, signed in, and running Drive for desktop.

The alternative, kept in reserve, was **semi-manual**: you click Download
into a Drive inbox folder, and a job unzips and files it. Use that if
Bandcamp ever starts blocking automated browsers too.

### Folder name from Bandcamp's zip name

Bandcamp names album zips `Artist - Album.zip`, which is exactly the folder
convention. Using it avoids parsing artist and album out of the email. Single
tracks arrive as one file and get the same treatment.

### Safe partial work

- Albums unzip into `.partial - Artist - Album` and are renamed when complete.
- Emails are only labelled after success.
- So an interrupted or failed run is simply retried next hour.

### The MFYN Artists sheet

FLAC tags don't include Instagram handles, but posts should tag the artist
(and label) when they have an account. Chrome is already on Bandcamp in step
1, so the step also collects what's useful for captions and the show.

- **What's kept:**
  - **Artists** (the artist library): Instagram, location, tags, website,
    other links and bio.
  - **Releases:** album, artist, label, release date, tags, album link,
    credits, purchase date and library folder.
  - **Labels:** each label's Instagram, so posts can tag the label too.
  - **Tags:** one row per tag per release, because a spreadsheet can't sort
    by a cell that holds several tags.
- **Automatic, no review.** Handles are confirmed when Reels are made (step
  3) and used when posts are scheduled (step 2c), so a handle fixed late still
  gets used.
- **Never overwrite typed values.** Only empty cells are filled, and tags are
  added to.
- **Non-Instagram links** are kept for crediting in captions, because
  Instagram can only tag Instagram accounts. Spotify (and Apple Music) are
  left out.
- **Not kept:** a "new release" flag, since the release and purchase dates
  are enough; track-level details, which step 2a reads from the FLACs; and
  artist photos (maybe later).
- **The seller's page decides whose details they are.** On a self-release,
  the Bandcamp sidebar is the artist's. On a label release it's the label's,
  so it goes to the Labels tab rather than being mistaken for the artist's.
- **Narrow access.** The sheet uses the `drive.file` permission, which only
  reaches files the automation created itself.

## Problems along the way

Each one is in [troubleshooting](01-acquire-troubleshooting.md).

- `python` vs `py` on the PC.
- Running commands from outside the repo folder.
- Pull requests merged before their last commits were pushed.
- The download link was found, but the click landed on Bandcamp's page footer.
  Fixed by clicking through JavaScript. mfyn-radio/process#5 first guessed,
  wrongly, that the link selector was out of date.

## First successful run

2026-10-23: *applied communications – applied communications bites the big
one*. 9 FLAC tracks and `cover.png` landed in `MFYN_Library`, the receipt was
labelled `MFYN/Downloaded`, and the hourly task `MFYN Acquire` was created.
