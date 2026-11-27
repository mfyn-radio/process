"""Archive the episode: copy a finished episode folder from MFYN_Workspace to
MFYN_Show_Archive, at the start of Make Episode Content (see
docs/02a-make-episode-content.md).

Build Show makes MFYN_Workspace\\2026_December, and Bryant adds the air day
(2026_December_3) once it's known. A folder with a day that has no episode in
the archive with that air date is ready to archive. The archive folder is
named "D_M_YYYY- Episode Name" (3_12_2026- Name), asking for the name.

Everything in the folder is copied (Tracks, the Reaper project, the show cards,
the rendered episode), except Reaper's own caches (.reapeaks, .rpp-bak and
the Backups folder). Each file is checked by size after copying. The local
folder stays put unless config.ARCHIVE_REMOVE_LOCAL is set; an existing archive
folder is never overwritten.

On its own: python -m intake.archive
"""
import argparse
import datetime
import logging
import re
import shutil
import sys

from . import config, episode, runlog

log = logging.getLogger("archive")

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
FOLDER = re.compile(r"^(\d{4})_(" + "|".join(MONTHS) + r")_(\d{1,2})\b", re.IGNORECASE)
SKIP_SUFFIXES = (".reapeaks", ".rpp-bak")
SKIP_DIRS = ("Backups",)


def air_date(folder):
    """The air date in a Workspace folder's name (2026_December_3), or None."""
    m = FOLDER.match(folder.name)
    if not m:
        return None
    month = [x.casefold() for x in MONTHS].index(m.group(2).casefold()) + 1
    try:
        return datetime.date(int(m.group(1)), month, int(m.group(3)))
    except ValueError:
        return None


def pending(work_dir, archive_dir):
    """Workspace folders with an air date that the archive doesn't have yet, oldest first."""
    if not work_dir.is_dir():
        return []
    archived = {e.air_date for e in episode.all_in(archive_dir)} if archive_dir.is_dir() else set()
    found = [(air_date(p), p) for p in work_dir.iterdir() if p.is_dir()]
    return [p for d, p in sorted((d, p) for d, p in found if d and d not in archived)]


def archive_name(day, name):
    return f"{day.day}_{day.month}_{day.year}- {name.strip()}"


def files(src):
    """The files to archive, relative to src."""
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if path.is_file() and path.suffix.lower() not in SKIP_SUFFIXES \
                and not any(part in SKIP_DIRS for part in rel.parts[:-1]):
            yield rel


def copy_folder(src, dest):
    """Copy src into dest (which mustn't exist yet), checking each file's size. Returns the count."""
    if dest.exists():
        raise FileExistsError(f"{dest} already exists; not overwriting it")
    count = 0
    for rel in files(src):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)
        if target.stat().st_size != (src / rel).stat().st_size:
            raise OSError(f"{rel} didn't copy completely")
        count += 1
    return count


def offer(ask=input, say=print, run=None, work_dir=None, archive_dir=None, remove_local=None):
    """Ask whether to archive the newest finished Workspace folder, and do it.
    Returns the archived Episode, or None if nothing was archived."""
    work_dir = work_dir or config.WORK_DIR
    archive_dir = archive_dir or config.SHOW_ARCHIVE_DIR
    remove_local = config.ARCHIVE_REMOVE_LOCAL if remove_local is None else remove_local
    ready = pending(work_dir, archive_dir)
    if not ready:
        undated = [p.name for p in work_dir.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}_[A-Za-z]+", p.name)] \
            if work_dir.is_dir() else []
        if undated:
            say(f"Not archiving {', '.join(undated)}: add the air day to the folder name first (like 2026_December_3).")
        return None
    src = ready[-1]
    day = air_date(src)
    answer = ask(f"\nArchive {src.name} (airs {day:%A %d %B %Y}) to MFYN_Show_Archive? [Y/n] ")
    if answer.strip().lower() not in ("", "y", "yes"):
        return None
    name = ""
    while not name.strip():
        name = ask("Episode name (the archive folder is "
                   f"{archive_name(day, 'Episode Name')}): ")
    dest = archive_dir / archive_name(day, name)
    try:
        count = copy_folder(src, dest)
    except Exception as e:
        log.error("Couldn't archive %s: %s", src.name, e)
        if run:
            run.add(f"{src.name}: Archive", runlog.FAILED, str(e))
        return None
    note = f"{count} file(s) copied to {dest.name}"
    if remove_local:
        shutil.rmtree(src)
        note += f"; removed {src.name} from MFYN_Workspace"
    log.info("Archived: %s", note)
    say(f"Archived: {note}.")
    if run:
        run.add(f"{dest.name}: Archive", runlog.OK, note)
    return episode.parse(dest)


def main(argv=None, ask=input, say=print):
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    def go(run):
        ep = offer(ask, say, run)
        run.summary = f"archived {ep.folder.name}" if ep else "nothing archived"
        return 0
    return runlog.track("Archive", go)


if __name__ == "__main__":
    sys.exit(main())
