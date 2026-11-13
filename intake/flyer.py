"""Reading the events out of an Instagram post with Claude.

Event details are usually on the flyer image, not in the caption, so the
image and caption both go to Claude, which returns each event it finds as
structured data. A post that isn't an event comes back with none.
"""
import base64
import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

FALLBACK_BETA = "server-side-fallback-2026-07-01"

PROMPT = """This is an Instagram post that Music for Your Neighbors, a radio show \
about independent music, saved because it may announce a live music event.

Posted by: @{account}
Posted on: {posted}
Caption:
{caption}

List every live event the post announces (a tour poster can list several \
dates). Read the flyer image as well as the caption; flyers often leave out \
the year, so work it out from the posting date (the next such date on or \
after it). Use 24-hour times, local to the venue. Leave a field empty rather \
than guess. Set confident to false if the date, venue or acts are unclear. \
If the post doesn't announce an event (a release, a photo, a past show), \
return no events."""


class Event(BaseModel):
    title: str = Field(description="Short name: the headline act, or the event's own name")
    acts: List[str] = Field(description="Every band or artist on the bill")
    date: str = Field(description="YYYY-MM-DD")
    start_time: Optional[str] = Field(None, description="HH:MM, doors or start, if given")
    end_time: Optional[str] = Field(None, description="HH:MM, if given")
    venue: Optional[str] = None
    city: Optional[str] = None
    tickets: Optional[str] = Field(None, description="Ticket link or price, if given")
    confident: bool


class Events(BaseModel):
    events: List[Event]


def request(post):
    """The message content for one post."""
    content = []
    if post.image:
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": post.image_type,
            "data": base64.standard_b64encode(post.image).decode("ascii")}})
    content.append({"type": "text", "text": PROMPT.format(
        account=post.account or "unknown", posted=post.posted or "unknown",
        caption=post.caption or "(none)")})
    return [{"role": "user", "content": content}]


def read(client, model, post):
    """The events in `post`, as a list of Event. Raises if Claude declines."""
    response = client.beta.messages.parse(
        model=model,
        max_tokens=16000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        messages=request(post),
        output_format=Events,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined to read {post.url}")
    return [e for e in response.parsed_output.events if valid_date(e.date)]


def valid_date(text):
    try:
        datetime.date.fromisoformat(text)
        return True
    except (TypeError, ValueError):
        return False
