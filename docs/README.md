# MFYN intake process

How a song or artist goes from being *discovered* to having content ready to
post on Instagram and play on Music for Your Neighbors (MFYN).

## The pipeline

| # | Step | What happens | Status |
|---|---|---|---|
| 1 | [Acquire](01-acquire.md) | A Bandcamp purchase is downloaded as FLAC into `MFYN_Library` | Live (2026-10-23) |
| 2 | *To be defined* | What happens to an album once it's in the library | — |

Ground rule: **MFYN only uses music it owns.** Everything starts with a
Bandcamp purchase.

## Systems and accounts

| What | Where | Used for |
|---|---|---|
| mfyn@nothingflatdigital.com | Google Workspace | Bandcamp purchases, receipts, owns the library |
| admin@nothingflatdigital.com | Google Workspace | Workspace and Google Cloud administration |
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
- **Secrets:** never in the repo. Google sign-in tokens live on the PC in
  `%APPDATA%\mfyn-intake\`.
- **Changing the code:** changes go through pull requests on GitHub. On the
  PC, `git pull` in `%USERPROFILE%\mfyn-process` picks them up.

## Docs

- Step 1, Acquire:
  - [What it does and how to set it up](01-acquire.md)
  - [Decisions and how we got here](01-acquire-decisions.md)
  - [Troubleshooting](01-acquire-troubleshooting.md)
- Setup: [Google Cloud](setup/google-cloud.md)
