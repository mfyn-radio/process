import datetime
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from intake import alerts, events, flyer, google_auth, instagram, show_calendar

POST = instagram.Post(
    shortcode="DAbc123", url="https://www.instagram.com/p/DAbc123/", account="thevenue",
    posted="2026-11-01", caption="Fellatio + Daufødt, Sat 21 Nov, doors 8pm", image=b"\xff\xd8jpeg")


def event(**kw):
    fields = dict(title="Fellatio", acts=["Fellatio", "Daufødt"], date="2026-11-21",
                  start_time="20:00", venue="The Venue", city="Hague", country="Netherlands", confident=True)
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


class FakeGrid:
    """A saved-posts page that shows `window` posts at a time and moves down
    by `step` posts on each scroll, like Instagram's grid."""

    def __init__(self, codes, window=12, step=6):
        self.codes, self.window, self.step, self.top = codes, window, step, 0
        self.current_url = "https://www.instagram.com/mfyn_thing/saved/events/1/"

    def find_elements(self, by, css):
        shown = self.codes[self.top:self.top + self.window]
        return [SimpleNamespace(get_attribute=lambda name, c=c: f"https://www.instagram.com/p/{c}/") for c in shown]

    def execute_script(self, script):
        self.top = min(self.top + self.step, max(len(self.codes) - self.window, 0))


def collection(codes, known, limit=15, backlog=False):
    browser = instagram.Browser("profile")
    grid = FakeGrid(codes)
    browser._open = lambda url: grid
    return browser.collection("u", set(known), limit, backlog=backlog)


def test_collection_takes_the_newest_15_and_stops_at_a_post_already_read(monkeypatch):
    monkeypatch.setattr(instagram, "pause", lambda *a: None)
    codes = [f"P{i:02}" for i in range(37)]  # newest first
    first = collection(codes, [])
    assert first == codes[:15]
    assert collection(codes, first) == []  # stops at P00: older posts aren't reached
    assert collection(["N1", "N2"] + codes, first) == ["N1", "N2"]


def test_backlog_reads_older_posts_below_ones_already_read(monkeypatch):
    monkeypatch.setattr(instagram, "pause", lambda *a: None)
    codes = [f"P{i:02}" for i in range(37)]
    read = codes[:1]  # the post tested with --post
    runs = []
    while True:
        new = collection(codes, read, backlog=True)
        if not new:
            break
        runs.append(new)
        read += new
    assert [len(r) for r in runs] == [15, 15, 6] and sorted(read) == codes


def test_collection_picks_up_a_new_post_at_the_top(monkeypatch):
    monkeypatch.setattr(instagram, "pause", lambda *a: None)
    codes = ["NEW"] + [f"P{i:02}" for i in range(37)]
    assert collection(codes, codes[1:]) == ["NEW"]


def test_location_tag_is_the_first_named_place_link():
    links = [("https://www.instagram.com/thevenue/", "thevenue"),
             ("https://www.instagram.com/explore/locations/123/", " "),
             ("https://www.instagram.com/explore/locations/456/worm/", "WORM\n Rotterdam")]
    assert instagram.location_tag(links) == "WORM Rotterdam"
    assert instagram.location_tag([("https://www.instagram.com/p/X/", "post")]) == ""


# Reading the flyer

def test_prompt_names_the_flyer_file_and_gives_the_posting_date():
    text = flyer.prompt(POST, "flyer.jpg")
    assert "flyer.jpg" in text and "@thevenue" in text and "2026-11-01" in text and "Daufødt" in text
    assert "Flyer image:" not in flyer.prompt(instagram.Post("X", "u", caption="hi"))


def test_prompt_gives_the_location_tag_and_says_it_wins_only_when_there_is_one():
    tagged = instagram.Post("X", "u", caption="hi", location="WORM Rotterdam")
    text = flyer.prompt(tagged, "flyer.jpg")
    assert "Location tag: WORM Rotterdam" in text and "even if the flyer" in text
    untagged = flyer.prompt(instagram.Post("X", "u", caption="hi"), "flyer.jpg")
    assert "Location tag" not in untagged and "location_conflict to true" not in untagged


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
            "end_time": None, "venue": "WORM", "city": "Rotterdam", "link": "worm.org/agenda/fellatio",
            "notes": "Cash only. 18+.", "tags": ["Hardcore", " "], "confident": True}
    found = flyer.parse(reply([good, {**good, "date": "21 Nov"}]))
    assert found == [flyer.Event(title="Fellatio", acts=["Fellatio", "Daufødt"], date="2026-11-21",
                                 start_time="20:00", venue="WORM", city="Rotterdam",
                                 link="https://worm.org/agenda/fellatio", notes="Cash only. 18+.",
                                 tags=["Hardcore"], confident=True)]


def test_only_real_web_addresses_count_as_links():
    assert flyer.web_address("https://worm.org/x") == "https://worm.org/x"
    assert flyer.web_address("worm.org") == "https://worm.org"
    assert flyer.web_address("link in bio") is None
    assert flyer.web_address(None) is None


def test_parse_raises_on_an_error_so_the_post_is_retried():
    with pytest.raises(RuntimeError):
        flyer.parse(json.dumps({"is_error": True, "subtype": "error_max_turns", "result": "x"}))
    with pytest.raises(RuntimeError):
        flyer.parse("Not logged in")


def test_claude_is_found_where_the_installer_puts_it_even_off_the_path(tmp_path, monkeypatch):
    monkeypatch.setattr(flyer.shutil, "which", lambda name: None)
    monkeypatch.setattr(flyer.Path, "home", lambda: tmp_path)
    with pytest.raises(SystemExit):
        flyer.find_claude()
    exe = tmp_path / ".local" / "bin" / "claude.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    assert flyer.find_claude() == str(exe)


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
    assert body["source"]["url"] == POST.url  # no link in the post


def test_description_follows_the_agreed_layout():
    post = instagram.Post("DAbc123", "https://www.instagram.com/p/DAbc123/",
                          caption="28th of November.. Check out these names..\n\nOnly €18,50 & vinyl <3")
    assert show_calendar.description(event(), post, ["alternative", "kraut"]) == (
        "alternative, kraut<br><br>"
        "28th of November.. Check out these names..<br><br>Only €18,50 &amp; vinyl &lt;3<br><br>"
        '<a href="https://www.instagram.com/p/DAbc123/">Save &amp; Share on Instagram</a>')


def test_description_leaves_out_empty_parts():
    text = show_calendar.description(event(), instagram.Post("X", "https://i/p/X/"))
    assert text == '<a href="https://i/p/X/">Save &amp; Share on Instagram</a>'


def test_post_link_is_the_source_unless_the_post_gives_one():
    body = show_calendar.body(event(link="https://worm.org/x"), POST, "UTC")
    assert body["source"]["url"] == "https://worm.org/x"


def test_event_past_midnight_ends_the_next_day():
    body = show_calendar.body(event(start_time="22:00", end_time="02:00"), POST, "UTC")
    assert body["end"]["dateTime"] == "2026-11-22T02:00:00"


def test_event_without_a_time_is_all_day():
    body = show_calendar.body(event(start_time=None), POST, "UTC")
    assert body["start"] == {"date": "2026-11-21"} and body["end"] == {"date": "2026-11-22"}


def test_unreadable_time_becomes_all_day():
    body = show_calendar.body(event(start_time="8pm"), POST, "UTC")
    assert body["start"] == {"date": "2026-11-21"}


def test_unclear_event_keeps_its_plain_title():
    body = show_calendar.body(event(confident=False), POST, "UTC")
    assert body["summary"] == "Fellatio"  # no "[Check]": an unclear flyer is only noted in the log


def test_event_id_is_stable_and_valid_for_calendar():
    a = show_calendar.event_id("DAbc123", event())
    assert a == show_calendar.event_id("DAbc123", event(title="FELLATIO live", start_time="21:00"))
    assert a != show_calendar.event_id("DAbc123", event(date="2026-11-22"))
    assert a != show_calendar.event_id("DAbc123", event(), 1)
    assert set(a) <= set("abcdefghijklmnopqrstuv0123456789") and 5 <= len(a) <= 1024


# Adding to the calendar

def http_error(status):
    from googleapiclient.errors import HttpError
    return HttpError(SimpleNamespace(status=status, reason=""), b"")


class FakeCalendar:
    def __init__(self):
        self.added = {}

    def events(self):
        return self

    def get(self, calendarId, eventId):
        def execute():
            if eventId not in self.added:
                raise http_error(404)
            return self.added[eventId]
        return SimpleNamespace(execute=execute)

    def update(self, calendarId, eventId, body):
        def execute():
            self.added[eventId] = body
            return {"htmlLink": "https://calendar/" + eventId}
        return SimpleNamespace(execute=execute)

    def insert(self, calendarId, body):
        def execute():
            if body["id"] in self.added:
                raise http_error(409)
            self.added[body["id"]] = body
            return {"htmlLink": "https://calendar/" + body["id"]}
        return SimpleNamespace(execute=execute)


class FakeCatalog:
    def __init__(self, rows=()):
        from test_catalog import MemoryTable
        from intake import catalog
        self.artists = MemoryTable(catalog.ARTISTS, "Artist", ("Tags",), rows=rows)
        self.events = MemoryTable(catalog.EVENTS, "Event id", ("Tags",))


TODAY = datetime.date(2026, 11, 13)


def test_handle_adds_upcoming_events_once_and_skips_past_ones():
    cal = FakeCalendar()
    target = events.Target(cal, "cal")
    found = [event(), event(date="2026-11-22"), event(title="Old show", date="2026-11-01")]
    assert events.handle(POST, found, target, TODAY, dry_run=False) == 2
    assert all("attachments" not in b for b in cal.added.values())
    assert events.handle(POST, found, target, TODAY, dry_run=False) == 0  # already there


def test_existing_event_is_left_alone_unless_the_post_is_named():
    cal = FakeCalendar()
    target = events.Target(cal, "cal")
    events.handle(POST, [event()], target, TODAY, dry_run=False)
    (eid, body), = cal.added.items()
    cal.added[eid] = dict(body, summary="edited by hand", status="cancelled")
    assert events.handle(POST, [event()], target, TODAY, dry_run=False) == 0
    assert cal.added[eid]["summary"] == "edited by hand"
    assert events.handle(POST, [event()], target, TODAY, dry_run=False, redo=True) == 1
    assert cal.added[eid]["summary"] == "Fellatio" and cal.added[eid]["status"] == "confirmed"


def test_two_events_on_one_date_in_a_post_both_get_added():
    cal = FakeCalendar()
    assert events.handle(POST, [event(), event(title="Afterparty")], events.Target(cal, "cal"), TODAY, dry_run=False) == 2


def test_only_shows_in_the_netherlands_or_belgium_are_added():
    cal = FakeCalendar()
    found = [event(), event(date="2026-11-22", city="Ghent", country="België"),
             event(date="2026-11-23", city="Berlin", country="Germany"),
             event(date="2026-11-24", city=None, country=None)]
    assert events.handle(POST, found, events.Target(cal, "cal"), TODAY, dry_run=False) == 3
    assert sorted(b["start"]["dateTime"][:10] for b in cal.added.values()) == ["2026-11-21", "2026-11-22", "2026-11-24"]


def test_each_added_event_gets_a_row_on_the_events_tab():
    cal, cat = FakeCalendar(), FakeCatalog([{"Artist": "Fellatio", "Tags": "punk"}])
    post = instagram.Post("DAbc123", POST.url, caption="x", location="WORM Rotterdam")
    ev = event(link="https://worm.org/x", tags=["Noise"])
    events.handle(post, [ev], events.Target(cal, "cal", cat), TODAY, dry_run=False)
    (row,) = cat.events.rows
    assert row["Date"] == "2026-11-21" and row["Start"] == "20:00" and row["End"] == "23:00"
    assert (row["Title"], row["Venue"], row["City"], row["Country"]) == ("Fellatio", "The Venue", "Hague", "Netherlands")
    assert row["Acts"] == "Fellatio, Daufødt" and row["Tags"] == "noise, punk"
    assert row["Link"] == "https://worm.org/x" and row["Post"] == POST.url
    assert row["Location tag"] == "WORM Rotterdam" and row["Event id"] == show_calendar.event_id("DAbc123", ev)
    assert row["Added"] == "2026-11-13"
    events.handle(post, [ev], events.Target(cal, "cal", cat), TODAY, dry_run=False)
    assert len(cat.events.rows) == 1  # no second row on a rerun


def test_row_for_an_older_event_without_kept_details():
    old = {"id": "mfabc", "summary": "Calls From The Hull IV", "location": "V11, Rotterdam",
           "start": {"date": "2026-11-28"}, "end": {"date": "2026-11-29"},
           "description": 'kraut<br><br>caption<br><br><a href="https://www.instagram.com/p/DfhmQJuAaLV/">Save &amp; Share</a>',
           "source": {"url": "https://www.instagram.com/p/DfhmQJuAaLV/"}}
    row = show_calendar.row(old, "2026-11-13")
    assert (row["Date"], row["Start"], row["Title"]) == ("2026-11-28", "", "Calls From The Hull IV")
    assert (row["Venue"], row["City"]) == ("V11", "Rotterdam")
    assert row["Post"] == "https://www.instagram.com/p/DfhmQJuAaLV/" and row["Link"] == ""


def test_fill_sheet_gives_every_calendar_event_a_row():
    cal, cat = FakeCalendar(), FakeCatalog()
    events.handle(POST, [event(), event(date="2026-11-22")], events.Target(cal, "cal"), TODAY, dry_run=False)
    cal.list = lambda calendarId, pageToken, showDeleted, singleEvents, maxResults: SimpleNamespace(
        execute=lambda: {"items": list(cal.added.values())})
    events.fill_sheet(events.Target(cal, "cal", cat), TODAY)
    assert sorted(r["Date"] for r in cat.events.rows) == ["2026-11-21", "2026-11-22"]


def test_dry_run_adds_nothing():
    assert events.handle(POST, [event()], events.Target(), TODAY, dry_run=True) == 0


def test_tags_combine_the_post_and_the_artists_sheet_without_places():
    cat = FakeCatalog([{"Artist": "Fellatio", "Tags": "punk, Noise, rotterdam", "Location": "Rotterdam, Netherlands"}])
    assert events.event_tags(event(tags=["Hardcore", "punk"]), cat) == ["hardcore", "noise", "punk"]
    assert events.event_tags(event(tags=["punk"]), None) == ["punk"]


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


def test_refreshing_for_acquire_keeps_the_calendar_permission(tmp_path, monkeypatch):
    token = tmp_path / "token.json"
    token.write_text(json.dumps({"scopes": google_auth.SCOPES, "token": "old", "refresh_token": "r",
                                 "client_id": "c", "client_secret": "s", "expiry": "2000-01-01T00:00:00Z"}))
    monkeypatch.setattr(google_auth.config, "TOKEN_FILE", token)

    def refresh(self, request):
        self.token, self.expiry = "new", datetime.datetime(2999, 1, 1)
    monkeypatch.setattr(google_auth.Credentials, "refresh", refresh)

    google_auth.credentials()  # Acquire: gmail and drive only
    saved = json.loads(token.read_text())
    assert saved["token"] == "new" and set(saved["scopes"]) == set(google_auth.SCOPES)
    google_auth.credentials(google_auth.SCOPES)  # the show calendar still works


def test_setup_only_keeps_a_sign_in_for_mfyn(tmp_path, monkeypatch):
    client = tmp_path / "client.json"
    client.write_text("{}")
    monkeypatch.setattr(google_auth.config, "APP_DIR", tmp_path)
    monkeypatch.setattr(google_auth.config, "CLIENT_FILE", client)
    monkeypatch.setattr(google_auth.config, "TOKEN_FILE", tmp_path / "token.json")
    creds = SimpleNamespace(to_json=lambda: "{}")
    flow = SimpleNamespace(run_local_server=lambda **kw: creds)
    monkeypatch.setattr(google_auth.InstalledAppFlow, "from_client_secrets_file", lambda *a: flow)

    monkeypatch.setattr(google_auth, "signed_in_as", lambda c: "admin@nothingflatdigital.com")
    with pytest.raises(SystemExit, match="admin@"):
        google_auth.setup(client)
    assert not (tmp_path / "token.json").exists()

    monkeypatch.setattr(google_auth, "signed_in_as", lambda c: "MFYN@nothingflatdigital.com")
    assert google_auth.setup(client) == "MFYN@nothingflatdigital.com"
    assert (tmp_path / "token.json").exists()


# "Your artist is playing"

def test_names_match_without_case_accents_punctuation_or_the():
    assert alerts.key("Daufødt") == alerts.key("DAUFODT") == alerts.key("daufødt.")
    assert alerts.key("The Ex") == alerts.key("Ex")
    assert alerts.key("Fellatio") != alerts.key("Fellatio Live Band")


def test_library_artists_are_found_among_the_acts_as_the_sheet_spells_them():
    cat = FakeCatalog([{"Artist": "Daufødt"}, {"Artist": "applied communications"}])
    assert alerts.library_artists(cat, ["FELLATIO", "DAUFODT", "Applied Communications"]) == [
        "Daufødt", "applied communications"]
    assert alerts.library_artists(None, ["x"]) == []


def test_a_new_show_with_a_library_artist_is_coloured_and_queued_for_the_email():
    cal, cat = FakeCalendar(), FakeCatalog([{"Artist": "Daufødt"}])
    target = events.Target(cal, "cal", cat)
    events.handle(POST, [event(), event(date="2026-11-22", acts=["Someone Else"])], target, TODAY, dry_run=False)
    colours = {b["start"]["dateTime"][:10]: b.get("colorId") for b in cal.added.values()}
    assert colours == {"2026-11-21": events.config.ALERT_COLOR, "2026-11-22": None}
    (match,) = target.alerts
    assert match.artists == ["Daufødt"] and match.date == "2026-11-21" and match.post == POST.url
    events.handle(POST, [event()], target, TODAY, dry_run=False)
    assert len(target.alerts) == 1  # already on the calendar: no second alert
    events.handle(POST, [event()], target, TODAY, dry_run=False, redo=True)
    assert len(target.alerts) == 2  # --post: alerts again, so it can be tried


def test_alert_email_lists_each_show():
    m = alerts.Match(["Daufødt"], "Fellatio", "2026-11-21", "20:00", "WORM, Rotterdam", POST.url, "https://cal/e")
    subject, text = alerts.email([m])
    assert subject == "MFYN: Daufødt is playing"
    assert "Daufødt: Fellatio\nSat 21 Nov 2026, 20:00, WORM, Rotterdam\nPost: " + POST.url in text
    own = alerts.Match(["Allarme"], "ALLARME", "2026-12-04", "", "", "u", "")
    assert alerts.email([own])[1].splitlines()[2] == "Allarme"  # not "Allarme: ALLARME"
    two = alerts.Match(["Fellatio"], "X", "2026-11-20", "", "", "u", "")
    assert alerts.email([m, two])[0] == "MFYN: 2 library artists are playing"


def test_alert_is_sent_as_one_gmail_message():
    sent = []
    gmail = SimpleNamespace(users=lambda: SimpleNamespace(messages=lambda: SimpleNamespace(
        send=lambda userId, body: SimpleNamespace(execute=lambda: sent.append(body)))))
    alerts.send(gmail, "mfyn@nothingflatdigital.com", "MFYN: test", "hello")
    import base64, email
    msg = email.message_from_bytes(base64.urlsafe_b64decode(sent[0]["raw"]))
    assert msg["To"] == "mfyn@nothingflatdigital.com" and msg["Subject"] == "MFYN: test"
