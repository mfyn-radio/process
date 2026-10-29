# MFYN Intake and Production Process

Code and documentation for the **Music for Your Neighbors (MFYN)** intake and
production process: how a song or artist goes from being *discovered* to having
all the content for a post ready, and a show ready to play on the radio.

It ends at a manual stop, where you review everything. The separate
**Publishing Process** starts after that. It isn't part of this repo yet.

## Layout

- `docs/` — process documentation. Start at [`docs/README.md`](docs/README.md):
  the pipeline, the systems involved, and each step's spec, decisions and
  troubleshooting.
- `intake/` — the automation code.
- `processing/` — the Processing sketches that make the Reels (and the Album
  Story, not automated yet).
- `scripts/` — launchers: the hourly Acquire task, and the Make Reels
  double-click.
- `tests/` — run with `python -m pytest`; GitHub runs them on pull requests
  and on pushes to `main`.

## Steps

1. [Acquire](docs/01-acquire.md) — download new Bandcamp purchases into
   `MFYN_Library` on Google Drive. Runs hourly on the MFYN PC. *(live since
   2026-10-23)*
2. [Create the show](docs/02-create-show.md) — pick tracks, make the episode,
   archive it. *(manual)*
   When you're ready to make a show, step 2 is the parent: it starts the
   sub-automations below, each its own step.
   - 2a. [Make Reels](docs/02a-make-reels.md) — the episode's tracks become
     30-second Instagram Reels. Double-click to start. *(built, being tested)*
   - 2b. Instagram copy — a caption for each Reel. *(not built yet; next up)*

**Manual stop:** you review all the content made for a post. When you're happy,
you trigger the Publishing Process (scheduling the posts, among other things).
*(The hand-off isn't built yet.)*

Every automation, what starts it and where it runs is listed in
[`docs/README.md`](docs/README.md#automations).

Where we left off: [`docs/session-log.md`](docs/session-log.md). Open work and
open questions: [GitHub Issues](https://github.com/mfyn-radio/process/issues).
