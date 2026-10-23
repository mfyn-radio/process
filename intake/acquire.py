"""Step 1, Acquire: download new Bandcamp purchases into MFYN_Library.

    python -m intake.acquire              # new purchases (hourly job)
    python -m intake.acquire --backlog    # also purchases before START_DATE
    python -m intake.acquire --dry-run    # show what would happen, change nothing
    python -m intake.acquire --message-id ID   # just this one purchase email
"""
import argparse
import datetime
import logging
import sys
import tempfile
import zipfile
from pathlib import Path

from . import bandcamp, config, google_clients, library, purchase_email

log = logging.getLogger("acquire")


def label_id(gmail, name):
    labels = gmail.users().labels().list(userId="me").execute()["labels"]
    for label in labels:
        if label["name"] == name:
            return label["id"]
    return gmail.users().labels().create(userId="me", body={"name": name}).execute()["id"]


def pending_message_ids(gmail, backlog):
    # Gmail search writes nested label names with "-" instead of "/".
    label = config.DONE_LABEL.lower().replace("/", "-").replace(" ", "-")
    query = f"{config.PURCHASE_QUERY} -label:{label}"
    if not backlog:
        query += f" after:{config.START_DATE:%Y/%m/%d}"
    ids, page = [], None
    while True:
        resp = gmail.users().messages().list(userId="me", q=query, pageToken=page).execute()
        ids += [m["id"] for m in resp.get("messages", [])]
        page = resp.get("nextPageToken")
        if not page:
            return list(reversed(ids))  # oldest first


def unpack(downloaded, work_dir):
    """Album downloads are zips: extract them and drop the zip. Single tracks arrive as-is."""
    if not zipfile.is_zipfile(downloaded):
        return [downloaded]
    out = work_dir / "unzipped"
    with zipfile.ZipFile(downloaded) as zf:
        zf.extractall(out)
    downloaded.unlink()
    return sorted(p for p in out.rglob("*") if p.is_file())


def handle(gmail, drive, message_id, today, dry_run):
    """Process one purchase email. Returns True when it's finished and can be labelled."""
    msg = gmail.users().messages().get(userId="me", id=message_id, format="full").execute()
    purchase = purchase_email.parse(message_id, purchase_email.body_text(msg["payload"]))
    if purchase is None:
        log.warning("%s: no download link found, skipping", message_id)
        return False
    if not purchase.is_released(today):
        log.info("%s: pre-order, releases %s; will retry then", message_id, purchase.release_date)
        return False

    items = bandcamp.items(purchase.download_url, config.AUDIO_FORMAT)
    if not items or any(item.format_url is None for item in items):
        log.info("%s: not downloadable yet; will retry next run", message_id)
        return False

    for item in items:
        name = library.folder_name(item.artist, item.title)
        if library.exists(drive, config.LIBRARY_FOLDER_ID, name):
            log.info("%s: '%s' is already in the library", message_id, name)
            continue
        if dry_run:
            log.info("%s: would add '%s'", message_id, name)
            continue
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            log.info("%s: downloading '%s'", message_id, name)
            files = unpack(bandcamp.download(item.format_url, work_dir), work_dir)
            library.add_album(drive, config.LIBRARY_FOLDER_ID, name, files)
            log.info("%s: added '%s' (%d files)", message_id, name, len(files))
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backlog", action="store_true", help=f"include purchases before {config.START_DATE}")
    parser.add_argument("--dry-run", action="store_true", help="don't download, upload or label anything")
    parser.add_argument("--message-id", help="process only this Gmail message, whatever its date or label")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    gmail, drive = google_clients.gmail(), google_clients.drive()
    done_label = None if args.dry_run else label_id(gmail, config.DONE_LABEL)
    today = datetime.date.today()

    message_ids = [args.message_id] if args.message_id else pending_message_ids(gmail, args.backlog)
    log.info("%d purchase email(s) to check", len(message_ids))
    failures = 0
    for message_id in message_ids:
        try:
            finished = handle(gmail, drive, message_id, today, args.dry_run)
        except Exception:
            log.exception("%s: failed; will retry next run", message_id)
            failures += 1
            continue
        if finished and not args.dry_run:
            gmail.users().messages().modify(
                userId="me", id=message_id, body={"addLabelIds": [done_label]}
            ).execute()

    if failures:
        log.error("%d purchase(s) failed", failures)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
