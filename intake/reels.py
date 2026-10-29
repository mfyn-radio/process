"""Step 2a, Make Reels: turn an episode's tracks into 30-second Instagram Reels.

Double-click scripts\\make_reels.cmd (or its desktop shortcut), or run:

    python -m intake.reels                    # the newest episode in MFYN_Show_Archive
    python -m intake.reels --episode NAME     # the episode whose folder name contains NAME
    python -m intake.reels --skip-handles     # don't stop to confirm Instagram handles

See docs/02a-make-reels.md.
"""
import argparse
import datetime
import json
import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import mutagen

from . import catalog, config, episode, google_auth, handles, library

log = logging.getLogger("reels")


@dataclass
class Track:
    path: Path
    artist: str
    title: str
    album: str = ""
    track_number: str = ""
    year: str = ""


def read_track(path):
    tags = mutagen.File(path, easy=True) or {}

    def tag(*keys):
        for key in keys:
            values = tags.get(key) if hasattr(tags, "get") else None
            if values and str(values[0]).strip():
                return str(values[0]).strip()
        return ""

    return Track(
        path=path,
        artist=tag("artist", "albumartist") or "Unknown Artist",
        title=tag("title") or path.stem,
        album=tag("album"),
        track_number=tag("tracknumber"),
        year=tag("date"),
    )


def reel_names(tracks):
    """`Artist - Title` for each track, numbered if two would clash."""
    names, seen = [], {}
    for track in tracks:
        name = library.clean(f"{track.artist} - {track.title}")
        seen[name.casefold()] = seen.get(name.casefold(), 0) + 1
        names.append(name if seen[name.casefold()] == 1 else f"{name} ({seen[name.casefold()]})")
    return names


def processing_command():
    """The command that runs a Processing sketch from the command line."""
    if config.PROCESSING:
        exe = Path(config.PROCESSING)
        return [str(exe), "cli"] if exe.stem.lower() == "processing" else [str(exe)]
    found = shutil.which("processing-java")
    if found:
        return [found]
    roots = [Path(os.environ.get(v, "")) for v in ("ProgramFiles", "LOCALAPPDATA", "ProgramFiles(x86)")]
    for root in roots:
        for folder in (root / "Processing", root / "Programs" / "Processing"):
            if (folder / "processing-java.exe").exists():
                return [str(folder / "processing-java.exe")]
            # Processing 4.4 and later: the app itself has a "cli" mode.
            if (folder / "Processing.exe").exists():
                return [str(folder / "Processing.exe"), "cli"]
    raise SystemExit("Can't find Processing's command-line runner. Set MFYN_PROCESSING to the full path "
                     "of processing-java.exe (or Processing.exe).")


def render(tracks, out_dir, seconds):
    """Run the Reel sketch on these tracks. Returns {track path: rendered mp4}."""
    with tempfile.TemporaryDirectory(prefix="mfyn-reels-") as tmp:
        staging_in, staging_out = Path(tmp) / "input", Path(tmp) / "output"
        staging_in.mkdir()
        staging_out.mkdir()
        # Copies, so the sketch only sees the tracks that still need a Reel.
        for track in tracks:
            shutil.copy2(track.path, staging_in / track.path.name)
        cmd = processing_command() + [
            f"--sketch={config.REEL_SKETCH}", "--run",
            f"input={staging_in}", f"output={staging_out}", f"seconds={seconds}",
        ]
        log.info("Rendering %d Reel(s) with Processing. A preview window opens while it works.", len(tracks))
        result = subprocess.run(cmd)
        if result.returncode != 0:
            log.error("Processing exited with code %d", result.returncode)
        rendered = {}
        for track in tracks:
            mp4 = staging_out / f"{track.path.stem}_reel.mp4"
            if mp4.exists():
                kept = out_dir / mp4.name
                shutil.move(mp4, kept)
                rendered[track.path] = kept
        return rendered


def details(track, ep, cat, seconds):
    """What step 2c needs to write the post. Handles are as of now; step 2c
    looks them up again in case they've changed since."""
    artist, release, label = {}, {}, {}
    if cat:
        _, artist = cat.artists.find({"Artist": track.artist})
        artist = artist or {}
        release = next((r for r in cat.releases.rows if r.get("Album", "").casefold() == track.album.casefold()
                        and track.album), {})
        if release.get("Label") and release["Label"] != "Self-released":
            _, label = cat.labels.find({"Label": release["Label"]})
            label = label or {}
    return {
        "artist": track.artist,
        "title": track.title,
        "album": track.album,
        "track_number": track.track_number,
        "year": track.year,
        "label": release.get("Label", ""),
        "release_date": release.get("Release date", ""),
        "album_link": release.get("Album link", ""),
        "tags": release.get("Tags", ""),
        "artist_instagram": artist.get("Instagram", ""),
        "artist_instagram_status": artist.get("Status", ""),
        "artist_website": artist.get("Website", ""),
        "artist_other_links": [l for l in artist.get("Other links", "").splitlines() if l],
        "label_instagram": label.get("Instagram", ""),
        "label_instagram_status": label.get("Status", ""),
        "episode": {"name": ep.name, "air_date": ep.air_date.isoformat(), "folder": ep.folder.name},
        "source_track": track.path.name,
        "clip_seconds": seconds,
        "made": datetime.datetime.now().isoformat(timespec="seconds"),
    }


def labels_for(tracks, cat):
    albums = {t.album.casefold() for t in tracks if t.album}
    labels = []
    for row in cat.releases.rows:
        label = row.get("Label", "").strip()
        if row.get("Album", "").casefold() in albums and label and label != "Self-released" and label not in labels:
            labels.append(label)
    return labels


def setup_logging():
    config.APP_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(config.REELS_LOG_FILE, maxBytes=1 << 20, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(message)s"))
    for handler in (file_handler, console):
        logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


def main(argv=None, ask=input):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", help="make Reels for the episode whose folder name contains this")
    parser.add_argument("--skip-handles", action="store_true", help="don't stop to confirm Instagram handles")
    args = parser.parse_args(argv)
    setup_logging()

    if not config.SHOW_ARCHIVE_DIR.is_dir():
        log.error("Show archive %s not found. Is Google Drive for desktop running?", config.SHOW_ARCHIVE_DIR)
        return 1
    ep = episode.find(config.SHOW_ARCHIVE_DIR, args.episode)
    if ep is None:
        log.error("No episode folder (named like 5_11_2026- Episode Name) found in %s", config.SHOW_ARCHIVE_DIR)
        return 1
    tracks = [read_track(p) for p in ep.tracks()]
    if not tracks:
        log.error("'%s' has no audio files in its Tracks folder.", ep.folder.name)
        return 1

    print(f"\nEpisode: {ep.folder.name}  (airs {ep.air_date:%A %d %B %Y})")
    for t in tracks:
        print(f"  {t.artist} - {t.title}")
    if ask(f"\nMake Reels for these {len(tracks)} track(s)? [Y/n] ").strip().lower() not in ("", "y", "yes"):
        return 0

    try:
        cat = catalog.Catalog(google_auth.credentials())
    except (Exception, SystemExit) as e:
        log.warning("Couldn't open the %s sheet (%s). Reels will be made without Instagram handles.",
                    config.ARTISTS_SHEET, e)
        cat = None

    if cat and not args.skip_handles:
        print("\nInstagram handles. Only ones that aren't confirmed yet are asked about.")
        handles.confirm(cat.artists, list(dict.fromkeys(t.artist for t in tracks)), "artist", ask=ask)
        handles.confirm(cat.labels, labels_for(tracks, cat), "label", ask=ask)

    out_dir = config.REELS_DIR / ep.folder.name
    out_dir.mkdir(parents=True, exist_ok=True)
    names = dict(zip((t.path for t in tracks), reel_names(tracks)))
    pending = [t for t in tracks if not (out_dir / f"{names[t.path]}.mp4").exists()]
    if len(pending) < len(tracks):
        log.info("%d track(s) already have a Reel; skipping them.", len(tracks) - len(pending))

    made = render(pending, out_dir, config.REEL_SECONDS) if pending else {}
    for track in pending:
        mp4 = made.get(track.path)
        if mp4 is None:
            log.error("No Reel was made for %s", track.path.name)
            continue
        name = names[track.path]
        mp4.replace(out_dir / f"{name}.mp4")
        (out_dir / f"{name}.json").write_text(
            json.dumps(details(track, ep, cat, config.REEL_SECONDS), indent=2, ensure_ascii=False), encoding="utf-8")
        log.info("Made %s.mp4", name)

    failed = len(pending) - len(made)
    log.info("\nDone: %d Reel(s) made, %d failed. They're in %s", len(made), failed, out_dir)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
