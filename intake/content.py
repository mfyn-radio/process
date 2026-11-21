"""Step 2a, Make Episode Content: one shortcut that runs an episode's content sub-scripts.

Double-click scripts\\make_content.cmd (or its desktop shortcut), or run:

    python -m intake.content                    # the newest episode in MFYN_Show_Archive
    python -m intake.content --episode NAME     # the episode whose folder name contains NAME
    python -m intake.content --skip-handles     # don't stop to confirm Instagram handles

This is only the orchestrator: STEPS below lists the sub-scripts, in the order
they run. The archive cover (with the YouTube playlist cover, one sketch)
always runs; for the others it asks first. Each sub-script is its own module
with one entry point, for_episode(ep, ask=input, ...) -> (ok, summary), and
also runs on its own (python -m intake.<module> --episode NAME). To add one,
write the module and add a line to STEPS. Anything already made is skipped,
so re-running is safe. See docs/02a-make-episode-content.md.
"""
import argparse
import importlib
import inspect
import logging
import random
import sys

from . import config, episode, reels, runlog

log = logging.getLogger("content")

# (module in intake/, what it makes, the question to ask first; None = always runs)
STEPS = (
    ("archive_cover", "Archive cover and YouTube playlist cover", None),
    ("reels", "ON AIR posts and captions", "Do you want ON AIR posts?"),
    ("stories", "Album Stories", "Album Story videos?"),
    ("playlist", "YouTube playlist", "Do you want a YouTube playlist?"),   # needs the playlist cover
)


def available_steps():
    """STEPS with their modules loaded. A sub-script that isn't built yet is left out."""
    steps = []
    for name, label, question in STEPS:
        try:
            module = importlib.import_module(f"intake.{name}")
        except ModuleNotFoundError as e:
            if e.name != f"intake.{name}":
                raise
            continue
        steps.append((module, label, question))
    return steps


def call(step, ep, **options):
    """Run a sub-script's for_episode with the options it takes."""
    accepted = inspect.signature(step.for_episode).parameters
    return step.for_episode(ep, **{k: v for k, v in options.items() if k in accepted})


def yes(answer):
    return answer.strip().lower() in ("", "y", "yes")


def main(argv=None, ask=input, say=print, rng=None):
    return runlog.track("Make Episode Content", lambda run: _main(argv, ask, say, rng, run))


def _main(argv, ask, say, rng, run):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", help="the episode whose folder name contains this")
    parser.add_argument("--skip-handles", action="store_true", help="don't stop to confirm Instagram handles")
    args = parser.parse_args(argv)
    reels.setup_logging(config.CONTENT_LOG_FILE)

    if not config.SHOW_ARCHIVE_DIR.is_dir():
        log.error("Show archive %s not found. Is Google Drive for desktop running?", config.SHOW_ARCHIVE_DIR)
        return 1
    ep = episode.find(config.SHOW_ARCHIVE_DIR, args.episode)
    if ep is None:
        log.error("No episode folder (named like 5_11_2026- Episode Name) found in %s", config.SHOW_ARCHIVE_DIR)
        return 1

    tracks = [reels.read_track(p) for p in ep.tracks()]
    say(f"\nEpisode: {ep.folder.name}  (airs {ep.air_date:%A %d %B %Y})")
    for t in tracks:
        say(f"  {t.artist} - {t.title}")
    if not yes(ask(f"\nMake the content for this episode ({len(tracks)} track(s))? [Y/n] ")):
        run.summary = f"stopped before making anything for {ep.folder.name}"
        return 0

    steps = available_steps()
    always = [label for _, label, question in steps if question is None]
    say(f"\nAlways made: {', '.join(always)}.")
    chosen = [(step, label) for step, label, question in steps
              if question is None or yes(ask(f"{question} [Y/n] "))]

    options = {"ask": ask, "skip_handles": args.skip_handles, "rng": rng or random.Random()}
    results = []
    for step, label in chosen:
        say(f"\n--- {label} ---")
        try:
            ok, summary = call(step, ep, **options)
        except Exception as e:      # one sub-script failing doesn't stop the others
            log.exception("%s crashed", label)
            ok, summary = False, f"crashed: {type(e).__name__}: {e}"
        results.append((label, ok, summary))
        run.add(f"{ep.folder.name}: {label}", runlog.OK if ok else runlog.FAILED, summary)

    log.info("\nDone with %s:", ep.folder.name)
    for label, ok, summary in results:
        (log.info if ok else log.error)("  %s %s: %s", "ok    " if ok else "FAILED", label, summary)
    run.summary = "; ".join(f"{label}: {summary}" for label, _, summary in results)
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
