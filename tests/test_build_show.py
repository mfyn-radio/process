import datetime
import json

import pytest

from intake import build_show, config, episode, reaper, runlog
from test_catalog import MemoryTable
from test_reels import flac

BLOB = {"appData": {"title": "MFYN - December 2026", "tracklist": {"tracks": [
    {"title": "Amends", "artistName": "Crowd Of Chairs", "album": {"title": "Breather"}, "url": "https://a/track/1"},
    {"title": "Not Me", "artistName": "My Wife's An Angel", "album": {"title": "Yeah, I Bet"}},
    {"title": "Glitter", "artistName": "Daufødt", "album": {"title": "Glitter"}},
    {"title": "Lil' Bug", "artistName": "My Wife's An Angel", "album": {"title": "Keep Honking"}},
    {"title": "(It's Our) Last Xmas Feat. Lulu", "artistName": "L.O.T.I.O.N. Multinational Corporation", "album": None},
]}}}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    lib, work = tmp_path / "MFYN_Library", tmp_path / "Desktop"
    lib.mkdir()
    work.mkdir()
    monkeypatch.setattr(config, "LIBRARY_DIR", lib)
    monkeypatch.setattr(config, "WORK_DIR", work)
    monkeypatch.setattr(config, "APP_DIR", tmp_path / "app")
    monkeypatch.setattr(config, "BUILD_SHOW_LOG_FILE", tmp_path / "app" / "build_show.log")
    runs, last = MemoryTable(runlog.RUNS, ("Time", "Automation", "About")), MemoryTable(runlog.LAST_RUN, "Automation")
    monkeypatch.setattr(runlog.RunLog, "open", classmethod(lambda cls, name: cls(name, runs, last)))
    return lib, work


def add(lib, folder, artist, title, album):
    (lib / folder).mkdir(exist_ok=True)
    return flac(lib / folder / f"{artist} - {album} - 01 {title}.flac", artist, title, album)


def full_library(lib):
    add(lib, "Crowd Of Chairs - Breather", "Crowd Of Chairs", "Amends", "Breather")
    add(lib, "Crowd Of Chairs - Breather", "Crowd Of Chairs", "Other Song", "Breather")
    add(lib, "My Wife's An Angel - Yeah, I Bet", "My Wife's An Angel", "Not Me", "Yeah, I Bet")
    add(lib, "My Wife's An Angel - Keep Honking", "My Wife's An Angel", "Lil' Bug", "Keep Honking")
    add(lib, "Daufodt - Glitter", "DAUFØDT", "Glitter", "Glitter")
    add(lib, "LOTION - Xmas", "L.O.T.I.O.N. Multinational Corporation", "(It's Our) Last Xmas feat. Lulu", "Xmas")


def run(argv=("--link", "https://bandcamp.com/x/playlist/y", "--date", "3_12_2026", "--name", "Fav Purchased 2026")):
    return build_show.main(list(argv), ask=lambda q: pytest.fail(f"asked {q}"), say=lambda *a: None,
                           read=lambda url: build_show.parse_playlist(json.dumps(BLOB)))


def test_parse_playlist():
    title, tracks = build_show.parse_playlist(json.dumps(BLOB))
    assert title == "MFYN - December 2026"
    assert [(t.number, t.artist, t.title, t.album) for t in tracks][:2] == [
        (1, "Crowd Of Chairs", "Amends", "Breather"), (2, "My Wife's An Angel", "Not Me", "Yeah, I Bet")]
    assert tracks[4].album == ""


def test_match_ignores_case_accents_and_punctuation(setup):
    lib, _ = setup
    full_library(lib)
    _, wanted = build_show.parse_playlist(BLOB)
    found, missing = build_show.match(wanted, build_show.library_tracks(lib))
    assert missing == []
    assert [m.path.parent.name for m in found] == [
        "Crowd Of Chairs - Breather", "My Wife's An Angel - Yeah, I Bet", "Daufodt - Glitter",
        "My Wife's An Angel - Keep Honking", "LOTION - Xmas"]


def test_album_breaks_a_tie(setup):
    lib, _ = setup
    add(lib, "A - Demo", "A", "Song", "Demo")
    add(lib, "A - LP", "A", "Song", "LP")
    found, _ = build_show.match([build_show.PlaylistTrack(1, "A", "Song", "LP")], build_show.library_tracks(lib))
    assert found[0].path.parent.name == "A - LP"


def test_partial_downloads_are_not_used(setup):
    lib, _ = setup
    add(lib, ".partial - A - LP", "A", "Song", "LP")
    _, missing = build_show.match([build_show.PlaylistTrack(1, "A", "Song", "LP")], build_show.library_tracks(lib))
    assert len(missing) == 1


def test_builds_the_working_folder_and_project(setup):
    lib, work = setup
    full_library(lib)
    assert run() == 0
    folder = work / "3_12_2026- Fav Purchased 2026"
    assert [p.name for p in sorted((folder / "Tracks").iterdir())] == [
        "01 - Crowd Of Chairs - Amends.flac",
        "02 - My Wife's An Angel - Not Me.flac",
        "03 - Daufødt - Glitter.flac",
        "04 - My Wife's An Angel - Lil' Bug.flac",
        "05 - L.O.T.I.O.N. Multinational Corporation - (It's Our) Last Xmas Feat. Lulu.flac",
    ]
    project = folder / "20261203_Fav Purchased 2026.rpp"
    text = project.read_text(encoding="utf-8")
    names = [line.strip()[5:] for line in text.splitlines() if line.strip().startswith("NAME") and "<" not in line]
    tracks = [n for n in names if not n.strip("\"'`")[:2].isdigit()]
    assert tracks == ['"Voice over"', '"Music bed"', '"Crowd Of Chairs"', '"My Wife\'s An Angel"', '"Daufødt"',
                      '"L.O.T.I.O.N. Multinational Corporation"']
    assert "FILE \"Tracks\\01 - Crowd Of Chairs - Amends.flac\"" in text

    # The project reads back as the playlist's running order (the YouTube playlist uses this).
    ep = episode.parse(folder)
    order = reaper.running_order(ep, project)
    assert [(p.artist, p.title) for p in order] == [
        ("Crowd Of Chairs", "Amends"), ("My Wife's An Angel", "Not Me"), ("DAUFØDT", "Glitter"),
        ("My Wife's An Angel", "Lil' Bug"), ("L.O.T.I.O.N. Multinational Corporation", "(It's Our) Last Xmas feat. Lulu")]


def test_missing_tracks_stop_before_copying(setup):
    lib, work = setup
    add(lib, "Crowd Of Chairs - Breather", "Crowd Of Chairs", "Amends", "Breather")
    assert run() == 1
    assert list(work.iterdir()) == []


def test_never_overwrites_a_working_folder(setup):
    lib, work = setup
    full_library(lib)
    (work / "3_12_2026- Fav Purchased 2026").mkdir()
    assert run() == 1
    assert list((work / "3_12_2026- Fav Purchased 2026").iterdir()) == []


def test_asks_for_what_is_missing(setup):
    lib, work = setup
    full_library(lib)
    answers = iter(["not a link", "https://bandcamp.com/x/playlist/y", "3 dec", "3-12-2026", "Fav"])
    code = build_show.main([], ask=lambda q: next(answers), say=lambda *a: None,
                           read=lambda url: build_show.parse_playlist(BLOB))
    assert code == 0
    assert (work / "3_12_2026- Fav" / "20261203_Fav.rpp").is_file()


def test_parse_date():
    assert build_show.parse_date("3_12_2026") == datetime.date(2026, 12, 3)
    assert build_show.parse_date("03/12/2026") == datetime.date(2026, 12, 3)
    assert build_show.parse_date("31_2_2026") is None
