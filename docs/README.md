# MFYN intake and production process

How a song or artist goes from being *discovered* to having all the content
for a post ready, and an event ready to play on Music for Your Neighbors (MFYN).
It ends at a manual stop, where you review everything. The Publishing Process
starts after that.

## The pipeline

| # | Step | What happens | Status |
|---|---|---|---|
| 1 | [Acquire](01-acquire.md) | A Bandcamp purchase is downloaded as FLAC into `MFYN_Library` | Live (2026-10-23) |
| 2 | [Create the show](02-create-show.md) | **The parent.** Pick tracks as a Bandcamp playlist, Build Show copies them and writes the Reaper project, make the episode, archive it in `MFYN_Show_Archive`, then start the sub-automations below | Build Show built; the rest manual |
| 2a | [Make Episode Content](02a-make-episode-content.md) | The episode's baseline content in one run: archive cover and YouTube playlist image, a 30-second 1080×1920 video post per track in `MFYN_Posts`, and an Album Story per artist in `MFYN_Stories` | Built, being tested |
| — | [YouTube playlist](youtube-playlist.md) | After the show airs: a proposed playlist of the bands' own videos, from the Reaper running order, reviewed in the MFYN Catalog, then made on MFYN's YouTube channel | Built, not set up yet |
| 2b | [Instagram copy](02b-instagram-copy.md) | A caption for each video post, from its details and the MFYN Catalog | Built, runs during Make Episode Content |
| — | **Manual stop** | You review everything made for a post, then trigger Publishing | Not built yet |
| → | *Publishing Process* | Starts after your review: scheduling the posts on Instagram, among other things | Separate process, not built yet |

Steps 2a and 2b are sub-automations of step 2: when an event is ready, step 2
runs and triggers them. Each is its own step, with its own doc. Together they
produce the baseline content for an episode, so they belong to production. What they
leave in the episode folder, `MFYN_Posts` and `MFYN_Stories` is what you review at the manual stop.

Ground rule: **MFYN only uses music it owns.** Everything starts with a
Bandcamp purchase.

## Automations

Everything that runs by itself or on a button press, and where to look when it
misbehaves.

| Automation | Started by | Runs on | Log | Docs |
|---|---|---|---|---|
| Acquire (`intake.acquire`) | Task Scheduler task `MFYN Acquire`, daily at 20:00, via `scripts\run_acquire.cmd` | MFYN PC, while signed in | `%APPDATA%\mfyn-intake\acquire.log` | [Step 1](01-acquire.md), [troubleshooting](01-acquire-troubleshooting.md) |
| Make Episode Content (`intake.content`): the archive cover (`intake.archive_cover`), video posts (`intake.reels`), Instagram copy (`intake.captions`) and Album Stories (`intake.stories`) | You, double-clicking **MFYN – Make Episode Content** (`scripts\make_content.cmd`), until step 2 starts it itself | MFYN PC | `%APPDATA%\mfyn-intake\content.log` | [Step 2a](02a-make-episode-content.md), [step 2b](02b-instagram-copy.md), [archive cover](archive-cover.md), [Album Stories](featured-album-story.md) |
| Build Show (`intake.build_show`) | You, double-clicking **MFYN – Build Show** (`scripts\build_show.cmd`) | MFYN PC | `%APPDATA%\mfyn-intake\build_show.log` | [Step 2](02-create-show.md#build-show) |
| Show cards | Asking Claude for the month's cards (`mfyn-show-cards` skill) | Claude, in the project | — | [Show cards](show-cards.md) |
| YouTube playlist (`intake.playlist`) | Make Episode Content's playlist question, or `python -m intake.playlist` | MFYN PC | `%APPDATA%\mfyn-intake\playlist.log` | [YouTube playlist](youtube-playlist.md) |
| Event Calendar (`intake.events`) | Task Scheduler task `MFYN Event Calendar`, daily at 20:00, via `scripts\run_events.cmd` | MFYN PC, while signed in | `%APPDATA%\mfyn-intake\events.log` | [Event Calendar](event-calendar.md) |
| Wishlist (`intake.wishlist`) | Task Scheduler task `MFYN Wishlist`, daily at 20:00, via `scripts\run_wishlist.cmd` | MFYN PC, while signed in | `%APPDATA%\mfyn-intake\wishlist.log` | [Wishlist](wishlist.md) |
| Tests | GitHub Actions, on pull requests and pushes to `main` (`.github/workflows/tests.yml`) | GitHub | the Actions tab | `python -m pytest` locally |
| Labels | GitHub Actions, when `.github/workflows/labels.yml` changes on `main`, or run by hand (`workflow_dispatch`) | GitHub | the Actions tab | [Issues](#issues) |

Not automated: the parent [step 2](02-create-show.md), which you still do by
hand. Not built: the manual stop's hand-off and the Publishing Process.
The logs keep four files of up to 1 MB each, and Make Episode Content also prints to its window.
Acquire and Make Episode Content (and the ON AIR posts, Album Story and archive cover when run on
their own) also write what they did to the **MFYN Run Log** sheet, for the status page: see
[run log](run-log.md).

## Systems and accounts

| What | Where | Used for |
|---|---|---|
| mfyn@nothingflatdigital.com | Google Workspace | Bandcamp purchases, receipts, owns the library |
| admin@nothingflatdigital.com | Google Workspace | Workspace and Google Cloud administration |
| MFYN Catalog | Airtable base on the free plan, in mfyn@'s Airtable account, kept by the automation ([Airtable](airtable.md)) | The artist library (Instagram handles, tags, links), releases, labels, every event on Event Calendar, and the YouTube playlist proposals, linked to each other |
| MFYN Artists | Google Sheet in mfyn@'s Drive | Where the catalog was kept until 21 Nov 2026. A backup now; nothing writes to it |
| MFYN Wishlist | Google Sheet in mfyn@'s Drive, kept by the automation | Your Bandcamp wishlist with tags and locations, to filter on your phone ([Wishlist](wishlist.md)) |
| MFYN Run Log | Google Sheet in mfyn@'s Drive, kept by the automation | What the automations did, for the status page ([run log](run-log.md)) |
| `MFYN_Show_Archive` | mfyn@'s My Drive, `H:\My Drive\MFYN_Show_Archive` | Finished episodes, `D_M_YYYY- Episode Name\Tracks` |
| `MFYN_Posts` | mfyn@'s My Drive, `H:\My Drive\MFYN_Posts` | Each episode's video posts, their details and captions, for your review and then Publishing |
| `MFYN_Stories` | mfyn@'s My Drive, `H:\My Drive\MFYN_Stories` | Featured-album Stories and their details, one folder per episode like `MFYN_Posts`, for your review and then Publishing |
| Processing sketches | this repo, `processing\` (master); a copy in `H:\My Drive\MFYN_Processing` ([working on the PC](working-on-the-pc.md)) | `MFYN_VideoPost_OnAir` makes the video posts; `MFYN_Story_Album` makes the featured-album Stories; `MFYN_Archive` makes the archive episode covers ([automated](archive-cover.md), or by hand: [README](../processing/MFYN_Archive/README.md)) |
| Event Calendar | Google Calendar, made by the automation in mfyn@'s account | Upcoming events, from posts saved to the **events** collection on Instagram |
| `MFYN_Library` | mfyn@'s My Drive, synced to `H:\My Drive\MFYN_Library` on the MFYN PC | The music library, one folder per album |
| MFYN PC | Windows, signed in, running Google Drive for desktop and Chrome | Runs the automation (Task Scheduler) |
| `mfyn-library-agent` | Google Cloud project, Internal audience | Lets the automation read and label mail, and keep its run log sheet and calendar ([setup](setup/google-cloud.md)) |
| Claude Code | installed on the MFYN PC, signed in to the Claude subscription | Reads event flyers for the [Event Calendar](event-calendar.md) (`claude -p`) |
| `mfyn-radio/process` | GitHub, this repo | Code and docs; GitHub only runs the tests |

## Issues

[GitHub Issues](https://github.com/mfyn-radio/process/issues) are the single
list of open work. There are two kinds:

- **General issues:** the default, a free-form tracker for work and ideas.
  They're yours.
- **Claude tasks:** made from the **Claude task** form, labelled
  `claude-task`. Claude works these on its own, at the start of a session, and
  opens a pull request that closes the issue. You review and merge. If Claude
  needs an answer it comments and adds `needs-human`; remove that label once
  you've answered. [`CLAUDE.md`](../CLAUDE.md) has the full rules.

## Conventions

- **Album folders:** `Artist - Album` (Bandcamp's own naming). Characters
  Windows doesn't allow become `_`.
- **Gmail labels:** the automation marks what it has handled.
  - `MFYN/Downloaded`: the album is in the library.
  - `MFYN/Excluded`: deliberately skipped (see
    [excluded purchases](01-acquire.md#excluded-purchases)).
- **Instagram status** in the MFYN Catalog:
  - `Suggested` or `Not found`: set by step 1.
  - `Confirmed` or `No Instagram`: set by you in step 2a.
- **Episode folders:** `D_M_YYYY- Episode Name`, using the air date. Each gets
  its archive cover, `MFYN_archive_NN.png`, and the YouTube playlist image `MFYN_tracklist_NN.png` in the same colour, numbered from No. 3 (5 November 2026).
- **Video posts:** `MFYN_Posts\<episode folder>\Artist - Title.mp4`, plus `.json`
  details and the `.txt` caption.
- **Secrets:** never in the repo. Google sign-in tokens live on the PC in
  `%APPDATA%\mfyn-intake\`.
- **Changing the code:** changes go through pull requests on GitHub. On the
  PC, `git pull` in `%USERPROFILE%\mfyn-process` picks them up, and
  `scripts\sync_sketches.cmd` refreshes the sketches in `MFYN_Processing`.
  See [working on the PC](working-on-the-pc.md).

## Docs

- **[Working on the MFYN PC](working-on-the-pc.md):** where the repo,
  Processing and output live, and how Claude renders and runs things there.
- **[Session log](session-log.md): where we left off.** Open work and open
  questions are tracked in the repo's
  [GitHub Issues](https://github.com/mfyn-radio/process/issues), the single
  list.
- Step 1, Acquire:
  - [What it does and how to set it up](01-acquire.md)
  - [Decisions and how we got here](01-acquire-decisions.md)
  - [Troubleshooting](01-acquire-troubleshooting.md)
- Step 2: [Create the show](02-create-show.md)
  - Step 2a: [Make Episode Content](02a-make-episode-content.md)
  - Step 2b: [Instagram copy](02b-instagram-copy.md)
  - [Archive cover](archive-cover.md)
  - [Album Stories](featured-album-story.md)
  - [YouTube playlist](youtube-playlist.md)
- [Event Calendar](event-calendar.md): events from saved Instagram posts
- Setup: [Google Cloud](setup/google-cloud.md)
