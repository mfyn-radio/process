"""The MFYN Shows Google calendar.

The automation creates the calendar itself and may only touch calendars it
created (the calendar.app.created permission). Each event gets an id made
from its post, so a re-run never adds it twice, and an event that's already
there is left alone, even if you've edited it.
"""
import datetime
import hashlib
import html
import re

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def client(creds):
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def create(service, name, timezone):
    """Create the calendar and return its id."""
    body = {"summary": name, "timeZone": timezone,
            "description": "Shows from posts saved to MFYN's Instagram collection. Made by the MFYN automation."}
    return service.calendars().insert(body=body).execute()["id"]


def event_id(shortcode, event, n=0):
    """A stable Calendar event id for one event in one post: the post, the
    date, and `n` for a second event on the same date. Not the title, which
    Claude may word differently on a rerun. Calendar ids use the letters a-v
    and digits, so a hex digest fits."""
    key = f"{shortcode}|{event.date}|{n}"
    return "mf" + hashlib.sha1(key.encode("utf-8")).hexdigest()


def description(event, post, tags=()):
    """The event's notes, as Calendar's simple HTML:

        punk, hardcore, noise           (the tags, if any)

        <the post's caption>

        Save & Share on Instagram       (a link to the post)
    """
    parts = []
    if tags:
        parts.append(html.escape(", ".join(tags)))
    if post.caption:
        parts.append(html.escape(post.caption.strip()).replace("\n", "<br>"))
    parts.append(f'<a href="{html.escape(post.url, quote=True)}">Save &amp; Share on Instagram</a>')
    return "<br><br>".join(parts)


def body(event, post, timezone, tags=(), n=0):
    """The Calendar event for an Event read from `post`."""
    link = event.link or post.url
    result = {
        "id": event_id(post.shortcode, event, n),
        "summary": event.title,
        "description": description(event, post, tags),
        "source": {"title": "Instagram" if link == post.url else event.title, "url": link},
        # The details, kept with the event so the Events tab can be rebuilt from the calendar.
        "extendedProperties": {"private": {k: v[:1000] for k, v in {
            "venue": event.venue or "", "city": event.city or "", "country": event.country or "",
            "acts": ", ".join(event.acts), "tags": ", ".join(tags), "link": event.link or "",
            "post": post.url, "location_tag": getattr(post, "location", "") or "",
        }.items() if v}},
    }
    location = ", ".join(p for p in (event.venue, event.city) if p)
    if location:
        result["location"] = location
    day = datetime.date.fromisoformat(event.date)
    start_time, end_time = clock(event.start_time), clock(event.end_time)
    if start_time:
        start = datetime.datetime.combine(day, start_time)
        end = None
        if end_time:
            end = datetime.datetime.combine(day, end_time)
            if end <= start:
                end += datetime.timedelta(days=1)  # runs past midnight
        end = end or start + datetime.timedelta(hours=3)
        result["start"] = {"dateTime": start.isoformat(), "timeZone": timezone}
        result["end"] = {"dateTime": end.isoformat(), "timeZone": timezone}
    else:
        result["start"] = {"date": day.isoformat()}
        result["end"] = {"date": (day + datetime.timedelta(days=1)).isoformat()}
    return result


def clock(text):
    """HH:MM as a time, or None if it's missing or not a time."""
    try:
        return datetime.time.fromisoformat(text) if text else None
    except ValueError:
        return None


def existing(service, calendar_id, eid):
    """The event if an earlier run added it (a deleted one has status
    "cancelled"), else None."""
    try:
        return service.events().get(calendarId=calendar_id, eventId=eid).execute()
    except HttpError as e:
        if e.resp.status in (404, 410):
            return None
        raise


def restore(service, calendar_id, event_body):
    """Rewrite an event (putting it back if it was deleted)."""
    body = dict(event_body, status="confirmed")
    made = service.events().update(calendarId=calendar_id, eventId=body["id"], body=body).execute()
    return (made or {}).get("htmlLink") or "(no link)"


def add(service, calendar_id, event_body):
    """Add the event. Returns its link in Google Calendar, or None if it's
    already on the calendar."""
    try:
        made = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return (made or {}).get("htmlLink") or "(no link)"
    except HttpError as e:
        if e.resp.status == 409:  # that id is taken: added on an earlier run
            return None
        raise


# Rows for the Events tab of the MFYN Artists sheet.

def _date_and_time(when):
    """("2026-11-28", "20:00") from a Calendar start or end; no time for all-day."""
    if "dateTime" in when:
        return when["dateTime"][:10], when["dateTime"][11:16]
    return when.get("date", ""), ""


def row(event_body, added):
    """The Events tab row for a Calendar event, from the details kept with it.
    Older events without them get what the title, place and dates give."""
    extra = event_body.get("extendedProperties", {}).get("private", {})
    date, start = _date_and_time(event_body.get("start", {}))
    end_date, end = _date_and_time(event_body.get("end", {}))
    venue, city = extra.get("venue", ""), extra.get("city", "")
    if not (venue or city) and event_body.get("location"):
        venue, _, city = event_body["location"].rpartition(", ")
    post = extra.get("post", "")
    if not post:
        found = re.search(r'href="([^"]+)"', event_body.get("description", ""))
        post = html.unescape(found.group(1)) if found else ""
    source = event_body.get("source", {}).get("url", "")
    return {
        "Date": date, "Start": start, "End": end, "Title": event_body.get("summary", ""),
        "Venue": venue, "City": city, "Country": extra.get("country", ""),
        "Acts": extra.get("acts", ""),
        "Tags": [t.strip() for t in extra.get("tags", "").split(",") if t.strip()],
        "Link": extra.get("link", "") or (source if source and source != post else ""),
        "Post": post, "Location tag": extra.get("location_tag", ""),
        "Event id": event_body.get("id", ""), "Added": added,
    }


def all_events(service, calendar_id):
    """Every event on the calendar, not counting deleted ones."""
    page = None
    while True:
        resp = service.events().list(calendarId=calendar_id, pageToken=page, showDeleted=False,
                                     singleEvents=True, maxResults=250).execute()
        yield from resp.get("items", [])
        page = resp.get("nextPageToken")
        if not page:
            return
