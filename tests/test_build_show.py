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
    lib, work = tmp_path / "MFYN_Library", tmp_path / "MFYN_Workspace"
    lib.mkdir()
    work.mkdir()
    monkeypatch.setattr(config, "LIBRARY_DIR", lib)
    monkeypatch.setattr(config, "WORK_DIR", work)
    monkeypatch.setattr(config, "BUILD_TEMPLATE", work / "MFYN_Template.rpp")
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


FOLDER = "2026_December"


def fake_cards(work):
    path = work / f"{work.name}_show_cards.md"
    path.write_text("# Show cards\n", encoding="utf-8")
    return path


def run(argv=("--link", "https://bandcamp.com/x/playlist/y"), get=None):
    return build_show.main(list(argv), ask=lambda q: pytest.fail(f"asked {q}"), say=lambda *a: None,
                           read=lambda url: build_show.parse_playlist(json.dumps(BLOB)),
                           get=get or (lambda: pytest.fail("ran Acquire")),
                           cards=lambda work, title, wanted: fake_cards(work))


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
    folder = work / FOLDER
    assert [p.name for p in sorted((folder / "Tracks").iterdir())] == [
        "01 - Crowd Of Chairs - Amends.flac",
        "02 - My Wife's An Angel - Not Me.flac",
        "03 - Daufødt - Glitter.flac",
        "04 - My Wife's An Angel - Lil' Bug.flac",
        "05 - L.O.T.I.O.N. Multinational Corporation - (It's Our) Last Xmas Feat. Lulu.flac",
    ]
    project = folder / f"{FOLDER}.rpp"
    text = project.read_text(encoding="utf-8")
    names = [line.strip()[5:] for line in text.splitlines() if line.strip().startswith("NAME") and "<" not in line]
    tracks = [n for n in names if not n.strip("\"'`")[:2].isdigit()]
    assert tracks == ['"Voice over"', '"Music bed"', '"Crowd Of Chairs"', '"My Wife\'s An Angel"', '"Daufødt"',
                      '"L.O.T.I.O.N. Multinational Corporation"']
    assert "FILE \"Tracks\\01 - Crowd Of Chairs - Amends.flac\"" in text

    # The project reads back as the playlist's running order (the YouTube playlist uses this).
    ep = episode.Episode(folder, datetime.date(2026, 12, 3), "")
    order = reaper.running_order(ep, project)
    assert [(p.artist, p.title) for p in order] == [
        ("Crowd Of Chairs", "Amends"), ("My Wife's An Angel", "Not Me"), ("DAUFØDT", "Glitter"),
        ("My Wife's An Angel", "Lil' Bug"), ("L.O.T.I.O.N. Multinational Corporation", "(It's Our) Last Xmas feat. Lulu")]


def test_missing_tracks_stop_before_copying(setup):
    lib, work = setup
    add(lib, "Crowd Of Chairs - Breather", "Crowd Of Chairs", "Amends", "Breather")
    acquired = []
    assert run(get=lambda: acquired.append(1)) == 1
    assert acquired == [1]
    assert list(work.iterdir()) == []


def test_acquire_fills_the_gaps(setup):
    lib, work = setup
    add(lib, "Crowd Of Chairs - Breather", "Crowd Of Chairs", "Amends", "Breather")
    assert run(get=lambda: full_library(lib)) == 0
    assert len(list((work / FOLDER / "Tracks").iterdir())) == 5
    # Copied, not moved: the library keeps its files.
    assert (lib / "Crowd Of Chairs - Breather" / "Crowd Of Chairs - Breather - 01 Amends.flac").is_file()


TEMPLATE = """<REAPER_PROJECT 0.1 "7.0/x64" 1700000000
  RIPPLE 0
  <MASTERFXLIST
    <VST "VST: ReaLimit" reaLimit.dll 0 ""
      ZmFrZQ==
    >
  >
  <TRACK {AAA}
    NAME "Voice over"
    <FXCHAIN
      <VST "VST: ReaComp" reacomp.dll 0 ""
        ZmFrZQ==
      >
    >
  >
  <TRACK {BBB}
    NAME "Old artist"
  >
>
"""


def test_starts_from_the_template(setup):
    lib, work = setup
    full_library(lib)
    (work / "MFYN_Template.rpp").write_text(TEMPLATE, encoding="utf-8")
    assert run() == 0
    text = (work / FOLDER / f"{FOLDER}.rpp").read_text(encoding="utf-8")
    assert text.startswith('<REAPER_PROJECT 0.1 "7.0/x64"')
    assert "ReaLimit" in text and "ReaComp" in text and "Old artist" not in text
    assert text.count("<TRACK") == 2 + 4          # Voice over (from the template), Music bed, 4 artists
    assert text.index("Voice over") < text.index("Music bed") < text.index("Crowd Of Chairs")
    assert text.rstrip().endswith(">")
    ep = episode.Episode(work / FOLDER, datetime.date(2026, 12, 3), "")
    assert len(reaper.running_order(ep, work / FOLDER / f"{FOLDER}.rpp")) == 5


def test_leaves_a_used_folder_alone(setup):
    lib, work = setup
    full_library(lib)
    (work / FOLDER).mkdir()
    (work / FOLDER / "old.rpp").write_text("x")
    assert run() == 1
    assert [p.name for p in (work / FOLDER).iterdir()] == ["old.rpp"]


def test_fills_an_empty_folder_and_ignores_renamed_ones(setup):
    lib, work = setup
    full_library(lib)
    (work / FOLDER).mkdir()
    (work / "2026_November_5").mkdir()
    (work / "2026_November_5" / "2026_November.rpp").write_text("done")
    assert run() == 0
    assert (work / FOLDER / f"{FOLDER}.rpp").is_file()


def test_folder_from_the_command_line(setup):
    lib, work = setup
    full_library(lib)
    assert run(("--link", "https://bandcamp.com/x/playlist/y", "--folder", "2027_January")) == 0
    assert (work / "2027_January" / "2027_January.rpp").is_file()


def test_asks_for_the_link_and_a_folder_when_the_title_has_no_month(setup):
    lib, work = setup
    full_library(lib)
    blob = json.loads(json.dumps(BLOB))
    blob["appData"]["title"] = "Fav purchases"
    answers = iter(["not a link", "https://bandcamp.com/x/playlist/y", "soon", "december 2026"])
    code = build_show.main(["--no-cards"], ask=lambda q: next(answers), say=lambda *a: None,
                           read=lambda url: build_show.parse_playlist(blob))
    assert code == 0
    assert (work / FOLDER / f"{FOLDER}.rpp").is_file()


def test_month_folder():
    assert build_show.month_folder("MFYN - December 2026") == "2026_December"
    assert build_show.month_folder("mfyn january, 2027") == "2027_January"
    assert build_show.month_folder("Fav purchases") is None


def test_writes_the_cards_and_survives_their_failure(setup):
    lib, work = setup
    full_library(lib)
    assert run() == 0
    assert (work / FOLDER / f"{FOLDER}_show_cards.md").is_file()

    def broken(work, title, wanted):
        raise RuntimeError("no Claude")
    (work / FOLDER).rename(work / "old")
    code = build_show.main(["--link", "https://bandcamp.com/x/playlist/y"], ask=lambda q: "", say=lambda *a: None,
                           read=lambda url: build_show.parse_playlist(BLOB), cards=broken)
    assert code == 0
    assert (work / FOLDER / f"{FOLDER}.rpp").is_file()
