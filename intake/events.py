"""Event Calendar: events from saved Instagram posts go on the Event Calendar Google calendar.

Runs on the MFYN PC (daily, from Task Scheduler). See docs/event-calendar.md.

    python -m intake.events --setup-instagram   # one-time Instagram sign-in in Chrome
    python -m intake.events                     # read new saved posts, add their events
    python -m intake.events --dry-run           # show what would be added, change nothing
    python -m intake.events --post SHORTCODE    # just this one post, even if read before
    python -m intake.events --backlog           # also older unread posts, 15 a run
    python -m intake.events --fill-sheet        # Events tab rows for events already on the calendar
"""
import argparse
import datetime
import html
import json
import logging
import logging.handlers
import sys
from dataclasses import dataclass, field

from . import alerts, catalog, config, flyer, gmail, google_auth, instagram, event_calendar, runlog, table

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
    alerts: list = field(default_factory=list)  # alerts.Match for library artists on new events


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
        if place and place not in config.EVENT_COUNTRIES:
            log.info("%s: '%s' on %s is in %s, not the Netherlands or Belgium; skipped",
                     post.url, event.title, when, place)
            continue
        if not place:
            log.warning("%s: couldn't tell which country '%s' is in; added anyway, check it",
                        post.url, event.title)
        tags = event_tags(event, target.catalog)
        body = event_calendar.body(event, post, config.EVENT_TIMEZONE, tags, n)
        mine = alerts.library_artists(target.catalog, event.acts)
        if mine:
            body["colorId"] = config.ALERT_COLOR
        if dry_run:
            if mine:
                log.info("%s: would alert: library artist(s) %s", post.url, ", ".join(mine))
            log.info("%s: would add '%s' on %s at %s (location tag: %s)\n%s", post.url, body["summary"], when,
                     body.get("location", "?"), post.location or "none",
                     event_calendar.description(event, post, tags).replace("<br>", "\n"))
            continue
        old = event_calendar.existing(target.calendar, target.calendar_id, body["id"])
        if old is not None and not redo:
            log.info("%s: '%s' on %s is already on the calendar: %s", post.url, event.title, when,
                     old.get("htmlLink", ""))
            if old.get("status") != "cancelled":
                record_row(target, old, today)
            continue
        if old is None and not redo:
            twin = find_duplicate(target, event, body, post)
            if twin is not None:
                merge_duplicate(target, twin, event, body, post, tags, today)
                continue
        if old is not None:
            link = event_calendar.restore(target.calendar, target.calendar_id, body)
            log.info("%s: rewrote '%s' on %s: %s", post.url, body["summary"], when, link)
        else:
            link = event_calendar.add(target.calendar, target.calendar_id, body)
            if not link:
                continue
            log.info("%s: added '%s' on %s: %s", post.url, body["summary"], when, link)
        # Alert for new events, and for a post redone with --post (so it can be tried).
        if mine:
            log.info("%s: library artist(s) %s; alert coming", post.url, ", ".join(mine))
            target.alerts.append(alerts.Match(mine, body["summary"], event.date, event.start_time or "",
                                              body.get("location", ""), post.url, link))
        added += 1
        record_row(target, body, today)
        if event.location_conflict:
            log.warning("%s: the location tag '%s' differs from the flyer for '%s'; used the tag (%s)",
                        post.url, post.location, event.title, body.get("location", "?"))
        if not event.confident:
            log.warning("%s: the flyer for '%s' wasn't clear; check the event against the post",
                        post.url, event.title)
    return added


# Two saved posts for the same night, such as the venue's and a band's, make one
# event. It keeps the details of the post that has more of them, and links the
# band's own post to repost, since Bryant reposts the band rather than the venue.

def _extra(event_body):
    return event_body.get("extendedProperties", {}).get("private", {})


def _venue_key(event_body):
    venue = _extra(event_body).get("venue") or ""
    if not venue:
        location = event_body.get("location") or ""
        venue = location.rpartition(", ")[0] or location
    return alerts.key(venue)


def _acts(event_body):
    return [a.strip() for a in _extra(event_body).get("acts", "").split(",") if a.strip()]


def band_account(account, acts):
    """Whether an Instagram account is one of the acts' own: sick__pack is
    Sick Pack's, and so is sickpackband."""
    handle = alerts.key(account)
    return bool(handle) and any(
        len(k) >= 4 and (handle.startswith(k) or handle.endswith(k)) for k in map(alerts.key, acts))


def _detail(event_body):
    """How much an event says: a start time first, then how many acts."""
    return ("dateTime" in event_body.get("start", {}), len(_acts(event_body)))


def find_duplicate(target, event, event_body, post):
    """An event from another post on the same date at the same venue, or None."""
    venue = _venue_key(event_body)
    if len(venue) < 3:
        return None
    for other in event_calendar.on_date(target.calendar, target.calendar_id, event.date):
        extra = _extra(other)
        if post.url in (extra.get("post"), extra.get("also")):
            continue  # the same post: a second event that night, or the event itself
        theirs = _venue_key(other)
        if len(theirs) >= 3 and (theirs.startswith(venue) or venue.startswith(theirs)):
            return other
    return None


def merge_duplicate(target, twin, event, event_body, post, tags, today):
    """Fold a second post for an event already on the calendar into that event."""
    old = _extra(twin)
    old_post, old_account = old.get("post", ""), old.get("account", "")
    acts = list(event.acts) + _acts(twin)
    if band_account(post.account, acts) and not band_account(old_account, acts):
        share, account, also = post.url, post.account, old_post
    else:
        share, account, also = old_post or post.url, old_account, post.url
    if _detail(event_body) > _detail(twin):
        # This post says more: its details replace the event's, under the same id.
        fields = {k: event_body[k] for k in ("summary", "start", "end", "source", "location") if k in event_body}
        fields["description"] = event_calendar.description(event, post, tags, share_url=share,
                                                           also=[also] if also and also != share else [])
        private = dict(_extra(event_body))
    else:
        fields = {"description": twin.get("description", "")}
        if share != old_post and old_post:
            fields["description"] = fields["description"].replace(
                f'href="{html.escape(old_post, quote=True)}"', f'href="{html.escape(share, quote=True)}"')
        if also and also != share and also not in fields["description"]:
            fields["description"] += f"<br>Also posted: {html.escape(also)}"
        private = dict(old)
    private.update(post=share, account=account, also=also if also != share else "")
    fields["extendedProperties"] = {"private": {k: v for k, v in private.items() if v}}
    link = event_calendar.patch(target.calendar, target.calendar_id, twin["id"], fields)
    log.info("%s: '%s' on %s is the same event as '%s'; merged into it, reposting %s: %s", post.url,
             event.title, event.date, twin.get("summary", ""), share, link)
    record_row(target, dict(twin, **fields), today)


def record_row(target, event_body, today):
    """Add or fill in the event's row on the Events tab. The calendar is what
    matters, so a problem with the sheet is only logged; --fill-sheet catches
    up later."""
    if target.catalog is None:
        return
    try:
        target.catalog.events.upsert(event_calendar.row(event_body, today.isoformat()))
    except Exception:
        log.exception("couldn't record '%s' on the Events tab", event_body.get("summary"))


def fill_sheet(target, today):
    """Give every event on the calendar a record in the Events table."""
    rows = [event_calendar.row(e, today.isoformat())
            for e in event_calendar.all_events(target.calendar, target.calendar_id)]
    target.catalog.events.upsert_many(rows)   # ten records a call, to save API calls
    log.info("%d event(s) on %s are in the Events table", len(rows), config.EVENT_CALENDAR)


def open_catalog(creds):
    try:
        return catalog.Catalog(creds)
    except Exception:
        log.exception("couldn't open the %s base; tags will come from the posts only", config.CATALOG)
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
    return runlog.track("Event Calendar", lambda run: _main(argv, run))


def _main(argv, run=None):
    run = run or runlog.RunLog("Event Calendar")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--setup-instagram", action="store_true", help="sign in to Instagram as MFYN in Chrome, once")
    parser.add_argument("--dry-run", action="store_true", help="read posts but don't add events or remember the posts")
    parser.add_argument("--backlog", action="store_true",
                        help="also read older posts below ones already read (15 a run; repeat until none are left)")
    parser.add_argument("--fill-sheet", action="store_true",
                        help="give every event already on the calendar a row on the Events tab, then stop")
    parser.add_argument("--post", metavar="SHORTCODE", help="read only this post (the code after /p/ in its link)")
    args = parser.parse_args(argv)
    setup_logging()
    if args.dry_run or args.setup_instagram:
        run.runs = run.last_run = None  # nothing to log

    browser = instagram.Browser(config.INSTAGRAM_PROFILE_DIR)
    try:
        if args.setup_instagram:
            browser.sign_in()
            log.info("Instagram sign-in saved in %s", config.INSTAGRAM_PROFILE_DIR)
            return 0
        if not (args.post or args.fill_sheet) and not config.INSTAGRAM_COLLECTION_URL:
            log.error("Set MFYN_INSTAGRAM_COLLECTION to the collection's address. See docs/event-calendar.md.")
            return 1
        return run_posts(browser, args, run)
    finally:
        browser.close()


def run_posts(browser, args, run=None):
    run = run or runlog.RunLog("Event Calendar")
    state = load_state(config.EVENTS_STATE_FILE)
    creds = None
    if args.dry_run:
        target = Target(catalog=open_catalog(google_auth.credentials()))
    else:
        creds = google_auth.credentials(google_auth.SCOPES)
        target = Target(event_calendar.client(creds), catalog=open_catalog(creds))
        if not state.get("calendar_id"):
            state["calendar_id"] = event_calendar.create(target.calendar, config.EVENT_CALENDAR, config.EVENT_TIMEZONE)
            save_state(config.EVENTS_STATE_FILE, state)
            log.info("Created the %s calendar in mfyn@'s Google Calendar. If it isn't listed there, "
                     "subscribe to it (Other calendars > + > Subscribe to calendar) with this ID: %s",
                     config.EVENT_CALENDAR, state["calendar_id"])
        target.calendar_id = state["calendar_id"]
        try:
            if event_calendar.ensure_name(target.calendar, target.calendar_id, config.EVENT_CALENDAR):
                log.info("Renamed the calendar to %s.", config.EVENT_CALENDAR)
        except Exception as e:  # the name is cosmetic; carry on
            log.warning("Couldn't rename the calendar to %s (%s).", config.EVENT_CALENDAR, e)
    if args.fill_sheet:
        if args.dry_run or target.catalog is None:
            log.error("--fill-sheet needs the %s base and can't be a dry run", config.CATALOG)
            return 1
        fill_sheet(target, datetime.date.today())
        run.summary = "filled in the Events tab from the calendar"
        return 0
    claude = flyer.find_claude()

    if args.post:
        codes = [args.post]
    else:
        codes = browser.collection(config.INSTAGRAM_COLLECTION_URL, set(state["posts"]), config.EVENTS_POSTS_PER_RUN,
                                   backlog=args.backlog)
    log.info("%d new post(s) to read", len(codes))

    today = datetime.date.today()
    failures = total = 0
    for code in codes:
        try:
            post = browser.post(code)
            if args.dry_run:
                log.info("%s: read @%s, posted %s, location tag: %s, image: %s, caption: %r", post.url,
                         post.account or "?", post.posted or "?", post.location or "none",
                         f"{len(post.image) // 1024} KB" if post.image else "none", post.caption[:300])
            events = flyer.read(post, config.EVENTS_MODEL, claude=claude)
            added = handle(post, events, target, today, args.dry_run, redo=bool(args.post))
        except Exception as e:
            log.exception("%s: failed; will retry next run", code)
            run.add(post_link(code), runlog.FAILED, f"{type(e).__name__}: {e}")
            failures += 1
            continue
        if added:
            total += added
            run.add(post.url, runlog.OK, f"{added} event(s) added")
        if not args.dry_run:
            # Remember the post so it isn't read again.
            state["posts"][code] = {"read": today.isoformat(), "events": len(events), "added": added}
            save_state(config.EVENTS_STATE_FILE, state)

    if target.alerts:
        send_alert(creds, target.alerts)

    run.summary = f"{len(codes)} new post(s) read, {total} event(s) added" + (
        f", {failures} failed" if failures else "")
    if failures:
        log.error("%d post(s) failed", failures)
        return 1
    return 0


def post_link(code):
    return f"https://www.instagram.com/p/{code}/"


def send_alert(creds, matches):
    """One email for the run's events with library artists. A failure is only
    logged: the events are on the calendar, with the alert colour, anyway."""
    subject, text = alerts.email(matches)
    try:
        alerts.send(gmail.client(creds), config.ALERT_EMAIL, subject, text)
        log.info("Emailed %s: %s", config.ALERT_EMAIL, subject)
    except Exception:
        log.exception("couldn't send the alert email (%s)", subject)


if __name__ == "__main__":
    sys.exit(main())
