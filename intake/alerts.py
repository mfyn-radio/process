""""Your artist is playing": shows with a library artist on the bill.

When the show calendar adds a show whose acts include an artist on the
Artists tab of the MFYN Artists sheet, the event gets the alert colour and
the run sends one email from mfyn@ listing those shows. See
docs/show-calendar.md.
"""
import base64
import datetime
import re
import unicodedata
from dataclasses import dataclass
from email.message import EmailMessage

# Letters that don't split into a plain letter plus an accent.
FOLD = str.maketrans({"ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "ß": "ss",
                      "đ": "d", "Đ": "d", "ł": "l", "Ł": "l", "þ": "th", "Þ": "th"})


def key(name):
    """A name for matching: no case, accents, punctuation or leading "The".
    "Daufødt" and "DAUFODT" match; so do "The Ex" and "Ex"."""
    text = unicodedata.normalize("NFKD", (name or "").translate(FOLD))
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    text = re.sub(r"[^0-9a-z]+", " ", text).strip()
    return re.sub(r"^the ", "", text).replace(" ", "")


def library_artists(catalog, acts):
    """The library artists among `acts`, as the sheet spells them."""
    if catalog is None:
        return []
    known = {}
    for row in catalog.artists.rows:
        name = (row.get("Artist") or "").strip()
        if key(name):
            known.setdefault(key(name), name)
    found = []
    for act in acts:
        name = known.get(key(act))
        if name and name not in found:
            found.append(name)
    return found


@dataclass
class Match:
    artists: list
    title: str
    date: str
    start: str
    place: str
    post: str
    calendar_link: str


def when(match):
    day = datetime.date.fromisoformat(match.date).strftime("%a %d %b %Y")
    return f"{day}, {match.start}" if match.start else day


def email(matches):
    """(subject, text) for one run's matches."""
    names = sorted({a for m in matches for a in m.artists}, key=str.casefold)
    subject = "MFYN: " + (f"{names[0]} is playing" if len(names) == 1 else f"{len(names)} library artists are playing")
    lines = ["Library artists on the bill of new shows on MFYN Shows:", ""]
    for m in sorted(matches, key=lambda m: (m.date, m.start)):
        names = ", ".join(m.artists)
        same = [key(a) for a in m.artists] == [key(m.title)]  # the show is named after the artist
        lines += [names if same else f"{names}: {m.title}",
                  f"{when(m)}" + (f", {m.place}" if m.place else ""),
                  f"Post: {m.post}"]
        if m.calendar_link:
            lines.append(f"Calendar: {m.calendar_link}")
        lines.append("")
    return subject, "\n".join(lines)


def send(gmail, to, subject, text):
    msg = EmailMessage()
    msg["To"], msg["Subject"] = to, subject
    msg.set_content(text)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    gmail.users().messages().send(userId="me", body={"raw": raw}).execute()
