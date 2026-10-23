# MFYN Intake Process

Code and documentation for the **Music for Your Neighbors (MFYN)** intake process:
how a song or artist goes from being *discovered* to having content ready to
post on Instagram and play on the radio show.

## Layout

- `docs/` — process documentation: the steps in the pipeline, who/what does each
  one, inputs and outputs, and decisions made along the way.
- `intake/` — the automation code, one module per step.
- `.github/workflows/` — the scheduled jobs that run it.
- `scripts/` — one-off helpers, like the Google sign-in script.
- `tests/` — run with `pytest`.

## Steps

1. [Acquire](docs/01-acquire.md) — download new Bandcamp purchases into
   `MFYN_Library` on Google Drive. *(built, being tested)*
