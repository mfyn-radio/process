import datetime
import json
from pathlib import Path
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

def test_prompt_names_the_flyer_file_and_gives_the_posting_date():
    text = flyer.prompt(POST, "flyer.jpg")
    assert "flyer.jpg" in text and "@thevenue" in text and "2026-11-01" in text and "Daufødt" in text
    assert "Flyer image:" not in flyer.prompt(instagram.Post("X", "u", caption="hi"))


def test_command_only_allows_reading_files_when_there_is_an_image():
    with_image = flyer.command("claude", True, "opus")
    assert with_image[with_image.index("--tools") + 1] == "Read"
    assert "--allowedTools" in with_image and with_image[-2:] == ["--model", "opus"]
    schema = json.loads(with_image[with_image.index("--json-schema") + 1])
    assert schema["properties"]["events"]["items"]["required"][0] == "title"
    without = flyer.command("claude", False)
    assert without[without.index("--tools") + 1] == "" and "--allowedTools" not in without and "--model" not in without


def reply(events, **kw):
    return json.dumps({"type": "result", "subtype": "success", "is_error": False,
                       "structured_output": {"events": events}, **kw})


def test_parse_keeps_events_with_real_dates():
    good = {"title": "Fellatio", "acts": ["Fellatio", "Daufødt"], "date": "2026-11-21", "start_time": "20:00",
            "end_time": None, "venue": "WORM", "city": "Rotterdam", "tickets": None, "confident": True}
    found = flyer.parse(reply([good, {**good, "date": "21 Nov"}]))
    assert found == [flyer.Event(title="Fellatio", acts=["Fellatio", "Daufødt"], date="2026-11-21",
                                 start_time="20:00", venue="WORM", city="Rotterdam", confident=True)]


def test_parse_raises_on_an_error_so_the_post_is_retried():
    with pytest.raises(RuntimeError):
        flyer.parse(json.dumps({"is_error": True, "subtype": "error_max_turns", "result": "x"}))
    with pytest.raises(RuntimeError):
        flyer.parse("Not logged in")


def test_read_saves_the_flyer_and_runs_claude_code_there(tmp_path):
    seen = {}

    def run(cmd, input, cwd, **kw):
        seen["cmd"], seen["files"] = cmd, {p.name: p.read_bytes() for p in Path(cwd).iterdir()}
        seen["prompt"] = input
        return SimpleNamespace(returncode=0, stdout=reply([]), stderr="")

    assert flyer.read(POST, run=run, claude="claude.exe") == []
    assert seen["files"] == {"flyer.jpg": POST.image}
    assert seen["cmd"][:2] == ["claude.exe", "-p"] and "flyer.jpg" in seen["prompt"]


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
