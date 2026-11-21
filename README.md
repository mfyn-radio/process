# MFYN Intake and Production Process

Code and documentation for the **Music for Your Neighbors (MFYN)** intake and
production process: how a song or artist goes from being *discovered* to having post content ready, and a show ready to play on the radio.

It ends at a manual stop, where you review everything. The separate
**Publishing Process** starts after that. It isn't part of this repo yet.

## Layout

- `docs/` — process documentation. Start at [`docs/README.md`](docs/README.md):
  the pipeline, the systems involved, and each step's spec, decisions and
  troubleshooting.
- `intake/` — the automation code.
- `processing/` — the Processing sketches that make the video posts, the Album
  Stories and the archive covers.
- `scripts/` — launchers: the Acquire and Event Calendar tasks, and the Make Episode Content
  double-click.
- `tests/` — run with `python -m pytest`; GitHub runs them on pull requests
  and on pushes to `main`.

## Steps

1. [Acquire](docs/01-acquire.md) — download new Bandcamp purchases into
   `MFYN_Library` on Google Drive. Runs daily on the MFYN PC. *(live since
   2026-10-23)*
2. [Create the show](docs/02-create-show.md) — pick tracks, make the episode,
   archive it. *(manual)*
   When you're ready to make a show, step 2 is the parent: it starts the
   sub-automations below, each its own step.
   - 2a. [Make Episode Content](docs/02a-make-episode-content.md) — the
     episode's baseline content in one run: archive cover and YouTube playlist
     image, a video post per track and an Album Story per artist. Double-click
     to start. *(built, being tested)*
   - 2b. [Instagram copy](docs/02b-instagram-copy.md) — a caption for each
     video post, written during the 2a run. *(built)*

**Manual stop:** you review all the content made for a post. When you're happy,
you trigger the Publishing Process (scheduling the posts, among other things).
*(The hand-off isn't built yet.)*

Every automation, what starts it and where it runs is listed in
[`docs/README.md`](docs/README.md#automations).

Where we left off: [`docs/session-log.md`](docs/session-log.md). Open work and
open questions: [GitHub Issues](https://github.com/mfyn-radio/process/issues).
