"""Step 1, Acquire: download new Bandcamp purchases into MFYN_Library.

Runs on the MFYN PC (hourly, from Task Scheduler). See docs/01-acquire.md.

    python -m intake.acquire --setup CLIENT_JSON   # one-time Gmail sign-in
    python -m intake.acquire                       # new purchases
    python -m intake.acquire --backlog             # also purchases before START_DATE
    python -m intake.acquire --dry-run             # show what would happen, change nothing
    python -m intake.acquire --message-id ID       # just this one purchase email
    python -m intake.acquire --artists             # fill the MFYN Artists sheet from the whole library
"""
import argparse
import datetime
import logging
import logging.handlers
import sys
import tempfile
from pathlib import Path

from . import bandcamp, catalog, config, gmail, google_auth, library, purchase_email

log = logging.getLogger("acquire")


def pending_message_ids(service, backlog):
    query = config.PURCHASE_QUERY
    for name in (config.DONE_LABEL, config.EXCLUDED_LABEL):
        # Gmail search writes nested label names with "-" instead of "/".
        query += " -label:" + name.lower().replace("/", "-").replace(" ", "-")
    if not backlog:
        query += f" after:{config.START_DATE:%Y/%m/%d}"
    ids, page = [], None
    while True:
        resp = service.users().messages().list(userId="me", q=query, pageToken=page).execute()
        ids += [m["id"] for m in resp.get("messages", [])]
        page = resp.get("nextPageToken")
        if not page:
            return list(reversed(ids))  # oldest first


def handle(service, browser, sheet, message_id, today, dry_run):
    """Process one purchase email. Returns the label to add once it's finished
    (DONE_LABEL or EXCLUDED_LABEL), or None to leave it for a later run."""
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    purchase = purchase_email.parse(message_id, purchase_email.body_text(msg["payload"]))
    if purchase is None:
        log.warning("%s: no download link found, skipping", message_id)
        return None
    excluded = {s.casefold() for s in config.EXCLUDED_SELLERS}
    if purchase.seller and purchase.seller.casefold() in excluded:
        log.info("%s: from %s, which is excluded", message_id, purchase.seller)
        return config.EXCLUDED_LABEL
    if not purchase.is_released(today):
        log.info("%s: pre-order, releases %s; will retry then", message_id, purchase.release_date)
        return None
    if dry_run:
        log.info("%s: would download from %s", message_id, purchase.seller)
        return None

    try:
        downloaded = browser.download(purchase.download_url, config.AUDIO_FORMAT)
    except bandcamp.NotAvailable as e:
        log.info("%s: not downloadable yet (%s); will retry next run", message_id, e)
        return None
    # Bandcamp names downloads "Artist - Album.zip", which is the folder name we want.
    name = library.clean(downloaded.stem)
    if (config.LIBRARY_DIR / name).exists():
        log.info("%s: '%s' is already in the library", message_id, name)
        downloaded.unlink()
        return config.DONE_LABEL
    files = library.add(config.LIBRARY_DIR, name, downloaded)
    log.info("%s: added '%s' (%d files)", message_id, name, len(files))
    purchased = datetime.datetime.fromtimestamp(int(msg["internalDate"]) / 1000).date().isoformat()
    record_artists(sheet, browser, config.LIBRARY_DIR / name, purchased, browser.last_album_url)
    return config.DONE_LABEL


def open_artists_sheet(creds):
    # Downloading doesn't depend on the sheet, so carry on without it.
    try:
        return catalog.Catalog(creds)
    except Exception:
        log.exception("couldn't open the %s sheet; artists won't be recorded this run", config.ARTISTS_SHEET)
        return None


def record_artists(sheet, browser, folder, purchased=None, album_url=None):
    # The album is safely in the library by now, so a problem here is only
    # logged; `--artists` fills in anything that was missed.
    if sheet is None:
        return
    try:
        catalog.record(sheet, browser, folder, log, purchased, album_url)
    except Exception:
        log.exception("'%s': couldn't update the %s sheet", folder.name, config.ARTISTS_SHEET)


def backfill_artists(sheet, browser):
    """Fill in the sheet from every album already in the library."""
    for folder in sorted(p for p in config.LIBRARY_DIR.iterdir() if p.is_dir()):
        if not folder.name.startswith(library.PARTIAL_PREFIX):
            record_artists(sheet, browser, folder)


def setup_logging():
    config.APP_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(config.LOG_FILE, maxBytes=1 << 20, backupCount=3, encoding="utf-8")
    console = logging.StreamHandler()
    for handler in (file_handler, console):
        handler.setFormatter(fmt)
        logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--setup", metavar="CLIENT_JSON", help="sign in to Google as mfyn@ using this OAuth client file")
    parser.add_argument("--backlog", action="store_true", help=f"include purchases before {config.START_DATE}")
    parser.add_argument("--dry-run", action="store_true", help="don't download, add or label anything")
    parser.add_argument("--message-id", help="process only this Gmail message, whatever its date or label")
    parser.add_argument("--artists", action="store_true", help=f"fill the {config.ARTISTS_SHEET} sheet from the whole library, then stop")
    args = parser.parse_args(argv)
    setup_logging()

    if args.setup:
        google_auth.setup(args.setup)
        log.info("Signed in. Token saved to %s", config.TOKEN_FILE)
        return 0
    if not config.LIBRARY_DIR.is_dir():
        log.error("Library folder %s not found. Is Google Drive for desktop running?", config.LIBRARY_DIR)
        return 1

    creds = google_auth.credentials()
    service = gmail.client(creds)
    sheet = None if args.dry_run else open_artists_sheet(creds)
    label_ids = {} if args.dry_run else {
        name: gmail.label_id(service, name) for name in (config.DONE_LABEL, config.EXCLUDED_LABEL)
    }
    today = datetime.date.today()
    message_ids = [] if args.artists else (
        [args.message_id] if args.message_id else pending_message_ids(service, args.backlog)
    )
    if not args.artists:
        log.info("%d purchase email(s) to check", len(message_ids))

    failures = 0
    with tempfile.TemporaryDirectory(prefix="mfyn-") as tmp:
        browser = bandcamp.Browser(Path(tmp))
        try:
            if args.artists and sheet:
                backfill_artists(sheet, browser)
            for message_id in message_ids:
                try:
                    label = handle(service, browser, sheet, message_id, today, args.dry_run)
                except Exception:
                    log.exception("%s: failed; will retry next run", message_id)
                    failures += 1
                    continue
                if label and not args.dry_run:
                    service.users().messages().modify(
                        userId="me", id=message_id, body={"addLabelIds": [label_ids[label]]}
                    ).execute()
        finally:
            browser.close()

    if failures:
        log.error("%d purchase(s) failed", failures)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
