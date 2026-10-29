# MFYN Intake Process

Code and documentation for the **Music for Your Neighbors (MFYN)** intake process:
how a song or artist goes from being *discovered* to having content ready to
post on Instagram and play on the radio show.

## Layout

- `docs/` — process documentation. Start at [`docs/README.md`](docs/README.md):
  the pipeline, the systems involved, and each step's spec, decisions and
  troubleshooting.
- `intake/` — the automation code.
- `processing/` — the Processing sketches that make the Reels (and the Album
  Story, not automated yet).
- `scripts/` — launchers: the hourly Acquire task, and the Create Show and
  Make Reels double-clicks.
- `tests/` — run with `python -m pytest`; GitHub runs them on every push.

## Steps

1. [Acquire](docs/01-acquire.md) — download new Bandcamp purchases into
   `MFYN_Library` on Google Drive. Runs hourly on the MFYN PC. *(live since
   2026-10-23)*
2. [Create the show](docs/02-create-show.md) — a Bandcamp playlist becomes an
   episode folder in `MFYN_Show_Archive`, then Make Reels starts. Double-click
   to start. *(built, being tested)*
3. [Make Reels](docs/03-make-reels.md) — the episode's tracks become
   30-second Instagram Reels. Double-click to start. *(built, being tested)*
4. Schedule posts — *(not built yet; Instagram captions come first)*

Where we left off, and what's next: [`docs/session-log.md`](docs/session-log.md).
