"""Show cards: spoken on-air intros for each artist on the playlist, and an
events card to close the show. Written by Build Show into the episode folder
as show_cards.md, for Bryant to edit. See docs/show-cards.md.

The facts are gathered here, so the cards only use what's verified: each
release's Bandcamp page (read in Chrome), the MFYN Catalog's Artists, and the
upcoming Events. Claude Code on the PC (`claude -p`, on MFYN's Claude
subscription, as the Event Calendar's flyer reading) then writes the cards
from those facts alone, with no tools.
"""
import datetime
import json
import logging
import subprocess
import tempfile

from . import config

log = logging.getLogger("show_cards")

FILE_NAME = "show_cards.md"
EVENT_WEEKS = 6

STYLE = """You write the show cards for Music for Your Neighbors (MFYN), a radio show in
Rotterdam about music and local scenes in the BeNe region (Belgium, Netherlands).
The host, Bryant, reads the cards out on air. Write in English, in Markdown.

Write one card per artist, in playlist order. An artist with several tracks gets
one card that introduces them all.
- Heading: "## N. Artist (City)", using the play number of the artist's first track.
  Add " · local" for artists from Belgium or the Netherlands. Leave out the city
  if it isn't in the facts.
- Then a spoken intro of 3 to 5 sentences, ready to read aloud. Use a
  conversational radio voice: who they are, where they're from, what it sounds
  like, one hook (the story behind the release, a guest, a cause, a credit), and
  the track's name. Hand off from place to place ("Over to Sheffield now") so the
  show travels. Never write a fact sheet or bullet points.
- If the artist has an upcoming event in the facts, say so in the intro (day,
  venue, city).
- Then one line in italics, which isn't read out: "*Link: <url>*", plus any care
  note. Keep explicit or sensitive titles (suicide, sexual, slurs) out of the
  spoken text, and name them in the care note. If a fact such as the location is
  missing, say so in this line instead of guessing.

The last card is "## Events: get out to a show". It's a spoken closing segment
covering the upcoming events in the facts, in date order, with weekday, venue,
city and start time where known. Lead with Rotterdam, then the rest of the BeNe
region, then one or two further ahead. End by pointing listeners to the MFYN
event calendar. Then one italic line listing any events you left out (no city,
looks private), and why.

Rules: use only the facts below; never add facts from memory. Get weekdays from
the dates given. Start the reply with "# Show cards: <playlist title>" and
return only the Markdown.
"""


def key(text):
    from .build_show import key as build_key
    return build_key(text)


def release_facts(browser, url):
    """What a release's Bandcamp page says, or {} if it can't be read."""
    from . import release_info
    try:
        r = release_info.parse(browser.read_page(url))
    except Exception as e:            # one unreadable page doesn't stop the cards
        log.warning("Couldn't read %s: %s", url, e)
        return {}
    return {k: v for k, v in {
        "album": r.album, "artist": r.artist, "label": None if r.self_released else r.label,
        "released": r.release_date, "tags": r.tags, "credits": r.credits,
        "bandcamp_location": r.seller.location, "bandcamp_bio": r.seller.bio,
    }.items() if v}


def upcoming(events, today, weeks=EVENT_WEEKS):
    """Events from today to `weeks` ahead, in date order."""
    until = today + datetime.timedelta(weeks=weeks)
    found = []
    for e in events:
        try:
            day = datetime.date.fromisoformat((e.get("Date") or "")[:10])
        except ValueError:
            continue
        if today <= day <= until:
            found.append({"date": day.isoformat(), "weekday": f"{day:%A}",
                          **{k.lower(): e.get(k) for k in ("Start", "Title", "Venue", "City", "Country", "Acts", "Link")
                             if e.get(k)}})
    return sorted(found, key=lambda e: (e["date"], e.get("start") or ""))


def artist_events(name, events):
    """The events whose title or acts name this artist."""
    wanted = key(name)
    if not wanted:
        return []
    found = []
    for e in events:
        acts = [key(a) for a in (e.get("acts") or "").split(",")]
        title = key(e.get("title", ""))
        # Titles often read "Band + Band" or "Promoter x Band": a long enough name inside counts.
        if wanted in acts or wanted == title or (len(wanted) >= 6 and wanted in title):
            found.append(e)
    return found


def facts(title, wanted, pages, artists, events):
    """Everything the cards may say, as one JSON-ready dict.
    pages: {release url: release_facts}, artists: Catalog Artists rows."""
    by_name = {key(a.get("Artist")): a for a in artists}
    cards, order = {}, []
    for w in wanted:
        k = key(w.artist)
        if k not in cards:
            row = by_name.get(k, {})
            cards[k] = {"artist": w.artist, "first_play": w.number, "tracks": [],
                        **{f.lower(): row.get(f) for f in ("Location", "Bio", "Tags") if row.get(f)},
                        "upcoming_events": artist_events(w.artist, events)}
            order.append(k)
        page = pages.get(w.url) or pages.get(album_url(w)) or {}
        cards[k]["tracks"].append({"play": w.number, "title": w.title, "album": w.album or None,
                                   "link": album_url(w) or w.url, **page})
    return {"playlist": title, "artists": [cards[k] for k in order], "events": events}


def album_url(w):
    return w.album_url or ""


def prompt(data):
    return STYLE + "\nFacts (JSON):\n" + json.dumps(data, ensure_ascii=False, indent=1)


def command(claude, model=None):
    cmd = [claude, "-p", "--output-format", "json", "--tools", "", "--no-session-persistence",
           "--strict-mcp-config"]
    return cmd + (["--model", model] if model else [])


def write_cards(data, model=None, run=subprocess.run, claude=None):
    """The cards' Markdown, from Claude Code."""
    from .flyer import find_claude
    claude = claude or find_claude()
    with tempfile.TemporaryDirectory(prefix="mfyn-cards-") as tmp:
        result = run(command(claude, model), input=prompt(data), cwd=tmp,
                     capture_output=True, text=True, encoding="utf-8", timeout=900)
    try:
        reply = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError(f"Claude Code didn't reply with JSON: {result.stdout[:300]!r} {result.stderr[:300]!r}")
    text = reply.get("result")
    if reply.get("is_error") or not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"Claude Code failed: {reply.get('subtype')} {str(text)[:300]!r}")
    return text.strip() + "\n"


def make(work, title, wanted, today=None, read_pages=None, catalog=None, writer=write_cards):
    """Write show_cards.md in the episode folder. Returns its path."""
    today = today or datetime.date.today()
    if catalog is None:
        from .catalog import Catalog
        catalog = Catalog()
    artists = list(catalog.artists.rows)
    events = upcoming(catalog.events.rows, today)
    pages = (read_pages or read_release_pages)(wanted)
    data = facts(title, wanted, pages, artists, events)
    path = work / FILE_NAME
    path.write_text(writer(data, model=config.EVENTS_MODEL or None), encoding="utf-8")
    return path


def read_release_pages(wanted):
    """Each release's Bandcamp page, read once, in Chrome."""
    from .bandcamp import Browser
    browser = Browser(config.APP_DIR)
    pages = {}
    try:
        for w in wanted:
            url = album_url(w) or w.url
            if url and url not in pages:
                pages[url] = release_facts(browser, url)
    finally:
        browser.close()
    return pages
