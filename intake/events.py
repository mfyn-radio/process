"""Show calendar: events from saved Instagram posts go on the MFYN Shows calendar.

Runs on the MFYN PC (daily, from Task Scheduler). See docs/show-calendar.md.

    python -m intake.events --setup-instagram   # one-time Instagram sign-in in Chrome
    python -m intake.events                     # read new saved posts, add their events
    python -m intake.events --dry-run           # show what would be added, change nothing
    python -m intake.events --post SHORTCODE    # just this one post, even if read before
"""
import argparse
import datetime
import json
import logging
import logging.handlers
import sys

from . import config, flyer, google_auth, instagram, show_calendar

log = logging.getLogger("events")


def load_state(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"calendar_id": None, "posts": {}}


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def handle(post, events, service, calendar_id, today, dry_run):
    """Add a post's upcoming events. Returns how many were added."""
    added = 0
    if not events:
        log.info("%s: no event found", post.url)
    for event in events:
        when = f"{event.date} {event.start_time or ''}".strip()
        if event.date < today.isoformat():
            log.info("%s: '%s' on %s is over; skipped", post.url, event.title, when)
            continue
        body = show_calendar.body(event, post, config.SHOW_TIMEZONE)
        if dry_run:
            log.info("%s: would add '%s' on %s at %s", post.url, body["summary"], when, body.get("location", "?"))
            continue
        if show_calendar.add(service, calendar_id, body):
            added += 1
            log.info("%s: added '%s' on %s", post.url, body["summary"], when)
        else:
            log.info("%s: '%s' on %s is already on the calendar", post.url, event.title, when)
    return added


def setup_logging():
    config.APP_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(config.EVENTS_LOG_FILE, maxBytes=1 << 20, backupCount=3, encoding="utf-8")
    console = logging.StreamHandler()
    for handler in (file_handler, console):
        handler.setFormatter(fmt)
        logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--setup-instagram", action="store_true", help="sign in to Instagram as MFYN in Chrome, once")
    parser.add_argument("--dry-run", action="store_true", help="read posts but don't add events or remember the posts")
    parser.add_argument("--post", metavar="SHORTCODE", help="read only this post (the code after /p/ in its link)")
    args = parser.parse_args(argv)
    setup_logging()

    browser = instagram.Browser(config.INSTAGRAM_PROFILE_DIR)
    try:
        if args.setup_instagram:
            browser.sign_in()
            log.info("Instagram sign-in saved in %s", config.INSTAGRAM_PROFILE_DIR)
            return 0
        if not args.post and not config.INSTAGRAM_COLLECTION_URL:
            log.error("Set MFYN_INSTAGRAM_COLLECTION to the collection's address. See docs/show-calendar.md.")
            return 1
        return run(browser, args)
    finally:
        browser.close()


def run(browser, args):
    import anthropic  # only this automation needs it

    state = load_state(config.EVENTS_STATE_FILE)
    service = None
    if not args.dry_run:
        service = show_calendar.client(google_auth.credentials([google_auth.CALENDAR]))
        if not state["calendar_id"]:
            state["calendar_id"] = show_calendar.create(service, config.SHOW_CALENDAR, config.SHOW_TIMEZONE)
            save_state(config.EVENTS_STATE_FILE, state)
            log.info("Created the %s calendar", config.SHOW_CALENDAR)
    claude = anthropic.Anthropic()

    if args.post:
        codes = [args.post]
    else:
        codes = browser.collection(config.INSTAGRAM_COLLECTION_URL, set(state["posts"]), config.EVENTS_POSTS_PER_RUN)
    log.info("%d new post(s) to read", len(codes))

    today = datetime.date.today()
    failures = 0
    for code in codes:
        try:
            post = browser.post(code)
            events = flyer.read(claude, config.EVENTS_MODEL, post)
            added = handle(post, events, service, state["calendar_id"], today, args.dry_run)
        except Exception:
            log.exception("%s: failed; will retry next run", code)
            failures += 1
            continue
        if not args.dry_run:
            # Remember the post so it isn't read (and paid for) again.
            state["posts"][code] = {"read": today.isoformat(), "events": len(events), "added": added}
            save_state(config.EVENTS_STATE_FILE, state)

    if failures:
        log.error("%d post(s) failed", failures)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
