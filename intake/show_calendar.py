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
from googleapiclient.http import MediaInMemoryUpload

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


def description(event, post, tags=()):
    """The event's notes, in this order:

        Link: …        (only if the post gives one)
        Tags: …
        Notes: …
        With: …

        Save & Share on Instagram
        <post link>

        —
        <caption>
    """
    lines = []
    for label, value in (("Link", event.link), ("Tags", ", ".join(tags)),
                         ("Notes", event.notes), ("With", ", ".join(event.acts))):
        if value:
            lines.append(f"{label}: {value}")
    if lines:
        lines.append("")
    lines += ["Save & Share on Instagram", post.url]
    if post.caption:
        lines += ["", "—", post.caption]
    return "\n".join(lines)


def body(event, post, timezone, tags=(), flyer=None):
    """The Calendar event for an Event read from `post`. `flyer` is the
    attachment from upload_flyer, if any."""
    title = event.title if event.confident else CHECK + event.title
    link = event.link or post.url
    result = {
        "id": event_id(post.shortcode, event),
        "summary": title,
        "description": description(event, post, tags),
        "source": {"title": "Instagram" if link == post.url else event.title, "url": link},
    }
    if flyer:
        result["attachments"] = [flyer]
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
    made = service.events().update(calendarId=calendar_id, eventId=body["id"], body=body,
                                   supportsAttachments=True).execute()
    return (made or {}).get("htmlLink") or "(no link)"


def make_visible(service, calendar_id):
    """Make sure the calendar is in mfyn@'s list in Google Calendar, shown
    and ticked. Returns its name as listed."""
    try:
        entry = service.calendarList().get(calendarId=calendar_id).execute()
    except HttpError as e:
        if e.resp.status != 404:
            raise
        entry = service.calendarList().insert(body={"id": calendar_id, "selected": True}).execute()
    if entry.get("hidden") or not entry.get("selected"):
        entry = service.calendarList().patch(calendarId=calendar_id, body={"hidden": False, "selected": True}).execute()
    return entry.get("summary")


def add(service, calendar_id, event_body):
    """Add the event. Returns its link in Google Calendar, or None if it's
    already on the calendar."""
    try:
        made = service.events().insert(calendarId=calendar_id, body=event_body, supportsAttachments=True).execute()
        return (made or {}).get("htmlLink") or "(no link)"
    except HttpError as e:
        if e.resp.status == 409:  # that id is taken: added on an earlier run
            return None
        raise


# The flyers, in a Drive folder the automation creates (drive.file permission).

def drive_client(creds):
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def create_folder(drive, name):
    body = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    return drive.files().create(body=body, fields="id").execute()["id"]


def flyer_name(event, extension):
    parts = [event.title, event.venue, event.date]
    name = " - ".join(p for p in parts if p)
    return "".join("_" if c in '<>:"/\\|?*' else c for c in name) + extension


def upload_flyer(drive, folder_id, name, image, mime_type):
    """Save the flyer to Drive. Returns it as a Calendar attachment."""
    media = MediaInMemoryUpload(image, mimetype=mime_type)
    made = drive.files().create(body={"name": name, "parents": [folder_id]}, media_body=media,
                                fields="id,webViewLink,mimeType").execute()
    return {"fileId": made["id"], "fileUrl": made["webViewLink"], "title": name, "mimeType": made["mimeType"]}
