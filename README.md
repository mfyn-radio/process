# MFYN Intake Process

Code and documentation for the **Music for Your Neighbors (MFYN)** intake process:
how a song or artist goes from being *discovered* to having content ready to
post on Instagram and play on the radio show.

## Layout

- `docs/` — process documentation. Start at [`docs/README.md`](docs/README.md):
  the pipeline, the systems involved, and each step's spec, decisions and
  troubleshooting.
- `intake/` — the automation code.
- `scripts/` — launchers, like the one Task Scheduler runs.
- `tests/` — run with `python -m pytest`; GitHub runs them on every push.

## Steps

1. [Acquire](docs/01-acquire.md) — download new Bandcamp purchases into
   `MFYN_Library` on Google Drive. Runs hourly on the MFYN PC. *(live since
   2026-10-23)*
