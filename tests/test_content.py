import json
import random
import stat
import sys

from intake import config, content, stories
from test_reels import flac

FAKE_PROCESSING = '''#!{python}
import sys
from pathlib import Path
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a and not a.startswith("--"))
sketch = next(a for a in sys.argv if a.startswith("--sketch="))
out = Path(args["output"])
if "MFYN_Archive" in sketch:
    (out / ("MFYN_archive_%02d.png" % int(args["number"]))).write_text(args["date"])
    (out / ("MFYN_tracklist_%02d.png" % int(args["number"]))).write_text("tracklist")
elif "MFYN_VideoPost_OnAir" in sketch:
    for f in Path(args["input"]).iterdir():
        (out / (f.stem + "_post.mp4")).write_bytes(b"mp4")
elif "MFYN_Story_Album" in sketch:
    for album in Path(args["input"]).iterdir():
        (out / (album.name + "_story.mp4")).write_text("featuring " + (album / "featured.txt").read_text())
        (out / (album.name + "_story.png")).write_bytes(b"png")
'''


def album(lib, folder, artist, name, titles):
    path = lib / folder
    path.mkdir(parents=True)
    from mutagen.flac import FLAC
    for n, title in enumerate(titles, 1):
        f = flac(path / f"{n:02} {title}.flac", artist, title, name)
        tags = FLAC(f); tags["tracknumber"] = str(n); tags.save()
    (path / "cover.jpg").write_bytes(b"jpg")
    return path


def setup(tmp_path, monkeypatch):
    lib, archive = tmp_path / "library", tmp_path / "archive"
    album(lib, "CADY - Limitations of the Human Form", "CADY", "Limitations of the Human Form",
          ["An Audience of Loved Ones", "Umbrella", "Constellation Indifference"])
    album(lib, "CADY - Earlier Record", "CADY", "Earlier Record", ["Old One"])
    album(lib, "Other Band - Other Album", "Other Band", "Other Album", ["Song", "Second Song"])
    tracks = archive / "5_11_2026- Official Unofficial" / "Tracks"
    tracks.mkdir(parents=True)
    flac(tracks / "01.flac", "CADY", "Umbrella", "Limitations of the Human Form")
    flac(tracks / "02.flac", "Other Band", "Song", "Other Album")
    flac(tracks / "03.flac", "cady", "Old One", "Earlier Record")      # same artist, another album
    flac(tracks / "04.flac", "Stranger", "Not Bought", "Not In Library")
    fake = tmp_path / "processing-java"
    fake.write_text(FAKE_PROCESSING.format(python=sys.executable))
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    for name, value in [("SHOW_ARCHIVE_DIR", archive), ("LIBRARY_DIR", lib), ("POSTS_DIR", tmp_path / "posts"),
                        ("STORIES_DIR", tmp_path / "stories"), ("PROCESSING", str(fake)),
                        ("APP_DIR", tmp_path / "app"), ("CONTENT_LOG_FILE", tmp_path / "app" / "content.log"),
                        ("TOKEN_FILE", tmp_path / "app" / "missing-token.json")]:
        monkeypatch.setattr(config, name, value)
    # The YouTube playlist needs Google and YouTube; it has its own tests (test_playlist.py).
    from intake import playlist
    monkeypatch.setattr(playlist, "for_episode", lambda ep, ask=input: (True, "playlist stub"))
    return archive / "5_11_2026- Official Unofficial"


def test_one_run_makes_cover_posts_captions_and_a_story_per_artist(tmp_path, monkeypatch):
    ep = setup(tmp_path, monkeypatch)
    # Stranger's album isn't in the library: they get no Story, and the run carries on.
    assert content.main([], ask=lambda p: "y", say=lambda *_: None, rng=random.Random(1)) == 0

    assert (ep / "MFYN_archive_03.png").exists() and (ep / "MFYN_tracklist_03.png").exists()
    posts = sorted(p.name for p in (tmp_path / "posts" / ep.name).iterdir())
    assert len([p for p in posts if p.endswith(".mp4")]) == 4
    assert len([p for p in posts if p.endswith(".txt")]) == 4

    story_dir = tmp_path / "stories" / ep.name
    infos = [json.loads(p.read_text()) for p in sorted(story_dir.glob("*.json"))]
    assert sorted(i["episode_artist"].casefold() for i in infos) == ["cady", "other band"]   # one per artist
    for info in infos:
        assert (story_dir / f"{info['artist']} - {info['featured_track']['title']}.mp4").exists()
        assert (story_dir / f"{info['artist']} - {info['featured_track']['title']}.png").exists()
    log = (tmp_path / "app" / "content.log").read_text()
    assert "Stranger: no album of theirs" in log

    # A second run has nothing left to make.
    before = sorted(p.name for p in story_dir.iterdir())
    assert content.main([], ask=lambda p: "y", say=lambda *_: None, rng=random.Random(2)) == 0
    assert sorted(p.name for p in story_dir.iterdir()) == before
    assert "CADY already has an Album Story" in (tmp_path / "app" / "content.log").read_text()


def test_for_episode_features_a_random_track_of_the_played_album(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    from intake import reels
    ep_tracks = [reels.read_track(p) for p in sorted((tmp_path / "archive").rglob("*.flac"))]
    folders = stories.albums(config.LIBRARY_DIR)
    featured = set()
    for seed in range(30):
        picks = stories.pick_per_artist(ep_tracks, folders, random.Random(seed))
        assert [artist.casefold() for *_, artist in picks] == ["cady", "other band"]
        folder, tracks, index, _ = next(p for p in picks if p[0].name.startswith("Other Band"))
        featured.add(tracks[index].title)
    assert featured == {"Song", "Second Song"}       # not only the track that was played
    picks = stories.pick_per_artist(ep_tracks, folders, random.Random(0), done={"cady"})
    assert [artist for *_, artist in picks] == ["Other Band"]


def test_in_library_matches_album_and_title(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    from intake import reels
    folders = stories.albums(config.LIBRARY_DIR)
    umbrella = reels.Track(tmp_path / "x.flac", "CADY", "umbrella", "Limitations of the Human Form")
    folder, tracks, index = stories.in_library(umbrella, folders)
    assert folder.name == "CADY - Limitations of the Human Form" and tracks[index].title == "Umbrella"
    assert stories.in_library(reels.Track(tmp_path / "y.flac", "CADY", "Umbrella", ""), folders) is None


def test_only_the_archive_cover_when_you_say_no_to_the_rest(tmp_path, monkeypatch):
    ep = setup(tmp_path, monkeypatch)
    answers = iter(["y", "n", "n", "n", "y"])     # tracks; posts, Stories, playlist; keep the cover
    asked = []
    assert content.main([], ask=lambda p: asked.append(p) or next(answers), say=lambda *_: None) == 0
    assert asked[1:4] == ["Do you want ON AIR posts? [Y/n] ", "Album Story videos? [Y/n] ",
                          "Do you want a YouTube playlist? [Y/n] "]
    assert asked[4].startswith("Keep this cover and tracklist image?")
    assert (ep / "MFYN_archive_03.png").exists() and (ep / "MFYN_tracklist_03.png").exists()
    assert not (tmp_path / "posts").exists() and not (tmp_path / "stories").exists()


def test_stories_without_posts(tmp_path, monkeypatch):
    ep = setup(tmp_path, monkeypatch)
    answers = iter(["", "n", "", "n", ""])   # tracks; no posts, Stories, no playlist; keep the cover
    assert content.main([], ask=lambda p: next(answers), say=lambda *_: None, rng=random.Random(3)) == 0
    assert (ep / "MFYN_tracklist_03.png").exists()
    assert not (tmp_path / "posts").exists()
    assert len(list((tmp_path / "stories" / ep.name).glob("*.mp4"))) == 2


def test_a_new_sub_script_is_one_line_in_steps_and_a_crash_doesnt_stop_the_rest(tmp_path, monkeypatch):
    import types
    ep = setup(tmp_path, monkeypatch)
    calls = []
    playlist = types.ModuleType("intake.playlist")

    def for_episode(ep, ask=input):        # takes only what it needs
        calls.append((ep.folder.name, ask("Create the YouTube playlist from the reviewed list? [y/N] ")))
        return True, "proposal written, waiting for your review"
    playlist.for_episode = for_episode
    broken = types.ModuleType("intake.broken")
    broken.for_episode = lambda ep: 1 / 0
    monkeypatch.setitem(sys.modules, "intake.playlist", playlist)
    monkeypatch.setitem(sys.modules, "intake.broken", broken)
    monkeypatch.setattr(content, "STEPS", content.STEPS[:1] + (("broken", "Broken", "Broken?"),) + content.STEPS[1:])

    asked = []
    answers = iter(["y", "y", "n", "n", "y", "y", "n"])   # tracks; broken, posts, Stories, playlist; cover; playlist's own
    assert content.main([], ask=lambda p: asked.append(p) or next(answers), say=lambda *_: None) == 1
    assert asked[1:5] == ["Broken? [Y/n] ", "Do you want ON AIR posts? [Y/n] ", "Album Story videos? [Y/n] ",
                          "Do you want a YouTube playlist? [Y/n] "]
    assert calls == [(ep.name, "n")]                    # ran after the broken step crashed
    assert (ep / "MFYN_tracklist_03.png").exists()      # the playlist cover was made first
    log = (tmp_path / "app" / "content.log").read_text()
    assert "FAILED Broken: crashed: ZeroDivisionError" in log
    assert "ok     YouTube playlist: proposal written" in log


def test_steps_not_built_yet_are_left_out():
    names = [m.__name__ for m, _, _ in content.available_steps()]
    assert names == ["intake.archive_cover", "intake.reels", "intake.stories", "intake.playlist"]
