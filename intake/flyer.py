"""Reading the events out of an Instagram post with Claude.

Event details are usually on the flyer image, not in the caption, so the
image and caption both go to Claude, which returns each event it finds as
structured data. A post that isn't an event comes back with none.

Claude is reached through Claude Code on the MFYN PC (`claude -p`), signed in
with MFYN's Claude subscription, so there's no API key or separate bill. The
flyer is saved to a temporary folder and Claude Code reads it with its Read
tool, the only tool it's given.
"""
import datetime
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

PROMPT = """This is an Instagram post that Music for Your Neighbors, a radio show \
about independent music, saved because it may announce a live music event.

Posted by: @{account}
Posted on: {posted}
{image}
Caption:
{caption}

List every live event the post announces (a tour poster can list several \
dates). Read the flyer image as well as the caption; flyers often leave out \
the year, so work it out from the posting date (the next such date on or \
after it). Use 24-hour HH:MM times, local to the venue, and YYYY-MM-DD dates. \
For link, give a web address written in the post for tickets or the event \
(tickets first); "link in bio" is not a link. For notes, give short practical \
details: price, cash only, age limit, free entry, sold out, set times, the \
address. For tags, give the music genres the post itself names or hashtags \
(e.g. punk, hardcore), lowercase, as words (#noiserock is noise rock), not \
places. Leave a field null rather than guess. Set confident to false if the date, \
venue or acts are unclear. If the post doesn't announce an event (a release, \
a photo, a past show), return no events."""

IMAGE_LINE = "Flyer image: the file {name} in the current folder. Read it first.\n"

TEXT = {"type": "string"}
MAYBE = {"type": ["string", "null"]}
SCHEMA = {
    "type": "object",
    "properties": {"events": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short name: the headline act, or the event's own name"},
            "acts": {"type": "array", "items": TEXT, "description": "Every band or artist on the bill"},
            "date": {"type": "string", "description": "YYYY-MM-DD"},
            "start_time": {**MAYBE, "description": "HH:MM, doors or start, if given"},
            "end_time": {**MAYBE, "description": "HH:MM, if given"},
            "venue": MAYBE,
            "city": MAYBE,
            "link": {**MAYBE, "description": "Tickets or event web address written in the post"},
            "notes": {**MAYBE, "description": "Practical details: price, cash only, 18+, set times, address"},
            "tags": {"type": "array", "items": TEXT, "description": "Music genres the post names, lowercase"},
            "confident": {"type": "boolean"},
        },
        "required": ["title", "acts", "date", "start_time", "end_time", "venue", "city", "link", "notes",
                     "tags", "confident"],
        "additionalProperties": False,
    }}},
    "required": ["events"],
    "additionalProperties": False,
}

EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}


@dataclass
class Event:
    title: str
    date: str
    acts: List[str] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    venue: Optional[str] = None
    city: Optional[str] = None
    link: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    confident: bool = False


def prompt(post, image_name=None):
    return PROMPT.format(
        account=post.account or "unknown", posted=post.posted or "unknown",
        image=IMAGE_LINE.format(name=image_name) if image_name else "",
        caption=post.caption or "(none)")


def command(claude, image, model=None):
    """The `claude -p` command line. The prompt goes in on stdin."""
    cmd = [claude, "-p", "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
           "--tools", "Read" if image else "", "--no-session-persistence", "--strict-mcp-config"]
    if image:
        cmd += ["--allowedTools", "Read"]
    if model:
        cmd += ["--model", model]
    return cmd


def find_claude():
    """Claude Code: on the PATH, or where its Windows installer puts it."""
    found = shutil.which("claude")
    if not found:
        installed = Path.home() / ".local" / "bin" / "claude.exe"
        found = str(installed) if installed.exists() else None
    if not found:
        raise SystemExit("Claude Code isn't installed on this PC. See docs/show-calendar.md.")
    return found


def parse(stdout):
    """The events from Claude Code's JSON reply. Raises if it went wrong."""
    try:
        reply = json.loads(stdout)
    except ValueError:
        raise RuntimeError(f"Claude Code didn't reply with JSON: {stdout[:300]!r}")
    output = reply.get("structured_output")
    if reply.get("is_error") or not isinstance(output, dict):
        raise RuntimeError(f"Claude Code failed: {reply.get('subtype')} {str(reply.get('result'))[:300]!r}")
    events = []
    for item in output.get("events") or []:
        known = {k: item.get(k) for k in Event.__dataclass_fields__ if k in item}
        if isinstance(known.get("title"), str) and valid_date(known.get("date")):
            for name in ("acts", "tags"):
                known[name] = [a for a in known.get(name) or [] if isinstance(a, str) and a.strip()]
            known["link"] = web_address(known.get("link"))
            known["confident"] = bool(known.get("confident"))
            events.append(Event(**known))
    return events


def read(post, model=None, run=subprocess.run, claude=None):
    """The events in `post`, as a list of Event."""
    claude = claude or find_claude()
    with tempfile.TemporaryDirectory(prefix="mfyn-flyer-") as tmp:
        name = None
        if post.image:
            name = "flyer" + EXTENSIONS.get(post.image_type, ".jpg")
            (Path(tmp) / name).write_bytes(post.image)
        result = run(command(claude, bool(name), model), input=prompt(post, name), cwd=tmp,
                     capture_output=True, text=True, encoding="utf-8", timeout=600)
    if result.returncode and not result.stdout:
        raise RuntimeError(f"Claude Code exited with {result.returncode}: {result.stderr[:300]}")
    return parse(result.stdout)


def web_address(text):
    """A clickable address, or None. Captions often leave off https://."""
    if not isinstance(text, str) or not text.strip() or " " in text.strip():
        return None
    text = text.strip()
    if text.startswith(("http://", "https://")):
        return text
    return "https://" + text if "." in text else None


def valid_date(text):
    try:
        datetime.date.fromisoformat(text)
        return True
    except (TypeError, ValueError):
        return False
