"""The MFYN Shows Google calendar.

The automation creates the calendar itself and may only touch calendars it
created (the calendar.app.created permission). Each event gets an id made
from its post, so a re-run never adds it twice, and an event that's already
there is left alone, even if you've edited it.
"""
import datetime
import hashlib

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CHECK = "[Check] "


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


def body(event, post, timezone):
    """The Calendar event for an Event read from `post`."""
    title = event.title if event.confident else CHECK + event.title
    lines = []
    if event.acts:
        lines.append("With: " + ", ".join(event.acts))
    if event.tickets:
        lines.append("Tickets: " + event.tickets)
    lines.append(f"From @{post.account}'s post: {post.url}" if post.account else f"From: {post.url}")
    if not event.confident:
        lines.append("Check the details against the post; the flyer wasn't clear.")
    if post.caption:
        lines += ["", post.caption]
    result = {
        "id": event_id(post.shortcode, event),
        "summary": title,
        "description": "\n".join(lines),
        "source": {"title": "Instagram", "url": post.url},
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


def add(service, calendar_id, event_body):
    """Add the event. Returns False if it's already on the calendar."""
    try:
        service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return True
    except HttpError as e:
        if e.resp.status == 409:  # that id is taken: added on an earlier run
            return False
        raise
