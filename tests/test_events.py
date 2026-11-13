import datetime
import json
from types import SimpleNamespace

import pytest

from intake import events, flyer, google_auth, instagram, show_calendar

POST = instagram.Post(
    shortcode="DAbc123", url="https://www.instagram.com/p/DAbc123/", account="thevenue",
    posted="2026-11-01", caption="Fellatio + Daufødt, Sat 21 Nov, doors 8pm", image=b"\xff\xd8jpeg")


def event(**kw):
    fields = dict(title="Fellatio", acts=["Fellatio", "Daufødt"], date="2026-11-21",
                  start_time="20:00", venue="The Venue", city="Hague", confident=True)
    fields.update(kw)
    return flyer.Event(**fields)


# Instagram pages

def test_shortcodes_from_collection_links_in_order_without_repeats():
    hrefs = ["https://www.instagram.com/p/AAA/", "https://www.instagram.com/mfyn/saved/", None,
             "https://www.instagram.com/reel/BBB/?img_index=1", "https://www.instagram.com/someone/p/AAA/",
             "https://www.instagram.com/explore/"]
    assert instagram.shortcodes(hrefs) == ["AAA", "BBB"]


def test_og_description_splits_into_account_date_and_caption():
    text = '12 likes, 3 comments - the.venue on November 1, 2026: &quot;Doors 8pm: "loud" bands&quot;.'
    assert instagram.parse_description(text) == ("the.venue", "November 1, 2026", 'Doors 8pm: "loud" bands')


def test_og_description_that_doesnt_match_is_kept_as_the_caption():
    assert instagram.parse_description("Just some text") == ("", "", "Just some text")


# Reading the flyer

def test_request_sends_image_then_text_with_the_posting_date():
    content = flyer.request(POST)[0]["content"]
    assert content[0]["type"] == "image" and content[0]["source"]["media_type"] == "image/jpeg"
    text = content[1]["text"]
    assert "@thevenue" in text and "2026-11-01" in text and "Daufødt" in text


def test_request_without_an_image_is_text_only():
    post = instagram.Post("X", "u", caption="hi")
    assert [c["type"] for c in flyer.request(post)[0]["content"]] == ["text"]


class FakeClaude:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

    def parse(self, **kw):
        self.calls.append(kw)
        return self.response


def test_read_returns_events_with_real_dates_and_asks_for_the_schema():
    good, bad = event(), event(date="21 Nov")
    claude = FakeClaude(SimpleNamespace(stop_reason="end_turn", parsed_output=flyer.Events(events=[good, bad])))
    assert flyer.read(claude, "claude-opus-5-5", POST) == [good]
    call = claude.calls[0]
    assert call["output_format"] is flyer.Events and call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"


def test_read_raises_on_refusal_so_the_post_is_retried():
    claude = FakeClaude(SimpleNamespace(stop_reason="refusal", parsed_output=None))
    with pytest.raises(RuntimeError):
        flyer.read(claude, "m", POST)


# The calendar event

def test_timed_event_body():
    body = show_calendar.body(event(), POST, "Europe/Amsterdam")
    assert body["summary"] == "Fellatio"
    assert body["location"] == "The Venue, Hague"
    assert body["start"] == {"dateTime": "2026-11-21T20:00:00", "timeZone": "Europe/Amsterdam"}
    assert body["end"] == {"dateTime": "2026-11-21T23:00:00", "timeZone": "Europe/Amsterdam"}
    assert "With: Fellatio, Daufødt" in body["description"]
    assert POST.url in body["description"] and body["source"]["url"] == POST.url


def test_event_past_midnight_ends_the_next_day():
    body = show_calendar.body(event(start_time="22:00", end_time="02:00"), POST, "UTC")
    assert body["end"]["dateTime"] == "2026-11-22T02:00:00"


def test_event_without_a_time_is_all_day():
    body = show_calendar.body(event(start_time=None), POST, "UTC")
    assert body["start"] == {"date": "2026-11-21"} and body["end"] == {"date": "2026-11-22"}


def test_unreadable_time_becomes_all_day():
    body = show_calendar.body(event(start_time="8pm"), POST, "UTC")
    assert body["start"] == {"date": "2026-11-21"}


def test_unclear_event_is_marked_check():
    body = show_calendar.body(event(confident=False), POST, "UTC")
    assert body["summary"] == "[Check] Fellatio"


def test_event_id_is_stable_and_valid_for_calendar():
    a = show_calendar.event_id("DAbc123", event())
    assert a == show_calendar.event_id("DAbc123", event(start_time="21:00"))
    assert a != show_calendar.event_id("DAbc123", event(date="2026-11-22"))
    assert set(a) <= set("abcdefghijklmnopqrstuv0123456789") and 5 <= len(a) <= 1024


# Adding to the calendar

class FakeCalendar:
    def __init__(self):
        self.added = {}

    def events(self):
        return self

    def insert(self, calendarId, body):
        def execute():
            if body["id"] in self.added:
                from googleapiclient.errors import HttpError
                raise HttpError(SimpleNamespace(status=409, reason="Conflict"), b"duplicate")
            self.added[body["id"]] = body
        return SimpleNamespace(execute=execute)


def test_handle_adds_upcoming_events_once_and_skips_past_ones():
    cal = FakeCalendar()
    today = datetime.date(2026, 11, 13)
    found = [event(), event(title="Old show", date="2026-11-01")]
    assert events.handle(POST, found, cal, "cal", today, dry_run=False) == 1
    assert [b["summary"] for b in cal.added.values()] == ["Fellatio"]
    assert events.handle(POST, found, cal, "cal", today, dry_run=False) == 0  # already there


def test_dry_run_adds_nothing():
    assert events.handle(POST, [event()], None, None, datetime.date(2026, 11, 13), dry_run=True) == 0


def test_state_round_trips(tmp_path):
    path = tmp_path / "events.json"
    state = events.load_state(path)
    assert state == {"calendar_id": None, "posts": {}}
    state["posts"]["DAbc123"] = {"read": "2026-11-13", "events": 1, "added": 1}
    events.save_state(path, state)
    assert json.loads(path.read_text(encoding="utf-8")) == state


# Google sign-in

def test_older_sign_in_without_calendar_still_works_for_the_rest(tmp_path, monkeypatch):
    token = tmp_path / "token.json"
    token.write_text(json.dumps({"scopes": google_auth.BASE_SCOPES, "token": "t", "refresh_token": "r",
                                 "client_id": "c", "client_secret": "s", "expiry": "2999-01-01T00:00:00Z"}))
    monkeypatch.setattr(google_auth.config, "TOKEN_FILE", token)
    assert google_auth.credentials().valid
    with pytest.raises(SystemExit):
        google_auth.credentials([google_auth.CALENDAR])
    assert google_auth.CALENDAR in google_auth.SCOPES  # --setup asks for it
