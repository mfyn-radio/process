"""The archive cover for an episode in MFYN_Show_Archive.

Make Reels runs this first, so it normally needs no double-click of its own.
To run it by hand:

    python -m intake.archive_cover                  # the newest episode
    python -m intake.archive_cover --episode NAME   # the episode whose folder name contains NAME

The date comes from the episode folder's name (5_11_2026-... is 5 November
2026). The number counts up from config.ARCHIVE_FIRST_NUMBER (No. 3, the
5 November 2026 episode), one per episode folder, in air-date order. The
cover is saved in the episode folder as MFYN_archive_03.png; an episode that
already has its cover is skipped.

Each new cover gets a random paper colour. It opens so you can look at it,
and you're asked whether to keep it; say no and another one is made. See
docs/archive-cover.md.
"""
import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config, episode, reels

log = logging.getLogger("archive_cover")


def number_for(ep, episodes):
    """The episode's archive number, or None for episodes before the first one."""
    if ep.air_date < config.ARCHIVE_FIRST_DATE:
        return None
    counted = sorted((e for e in episodes if e.air_date >= config.ARCHIVE_FIRST_DATE),
                     key=lambda e: (e.air_date, e.folder.name))
    names = [e.folder.name for e in counted]
    return config.ARCHIVE_FIRST_NUMBER + names.index(ep.folder.name)


def cover_date(d):
    """5 November 2026: day without a leading zero, month spelled out."""
    return f"{d.day} {d:%B %Y}"


def cover_name(number):
    return f"MFYN_archive_{number:02d}.png"


def open_image(path):
    """Show the cover in the PC's image viewer."""
    if hasattr(os, "startfile"):
        os.startfile(path)
    else:
        log.info("Have a look at %s", path)


def make(ep, episodes, ask=input, show=open_image):
    """Render the episode's cover, show it, and save it into the episode
    folder once you keep it; a new colour each time you don't. Returns the
    path, or None if the episode gets no cover or it couldn't be made."""
    number = number_for(ep, episodes)
    if number is None:
        log.info("%s is before %s, so it gets no archive cover.", ep.folder.name, cover_date(config.ARCHIVE_FIRST_DATE))
        return None
    target = ep.folder / cover_name(number)
    if target.exists():
        log.info("Archive cover %s is already there.", target.name)
        return target
    # The image viewer may still have a shown cover open, which Windows won't
    # let us move or delete: copy the kept one, and tidy up what we can.
    tmp = tempfile.mkdtemp(prefix="mfyn-archive-")
    try:
        attempt = 0
        while True:
            attempt += 1
            out = Path(tmp) / str(attempt)          # a new file each time, so the viewer shows the new one
            out.mkdir()
            cmd = reels.processing_command() + [
                f"--sketch={config.ARCHIVE_SKETCH}", "--run",
                f"number={number}", f"date={cover_date(ep.air_date)}", f"output={out}",
            ]
            log.info("Making archive cover No. %02d (%s).", number, cover_date(ep.air_date))
            result = subprocess.run(cmd)
            made = out / cover_name(number)
            if result.returncode != 0 or not made.exists():
                log.error("No archive cover was made for %s (Processing exited with code %d).",
                          ep.folder.name, result.returncode)
                return None
            show(made)
            answer = ask("Keep this cover? [Y = keep, n = make another with a new colour] ").strip().lower()
            if answer in ("", "y", "yes"):
                break
        shutil.copyfile(made, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    log.info("Made %s in %s", target.name, ep.folder)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", help="the episode whose folder name contains this")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not config.SHOW_ARCHIVE_DIR.is_dir():
        log.error("Show archive %s not found. Is Google Drive for desktop running?", config.SHOW_ARCHIVE_DIR)
        return 1
    ep = episode.find(config.SHOW_ARCHIVE_DIR, args.episode)
    if ep is None:
        log.error("No episode folder (named like 5_11_2026- Episode Name) found in %s", config.SHOW_ARCHIVE_DIR)
        return 1
    made = make(ep, episode.all_in(config.SHOW_ARCHIVE_DIR))
    return 0 if made or number_for(ep, episode.all_in(config.SHOW_ARCHIVE_DIR)) is None else 1


if __name__ == "__main__":
    sys.exit(main())
