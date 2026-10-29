# MFYN intake process

How a song or artist goes from being *discovered* to having content ready to
post on Instagram and play on Music for Your Neighbors (MFYN).

## The pipeline

| # | Step | What happens | Status |
|---|---|---|---|
| 1 | [Acquire](01-acquire.md) | A Bandcamp purchase is downloaded as FLAC into `MFYN_Library` | Live (2026-10-23) |
| 2 | [Create the show](02-create-show.md) | Pick tracks, make the episode, archive it in `MFYN_Show_Archive` | Manual |
| 3 | [Make Reels](03-make-reels.md) | The episode's tracks become 30-second Reels in `MFYN_Reels` | Built, being tested |
| — | *Instagram copy* | A caption for each Reel, from its details and the MFYN Artists sheet | Next up |
| 4 | *Schedule posts* | Reels in `MFYN_Reels` are scheduled on Instagram | Not built yet |

Ground rule: **MFYN only uses music it owns.** Everything starts with a
Bandcamp purchase.

## Automations

Everything that runs by itself or on a button press, and where to look when it
misbehaves.

| Automation | Started by | Runs on | Log | Docs |
|---|---|---|---|---|
| Acquire (`intake.acquire`) | Task Scheduler task `MFYN Acquire`, hourly, via `scripts\run_acquire.cmd` | MFYN PC, while signed in | `%APPDATA%\mfyn-intake\acquire.log` | [Step 1](01-acquire.md), [troubleshooting](01-acquire-troubleshooting.md) |
| Make Reels (`intake.reels`) | You, double-clicking **MFYN – Make Reels** (`scripts\make_reels.cmd`) | MFYN PC | `%APPDATA%\mfyn-intake\reels.log` | [Step 3](03-make-reels.md) |
| Tests | GitHub Actions, on pull requests and pushes to `main` (`.github/workflows/tests.yml`) | GitHub | the Actions tab | `python -m pytest` locally |

Not automated: [step 2](02-create-show.md), and the Album Story sketch. Not
built: Instagram captions and step 4. Both logs keep four files of up to 1 MB
each, and Make Reels also prints to its window.

## Systems and accounts

| What | Where | Used for |
|---|---|---|
| mfyn@nothingflatdigital.com | Google Workspace | Bandcamp purchases, receipts, owns the library |
| admin@nothingflatdigital.com | Google Workspace | Workspace and Google Cloud administration |
| MFYN Artists | Google Sheet in mfyn@'s Drive, kept by the automation | The artist library (Instagram handles, tags, links), releases and labels |
| `MFYN_Show_Archive` | mfyn@'s My Drive, `H:\My Drive\MFYN_Show_Archive` | Finished episodes, `D_M_YYYY- Episode Name\Tracks` |
| `MFYN_Reels` | mfyn@'s My Drive, `H:\My Drive\MFYN_Reels` | Each episode's Reels and their details, for step 4 |
| Processing sketches | this repo, `processing\` | `MFYN_Reel` makes the Reels; `MFYN_Album` (not automated yet) |
| `MFYN_Library` | mfyn@'s My Drive, synced to `H:\My Drive\MFYN_Library` on the MFYN PC | The music library, one folder per album |
| MFYN PC | Windows, signed in, running Google Drive for desktop and Chrome | Runs the automation (Task Scheduler) |
| `mfyn-library-agent` | Google Cloud project, Internal audience | Lets the automation read and label mail ([setup](setup/google-cloud.md)) |
| `mfyn-radio/process` | GitHub, this repo | Code and docs; GitHub only runs the tests |

## Conventions

- **Album folders:** `Artist - Album` (Bandcamp's own naming). Characters
  Windows doesn't allow become `_`.
- **Gmail labels:** the automation marks what it has handled.
  - `MFYN/Downloaded`: the album is in the library.
  - `MFYN/Excluded`: deliberately skipped (see
    [excluded purchases](01-acquire.md#excluded-purchases)).
- **Instagram status** in the MFYN Artists sheet:
  - `Suggested` or `Not found`: set by step 1.
  - `Confirmed` or `No Instagram`: set by you in step 3.
- **Episode folders:** `D_M_YYYY- Episode Name`, using the air date.
- **Reels:** `MFYN_Reels\<episode folder>\Artist - Title.mp4`, plus `.json`
  details.
- **Secrets:** never in the repo. Google sign-in tokens live on the PC in
  `%APPDATA%\mfyn-intake\`.
- **Changing the code:** changes go through pull requests on GitHub. On the
  PC, `git pull` in `%USERPROFILE%\mfyn-process` picks them up.

## Docs

- **[Session log](session-log.md): where we left off, and what's next.**
- Step 1, Acquire:
  - [What it does and how to set it up](01-acquire.md)
  - [Decisions and how we got here](01-acquire-decisions.md)
  - [Troubleshooting](01-acquire-troubleshooting.md)
- Step 2: [Create the show](02-create-show.md)
- Step 3: [Make Reels](03-make-reels.md)
- Setup: [Google Cloud](setup/google-cloud.md)
