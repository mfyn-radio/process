"""Step 2b, Instagram copy: a caption for each Reel in MFYN_Reels.

Make Reels runs this at its end, so it normally needs no double-click of its
own. To run it by hand:

    python -m intake.captions                  # the newest episode in MFYN_Reels
    python -m intake.captions --episode NAME   # the episode whose folder name contains NAME

Each Reel's .json gives the track details. Instagram handles are looked up
again in the MFYN Artists sheet, in case one was corrected after the Reel was
made. Only Confirmed handles are tagged; anyone else is credited by name.

A Reel that already has a caption is left alone. To remake one, delete its
.txt and run again. See docs/02b-instagram-copy.md.
"""
import argparse
import datetime
import json
import logging
import sys

from . import catalog, config, episode, google_auth

log = logging.getLogger("captions")

OPENING = "Music worth paying for, follow to find and support an artist"


def nice_date(value):
    """'2026-09-12' -> '12 September 2026'. Anything else is returned as is."""
    try:
        d = datetime.date.fromisoformat(str(value).strip())
    except ValueError:
        return str(value or "").strip()
    return f"{d.day} {d:%B %Y}"


def credit(name, handle, status):
    """@handle when it's confirmed, otherwise the name."""
    handle = (handle or "").strip()
    if handle and (status or "").strip().casefold() == catalog.CONFIRMED.casefold():
        return "@" + handle.lstrip("@")
    return name


def fresh_handles(details, cat):
    """The artist's and label's handle and status, from the sheet if we can
    reach it, otherwise as they were when the Reel was made."""
    artist = (details.get("artist_instagram", ""), details.get("artist_instagram_status", ""))
    label = (details.get("label_instagram", ""), details.get("label_instagram_status", ""))
    if cat:
        _, row = cat.artists.find({"Artist": details.get("artist", "")})
        artist = (row.get("Instagram", ""), row.get("Status", "")) if row else ("", "")
        if details.get("label") and details["label"] != "Self-released":
            _, row = cat.labels.find({"Label": details["label"]})
            label = (row.get("Instagram", ""), row.get("Status", "")) if row else ("", "")
    return artist, label


def caption(details, cat=None):
    """The caption text for one Reel's details."""
    (artist_handle, artist_status), (label_handle, label_status) = fresh_handles(details, cat)
    label = details.get("label", "")
    if label and label != "Self-released":
        label = credit(label, label_handle, label_status)
    ep = details.get("episode") or {}
    air = nice_date(ep.get("air_date", ""))
    if air and ep.get("name"):
        air = f"{air} – {ep['name']}"

    blocks = [
        [OPENING],
        [f"Artist: {credit(details.get('artist', ''), artist_handle, artist_status)}",
         f"Song Title: {details.get('title', '')}" if details.get("title") else "",
         f"Album: {details['album']}" if details.get("album") else ""],
        [f"Label: {label}" if label else "",
         f"Release Date: {nice_date(details['release_date'])}" if details.get("release_date") else ""],
        [f"Air Date: {air}" if air else ""],
    ]
    blocks = [[line for line in block if line] for block in blocks]
    return "\n\n".join("\n".join(block) for block in blocks if block) + "\n"


def write_all(folder, cat=None):
    """Write a caption next to every Reel in `folder` that doesn't have one.
    Returns how many were written."""
    written = 0
    for details_file in sorted(folder.glob("*.json")):
        txt = details_file.with_suffix(".txt")
        if txt.exists():
            continue
        try:
            details = json.loads(details_file.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            log.error("Couldn't read %s (%s); no caption made for it.", details_file.name, e)
            continue
        txt.write_text(caption(details, cat), encoding="utf-8")
        log.info("Wrote caption %s", txt.name)
        written += 1
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", help="the episode whose folder name contains this")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not config.REELS_DIR.is_dir():
        log.error("%s not found. Is Google Drive for desktop running?", config.REELS_DIR)
        return 1
    ep = episode.find(config.REELS_DIR, args.episode)
    if ep is None:
        log.error("No episode folder found in %s", config.REELS_DIR)
        return 1
    try:
        cat = catalog.Catalog(google_auth.credentials())
    except (Exception, SystemExit) as e:
        log.warning("Couldn't open the %s sheet (%s). Using the handles saved with each Reel.",
                    config.ARTISTS_SHEET, e)
        cat = None
    n = write_all(ep.folder, cat)
    log.info("Done: %d caption(s) written in %s", n, ep.folder)
    return 0


if __name__ == "__main__":
    sys.exit(main())
