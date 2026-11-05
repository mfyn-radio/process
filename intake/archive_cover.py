"""The archive cover for an episode in MFYN_Show_Archive.

Make Reels runs this first, so it normally needs no double-click of its own.
To run it by hand:

    python -m intake.archive_cover                  # the newest episode
    python -m intake.archive_cover --episode NAME   # the episode whose folder name contains NAME

The date comes from the episode folder's name (5_11_2026-... is 5 November
2026). The number counts up from config.ARCHIVE_FIRST_NUMBER (No. 3, the
5 November 2026 episode), one per episode folder, in air-date order. The
cover is saved in the episode folder as MFYN_archive_03.png; an episode that
already has its cover is skipped. See docs/archive-cover.md.
"""
import argparse
import logging
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


def make(ep, episodes):
    """Render the episode's cover into its folder. Returns the path, or None
    if the episode gets no cover or it couldn't be made."""
    number = number_for(ep, episodes)
    if number is None:
        log.info("%s is before %s, so it gets no archive cover.", ep.folder.name, cover_date(config.ARCHIVE_FIRST_DATE))
        return None
    target = ep.folder / cover_name(number)
    if target.exists():
        log.info("Archive cover %s is already there.", target.name)
        return target
    with tempfile.TemporaryDirectory(prefix="mfyn-archive-") as tmp:
        cmd = reels.processing_command() + [
            f"--sketch={config.ARCHIVE_SKETCH}", "--run",
            f"number={number}", f"date={cover_date(ep.air_date)}", f"output={tmp}",
        ]
        log.info("Making archive cover No. %02d (%s).", number, cover_date(ep.air_date))
        result = subprocess.run(cmd)
        made = Path(tmp) / cover_name(number)
        if result.returncode != 0 or not made.exists():
            log.error("No archive cover was made for %s (Processing exited with code %d).",
                      ep.folder.name, result.returncode)
            return None
        shutil.move(made, target)
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
