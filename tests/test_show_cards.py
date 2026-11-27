import datetime
import json
import types

from intake import show_cards
from intake.build_show import PlaylistTrack

TODAY = datetime.date(2026, 11, 27)
EVENTS = [
    {"Date": "2026-12-05", "Start": "20:30", "Title": "Hidden Behind x WORM: Sick Pack, Mitraille & Paracetamøl",
     "Venue": "WORM", "City": "Rotterdam", "Acts": "Sick Pack, Mitraille, Paracetamøl"},
    {"Date": "2026-12-03", "Title": "Coffin", "Venue": "Rotown", "City": "Rotterdam"},
    {"Date": "2026-11-20", "Title": "Old show"},
    {"Date": "2027-10-08", "Title": "Wolf Eyes"},
    {"Date": "", "Title": "No date"},
]


def test_upcoming_keeps_six_weeks_in_order():
    found = show_cards.upcoming(EVENTS, TODAY)
    assert [e["title"] for e in found] == ["Coffin", "Hidden Behind x WORM: Sick Pack, Mitraille & Paracetamøl"]
    assert found[0]["weekday"] == "Thursday"


def test_artist_events_match_acts_and_titles():
    found = show_cards.upcoming(EVENTS, TODAY)
    assert [e["title"] for e in show_cards.artist_events("PARACETAMOL", found)] == [found[1]["title"]]
    assert [e["title"] for e in show_cards.artist_events("Coffin", found)] == ["Coffin"]
    assert show_cards.artist_events("Sick", found) == []     # too short to match inside a title


def test_facts_group_tracks_by_artist():
    wanted = [PlaylistTrack(1, "A", "One", "LP", "https://a/track/1", "https://a/album/lp"),
              PlaylistTrack(2, "B", "Two", "", "https://b/track/2", ""),
              PlaylistTrack(3, "a", "Three", "LP", "https://a/track/3", "https://a/album/lp")]
    pages = {"https://a/album/lp": {"label": "Knife Hits"}, "https://b/track/2": {"released": "2025-12-16"}}
    artists = [{"Artist": "A", "Location": "Ghent, Belgium", "Bio": "noisy", "Tags": ""}]
    data = show_cards.facts("MFYN - December 2026", wanted, pages, artists, [])
    assert [a["artist"] for a in data["artists"]] == ["A", "B"]
    a = data["artists"][0]
    assert a["location"] == "Ghent, Belgium" and "tags" not in a
    assert [t["play"] for t in a["tracks"]] == [1, 3]
    assert a["tracks"][0]["label"] == "Knife Hits" and a["tracks"][0]["link"] == "https://a/album/lp"
    assert data["artists"][1]["tracks"][0]["released"] == "2025-12-16"
    assert json.dumps(data)          # all of it goes into the prompt


def test_write_cards_reads_claudes_reply():
    calls = []

    def run(cmd, **kw):
        calls.append((cmd, kw["input"]))
        return types.SimpleNamespace(stdout=json.dumps({"result": "# Show cards: X\n\n## 1. A\n", "is_error": False}),
                                     stderr="", returncode=0)
    text = show_cards.write_cards({"playlist": "X", "artists": [], "events": []}, run=run, claude="claude")
    assert text.startswith("# Show cards: X")
    assert calls[0][0][:2] == ["claude", "-p"] and "--tools" in calls[0][0]
    assert "spoken intro" in calls[0][1] and '"playlist": "X"' in calls[0][1]


def test_make_writes_the_file(tmp_path):
    catalog = types.SimpleNamespace(artists=types.SimpleNamespace(rows=[]), events=types.SimpleNamespace(rows=EVENTS))
    seen = {}

    def writer(data, model=None):
        seen.update(data)
        return "# Show cards\n"
    wanted = [PlaylistTrack(1, "Coffin", "Song", "", "https://c/track/1", "")]
    path = show_cards.make(tmp_path, "MFYN - December 2026", wanted, today=TODAY,
                           read_pages=lambda w: {}, catalog=catalog, writer=writer)
    assert path.read_text(encoding="utf-8") == "# Show cards\n"
    assert seen["artists"][0]["upcoming_events"][0]["venue"] == "Rotown"
