import datetime
import json
import shutil
import stat
import sys
from pathlib import Path

from mutagen.flac import FLAC

from intake import catalog, config, episode, handles, reels
from test_catalog import MemoryTable

BLANK = Path(__file__).parent / "blank.flac"


def flac(path, artist, title, album="Album"):
    shutil.copy(BLANK, path)
    tags = FLAC(path)
    tags["artist"], tags["title"], tags["album"], tags["tracknumber"] = artist, title, album, "1"
    tags.save()
    return path


def test_episode_names(tmp_path):
    for name in ("5_11_2026- Official Unofficial", "12_10_2026 - Older One", "28_2_2027", "notes", "31_2_2026- Bad date"):
        (tmp_path / name).mkdir()
    eps = episode.all_in(tmp_path)
    assert [(e.air_date, e.name) for e in eps] == [
        (datetime.date(2026, 10, 12), "Older One"),
        (datetime.date(2026, 11, 5), "Official Unofficial"),
        (datetime.date(2027, 2, 28), ""),
    ]
    assert episode.find(tmp_path).folder.name == "28_2_2027"
    assert episode.find(tmp_path, "official").name == "Official Unofficial"


def test_reel_names_are_clean_and_unique(tmp_path):
    t = [reels.Track(tmp_path / f"{i}.flac", a, b) for i, (a, b) in
         enumerate([("AC/DC", "Live?"), ("A", "Song"), ("A", "Song")])]
    assert reels.reel_names(t) == ["AC_DC - Live_", "A - Song", "A - Song (2)"]


def test_handle_answers():
    assert handles.answer_to_change("", "@x") == {"Status": "Confirmed"}
    assert handles.answer_to_change("", "") is None
    assert handles.answer_to_change("newname", "@x") == {"Instagram": "@newname", "Status": "Confirmed"}
    assert handles.answer_to_change("-", "@x") == {"Instagram": "", "Status": "No Instagram"}
    assert handles.answer_to_change("not a handle!", "@x") is None


def test_confirm_asks_only_unsettled_and_adds_missing():
    table = MemoryTable(catalog.ARTISTS, "Artist", ("Tags",), rows=[
        {"Artist": "Sure", "Instagram": "@sure", "Status": "Confirmed"},
        {"Artist": "Maybe", "Instagram": "@maybe", "Status": "Suggested"},
    ])
    answers = iter(["", "@brandnew"])
    asked = []
    handles.confirm(table, ["Sure", "Maybe", "Newcomer"], "artist",
                    ask=lambda p: asked.append(p) or next(answers), say=lambda *_: None)
    rows = {r["Artist"]: r for r in table.rows}
    assert len(asked) == 2
    assert rows["Maybe"]["Status"] == "Confirmed"
    assert (rows["Newcomer"]["Instagram"], rows["Newcomer"]["Status"]) == ("@brandnew", "Confirmed")


FAKE_PROCESSING = '''#!{python}
import sys
from pathlib import Path
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a and not a.startswith("--"))
assert "--run" in sys.argv and any(a.startswith("--sketch=") for a in sys.argv)
assert args["seconds"] == "30"
for f in Path(args["input"]).iterdir():
    (Path(args["output"]) / (f.stem + "_reel.mp4")).write_bytes(b"mp4")
'''


def test_make_reels_end_to_end(tmp_path, monkeypatch, capsys):
    archive, out = tmp_path / "archive", tmp_path / "reels"
    tracks = archive / "5_11_2026- Official Unofficial" / "Tracks"
    tracks.mkdir(parents=True)
    flac(tracks / "01.flac", "applied communications", "donna deegan", "bites the big one")
    flac(tracks / "02.flac", "Other Artist", "Song/Two")
    (tracks / "notes.txt").write_text("not audio")
    fake = tmp_path / "processing-java"
    fake.write_text(FAKE_PROCESSING.format(python=sys.executable))
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setattr(config, "SHOW_ARCHIVE_DIR", archive)
    monkeypatch.setattr(config, "REELS_DIR", out)
    monkeypatch.setattr(config, "PROCESSING", str(fake))
    monkeypatch.setattr(config, "APP_DIR", tmp_path / "app")
    monkeypatch.setattr(config, "REELS_LOG_FILE", tmp_path / "app" / "reels.log")
    monkeypatch.setattr(config, "TOKEN_FILE", tmp_path / "app" / "missing-token.json")

    assert reels.main([], ask=lambda prompt: "y") == 0
    ep_out = out / "5_11_2026- Official Unofficial"
    assert sorted(p.name for p in ep_out.iterdir()) == [
        "Other Artist - Song_Two.json", "Other Artist - Song_Two.mp4",
        "applied communications - donna deegan.json", "applied communications - donna deegan.mp4",
    ]
    info = json.loads((ep_out / "applied communications - donna deegan.json").read_text())
    assert info["title"] == "donna deegan" and info["album"] == "bites the big one"
    assert info["episode"] == {"name": "Official Unofficial", "air_date": "2026-11-05",
                               "folder": "5_11_2026- Official Unofficial"}
    assert info["clip_seconds"] == 30

    # A second run has nothing left to do.
    assert reels.main([], ask=lambda prompt: "y") == 0
    assert "2 track(s) already have a Reel" in (tmp_path / "app" / "reels.log").read_text()
