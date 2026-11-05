import json
import stat
import sys

from intake import config, stories
from test_reels import flac

FAKE_PROCESSING = '''#!{python}
import sys
from pathlib import Path
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a and not a.startswith("--"))
assert "--run" in sys.argv and any(a.startswith("--sketch=") and "MFYN_Album" in a for a in sys.argv)
assert args["seconds"] == "30"
for album in Path(args["input"]).iterdir():
    featured = (album / "featured.txt").read_text()
    (Path(args["output"]) / (album.name + "_story.mp4")).write_text("mp4 featuring " + featured)
    (Path(args["output"]) / (album.name + "_story.png")).write_bytes(b"png")
'''


def library_with_album(tmp_path):
    lib = tmp_path / "library"
    album = lib / "CADY - Limitations of the Human Form"
    album.mkdir(parents=True)
    for n, title in [(1, "An Audience of Loved Ones"), (2, "Umbrella"), (10, "Constellation Indifference")]:
        path = flac(album / f"CADY - Limitations of the Human Form - {n:02} {title}.flac", "CADY", title,
                    "Limitations of the Human Form")
        from mutagen.flac import FLAC
        tags = FLAC(path); tags["tracknumber"] = str(n); tags.save()
    (album / "cover.jpg").write_bytes(b"jpg")
    (lib / "Other Band - Other Album").mkdir()
    flac(lib / "Other Band - Other Album" / "01.flac", "Other Band", "Song", "Other Album")
    (lib / ".partial - Half Done").mkdir()
    flac(lib / ".partial - Half Done" / "01.flac", "X", "Y")
    (lib / "Empty").mkdir()
    return lib, album


def test_albums_and_matching(tmp_path):
    lib, album = library_with_album(tmp_path)
    found = stories.albums(lib)
    assert [f.name for f in found] == ["CADY - Limitations of the Human Form", "Other Band - Other Album"]
    assert stories.matching(found, "cady") == [album]
    assert stories.matching(found, "  ") == []


def test_tracks_are_in_sketch_order_and_featured_txt(tmp_path):
    _, album = library_with_album(tmp_path)
    tracks = stories.album_tracks(album)
    assert [t.title for t in tracks] == ["An Audience of Loved Ones", "Umbrella", "Constellation Indifference"]
    assert stories.featured_txt(tracks, 2) == "10"
    tracks[0].track_number = tracks[1].track_number = "2"   # duplicate numbers: use the position
    assert stories.featured_txt(tracks, 1) == "2" and stories.featured_txt(tracks, 0) == "1"


def test_make_story_end_to_end(tmp_path, monkeypatch):
    lib, album = library_with_album(tmp_path)
    fake = tmp_path / "processing-java"
    fake.write_text(FAKE_PROCESSING.format(python=sys.executable))
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    out = tmp_path / "stories"
    monkeypatch.setattr(config, "LIBRARY_DIR", lib)
    monkeypatch.setattr(config, "STORIES_DIR", out)
    monkeypatch.setattr(config, "PROCESSING", str(fake))
    monkeypatch.setattr(config, "APP_DIR", tmp_path / "app")
    monkeypatch.setattr(config, "STORIES_LOG_FILE", tmp_path / "app" / "stories.log")
    monkeypatch.setattr(config, "TOKEN_FILE", tmp_path / "app" / "missing-token.json")

    answers = iter(["human", "3"])
    assert stories.main([], ask=lambda p: next(answers), say=lambda *_: None) == 0
    folder = out / "CADY - Limitations of the Human Form"
    name = "CADY - Limitations of the Human Form - Constellation Indifference"
    assert sorted(p.name for p in folder.iterdir()) == [f"{name}.json", f"{name}.mp4", f"{name}.png"]
    assert (folder / f"{name}.mp4").read_text() == "mp4 featuring 10"
    info = json.loads((folder / f"{name}.json").read_text())
    assert info["album"] == "Limitations of the Human Form" and info["artist"] == "CADY"
    assert info["featured_track"]["title"] == "Constellation Indifference"
    assert info["clip_seconds"] == 30

    # Same album and track again: nothing to do.
    assert stories.main(["--album", "cady", "--track", "3"], ask=lambda p: "", say=lambda *_: None) == 0
    assert "already exists" in (tmp_path / "app" / "stories.log").read_text()


def test_pick_album_asks_again_and_chooses_from_several(tmp_path):
    lib, album = library_with_album(tmp_path)
    found = stories.albums(lib)
    answers = iter(["nothing like this", "o", "1"])
    said = []
    assert stories.pick_album(found, None, lambda p: next(answers), said.append) == album
    assert any("No album" in s for s in said)
