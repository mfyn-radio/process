"""Show calendar: events from saved Instagram posts go on the MFYN Shows calendar.

Runs on the MFYN PC (daily, from Task Scheduler). See docs/show-calendar.md.

    python -m intake.events --setup-instagram   # one-time Instagram sign-in in Chrome
    python -m intake.events                     # read new saved posts, add their events
    python -m intake.events --dry-run           # show what would be added, change nothing
    python -m intake.events --post SHORTCODE    # just this one post, even if read before
    python -m intake.events --backlog           # also older unread posts, 15 a run
"""
import argparse
import datetime
import json
import logging
import logging.handlers
import sys
from dataclasses import dataclass

from . import catalog, config, flyer, google_auth, instagram, show_calendar, table

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


@dataclass
class Target:
    """Where events go. In a dry run only `catalog` (for tags) is set."""
    calendar: object = None
    calendar_id: str = None
    catalog: object = None


def sheet_tags(catalog, acts):
    """Bandcamp tags from the MFYN Artists sheet for acts already in it,
    leaving out tags that are just the artist's town or country."""
    found = []
    if catalog is None:
        return found
    for act in acts:
        _, row = catalog.artists.find({"Artist": act})
        if not row:
            continue
        places = {p.strip().casefold() for p in (row.get("Location") or "").split(",")}
        found += [t for t in table.split_list(row.get("Tags")) if t.casefold() not in places]
    return found


def event_tags(event, catalog):
    """The post's genres plus the sheet's, lowercase, sorted, without repeats."""
    return sorted({t.strip().lower() for t in event.tags + sheet_tags(catalog, event.acts) if t.strip()})


COUNTRY_NAMES = {
    "netherlands": "Netherlands", "the netherlands": "Netherlands", "nederland": "Netherlands",
    "holland": "Netherlands", "nl": "Netherlands",
    "belgium": "Belgium", "belgië": "Belgium", "belgie": "Belgium", "belgique": "Belgium",
    "belgien": "Belgium", "be": "Belgium",
}


def country(event):
    """The event's country, tidied (e.g. "Nederland" is "Netherlands"), or None."""
    name = (event.country or "").strip()
    return COUNTRY_NAMES.get(name.casefold(), name) or None


def handle(post, events, target, today, dry_run, redo=False):
    """Add a post's upcoming events. Returns how many were added or
    rewritten. An event already on the calendar is left alone, even if
    you've edited or deleted it, unless `redo` (the post was named with
    --post): then it's rewritten with the current layout."""
    added = 0
    seen = {}  # events per date in this post, for their ids
    if not events:
        log.info("%s: no event found", post.url)
    for event in events:
        n = seen[event.date] = seen.get(event.date, -1) + 1
        when = f"{event.date} {event.start_time or ''}".strip()
        if event.date < today.isoformat():
            log.info("%s: '%s' on %s is over; skipped", post.url, event.title, when)
            continue
        place = country(event)
        if place and place not in config.SHOW_COUNTRIES:
            log.info("%s: '%s' on %s is in %s, not the Netherlands or Belgium; skipped",
                     post.url, event.title, when, place)
            continue
        if not place:
            log.warning("%s: couldn't tell which country '%s' is in; added anyway, check it",
                        post.url, event.title)
        tags = event_tags(event, target.catalog)
        body = show_calendar.body(event, post, config.SHOW_TIMEZONE, tags, n)
        if dry_run:
            log.info("%s: would add '%s' on %s at %s\n%s", post.url, body["summary"], when,
                     body.get("location", "?"), show_calendar.description(event, post, tags).replace("<br>", "\n"))
            continue
        old = show_calendar.existing(target.calendar, target.calendar_id, body["id"])
        if old is not None and not redo:
            log.info("%s: '%s' on %s is already on the calendar: %s", post.url, event.title, when,
                     old.get("htmlLink", ""))
            continue
        if old is not None:
            link = show_calendar.restore(target.calendar, target.calendar_id, body)
            log.info("%s: rewrote '%s' on %s: %s", post.url, body["summary"], when, link)
        else:
            link = show_calendar.add(target.calendar, target.calendar_id, body)
            if not link:
                continue
            log.info("%s: added '%s' on %s: %s", post.url, body["summary"], when, link)
        added += 1
        if event.location_conflict:
            log.warning("%s: the location tag '%s' differs from the flyer for '%s'; used the tag (%s)",
                        post.url, post.location, event.title, body.get("location", "?"))
        if not event.confident:
            log.warning("%s: the flyer for '%s' wasn't clear; check the event against the post",
                        post.url, event.title)
    return added


def open_catalog(creds):
    try:
        return catalog.Catalog(creds)
    except Exception:
        log.exception("couldn't open the %s sheet; tags will come from the posts only", config.ARTISTS_SHEET)
        return None


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
    parser.add_argument("--backlog", action="store_true",
                        help="also read older posts below ones already read (15 a run; repeat until none are left)")
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
    state = load_state(config.EVENTS_STATE_FILE)
    if args.dry_run:
        target = Target(catalog=open_catalog(google_auth.credentials()))
    else:
        creds = google_auth.credentials(google_auth.SCOPES)
        target = Target(show_calendar.client(creds), catalog=open_catalog(creds))
        if not state.get("calendar_id"):
            state["calendar_id"] = show_calendar.create(target.calendar, config.SHOW_CALENDAR, config.SHOW_TIMEZONE)
            save_state(config.EVENTS_STATE_FILE, state)
            log.info("Created the %s calendar in mfyn@'s Google Calendar. If it isn't listed there, "
                     "subscribe to it (Other calendars > + > Subscribe to calendar) with this ID: %s",
                     config.SHOW_CALENDAR, state["calendar_id"])
        target.calendar_id = state["calendar_id"]
    claude = flyer.find_claude()

    if args.post:
        codes = [args.post]
    else:
        codes = browser.collection(config.INSTAGRAM_COLLECTION_URL, set(state["posts"]), config.EVENTS_POSTS_PER_RUN,
                                   backlog=args.backlog)
    log.info("%d new post(s) to read", len(codes))

    today = datetime.date.today()
    failures = 0
    for code in codes:
        try:
            post = browser.post(code)
            events = flyer.read(post, config.EVENTS_MODEL, claude=claude)
            added = handle(post, events, target, today, args.dry_run, redo=bool(args.post))
        except Exception:
            log.exception("%s: failed; will retry next run", code)
            failures += 1
            continue
        if not args.dry_run:
            # Remember the post so it isn't read again.
            state["posts"][code] = {"read": today.isoformat(), "events": len(events), "added": added}
            save_state(config.EVENTS_STATE_FILE, state)

    if failures:
        log.error("%d post(s) failed", failures)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
