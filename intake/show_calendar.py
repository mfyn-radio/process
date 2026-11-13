"""The MFYN Shows Google calendar.

The automation creates the calendar itself and may only touch calendars it
created (the calendar.app.created permission). Each event gets an id made
from its post, so a re-run never adds it twice, and an event that's already
there is left alone, even if you've edited it.
"""
import datetime
import hashlib
import html

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def client(creds):
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def create(service, name, timezone):
    """Create the calendar and return its id."""
    body = {"summary": name, "timeZone": timezone,
            "description": "Shows from posts saved to MFYN's Instagram collection. Made by the MFYN automation."}
    return service.calendars().insert(body=body).execute()["id"]


def event_id(shortcode, event):
    """A stable Calendar event id for one event in one post. Calendar ids use
    the letters a-v and digits, so a hex digest fits."""
    key = f"{shortcode}|{event.date}|{event.title.casefold()}"
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


def body(event, post, timezone, tags=()):
    """The Calendar event for an Event read from `post`."""
    link = event.link or post.url
    result = {
        "id": event_id(post.shortcode, event),
        "summary": event.title,
        "description": description(event, post, tags),
        "source": {"title": "Instagram" if link == post.url else event.title, "url": link},
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
    """Put back an event that was deleted, as new."""
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
