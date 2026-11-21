import datetime
import json
import types

from intake import catalog, config, episode, playlist, reaper
from test_catalog import MemoryTable
from test_reels import flac

RPP = '''<REAPER_PROJECT 0.1 "7.0"
  <TRACK {A}
    NAME voice
    MUTESOLO 0 0 0
    <ITEM
      POSITION 105.9
      NAME 01-voice.wav
      <SOURCE WAVE
        FILE "Media\\01-voice.wav"
      >
    >
  >
  <TRACK {B}
    NAME "skimp - hey alright - 05 Birdwatching"
    MUTESOLO 0 0 0
    <ITEM
      POSITION 358
      MUTE 0 0
      NAME "skimp - hey alright - 01 Hey Alright.flac"
      <SOURCE FLAC
        FILE "H:\\My Drive\\MFYN_Show_Archive\\5_11_2026- Old Name\\Tracks\\skimp - hey alright - 01 Hey Alright.flac"
      >
    >
    <ITEM
      POSITION 110
      MUTE 0 0
      NAME "skimp - hey alright - 05 Birdwatching.mp3"
      <SOURCE MP3
        FILE "H:\\My Drive\\MFYN_Show_Archive\\5_11_2026- Old Name\\Tracks\\skimp - hey alright - 05 Birdwatchi.mp3" 1
      >
    >
    <ITEM
      POSITION 500
      MUTE 1 0
      NAME "skimp - hey alright - 09 Cut.flac"
      <SOURCE FLAC
        FILE "x.flac"
      >
    >
  >
  <TRACK {C}
    NAME "Julia Set - volume one - 01 one"
    <ITEM
      POSITION 2283
      NAME "Julia Set - volume one - 01 one.flac"
      <SOURCE FLAC
        FILE "H:\\My Drive\\MFYN_Library\\Julia Set - volume one\\Julia Set - volume one - 01 one.flac"
      >
    >
    <ITEM
      POSITION 2286
      NAME "Julia Set - volume one - 01 one.flac"
      <SOURCE FLAC
        FILE "H:\\My Drive\\MFYN_Library\\Julia Set - volume one\\Julia Set - volume one - 01 one.flac"
      >
    >
  >
  <TRACK {D}
    NAME "ALIEN DINER"
    <ITEM
      POSITION 0
      NAME "ALIEN DINER - SONIC SODA - 01 snake obamna.flac"
      <SOURCE FLAC
        FILE "H:\\My Drive\\MFYN_Library\\Gone\\ALIEN DINER - SONIC SODA - 01 snake obamna.flac"
      >
    >
  >
>
'''


def make_episode(tmp_path, monkeypatch):
    archive, lib = tmp_path / "archive", tmp_path / "library"
    folder = archive / "5_11_2026-Normal Show-Skramish"
    (folder / "Tracks").mkdir(parents=True)
    flac(folder / "Tracks" / "skimp - hey alright - 01 Hey Alright.flac", "skimp", "Hey Alright", "hey alright")
    flac(folder / "Tracks" / "skimp - hey alright - 05 Birdwatching.flac", "skimp", "Birdwatching", "hey alright")
    (lib / "Julia Set - volume one").mkdir(parents=True)
    flac(lib / "Julia Set - volume one" / "Julia Set - volume one - 01 one.flac", "Julia Set", "one", "volume one")
    (folder / "20261105_Music_For_Your_Neighbors-Skramz-ish.rpp").write_text(RPP, encoding="utf-8")
    (folder / "no.rpp").write_text("<REAPER_PROJECT\n>\n")
    monkeypatch.setattr(config, "SHOW_ARCHIVE_DIR", archive)
    monkeypatch.setattr(config, "LIBRARY_DIR", lib)
    return episode.parse(folder)


def test_running_order_from_the_reaper_project(tmp_path, monkeypatch):
    ep = make_episode(tmp_path, monkeypatch)
    assert reaper.project_for(ep).name.startswith("20261105_")
    plays = reaper.running_order(ep)
    assert [(p.artist, p.title, p.album) for p in plays] == [
        ("ALIEN DINER", "snake obamna", "SONIC SODA"),          # not on disk: from the item name
        ("skimp", "Birdwatching", "hey alright"),               # .mp3 in the project, a shorter name: found anyway
        ("skimp", "Hey Alright", "hey alright"),
        ("Julia Set", "one", "volume one"),                     # from the library, split item counted once
    ]


def test_names_and_values():
    assert reaper.value('"a b" 1') == "a b"
    assert reaper.value("`say \"hi\"`") == 'say "hi"'
    assert reaper.value("voice") == "voice"
    assert reaper.from_name("A - Album - With - Dash - 03 Song.flac") == ("A", "Album - With - Dash", "Song")
    assert playlist.video_id("https://music.youtube.com/watch?v=yJF7Tk7u3eI") == "yJF7Tk7u3eI"
    assert playlist.video_id("https://youtu.be/-H_nnPnQNhI?t=3") == "-H_nnPnQNhI"
    assert playlist.link("bkqSBJ4ISyM", 1, "14:05") == "https://www.youtube.com/watch?v=bkqSBJ4ISyM&t=845s"


class Call:
    def __init__(self, result, log=None, entry=None):
        self.result, self.log, self.entry = result, log, entry

    def execute(self):
        if self.log is not None:
            self.log.append(self.entry)
        return self.result() if callable(self.result) else self.result


class FakeYouTube:
    def __init__(self, library):
        self.library, self.searches, self.calls, self.items = library, [], [], []
        self.fail_after = None

    def search(self):
        def list_(part, q, type, maxResults):
            self.searches.append(q)
            hits = [v for v, info in self.library.items() if info["artist"].casefold() in q.casefold()]
            return Call({"items": [{"id": {"videoId": v}} for v in hits]})
        return types.SimpleNamespace(list=list_)

    def videos(self):
        def list_(part, id):
            return Call({"items": [{"id": v, "snippet": {"title": self.library[v]["title"],
                                                        "channelTitle": self.library[v]["channel"],
                                                        "description": "", "publishedAt": "2025-01-01T00:00:00Z"},
                                    "contentDetails": {"duration": "PT3M"}} for v in id.split(",")]})
        return types.SimpleNamespace(list=list_)

    def playlists(self):
        return types.SimpleNamespace(insert=lambda part, body: Call({"id": "PL123"}, self.calls, ("playlist", body)))

    def playlistItems(self):
        def insert(part, body):
            vid = body["snippet"]["resourceId"]["videoId"]
            if self.fail_after is not None and len(self.items) >= self.fail_after:
                def boom():
                    raise RuntimeError("quotaExceeded")
                return Call(boom)
            return Call(lambda: self.items.append(vid) or {}, self.calls, ("item", vid))

        def list_(part, playlistId, maxResults, pageToken):
            return Call({"items": [{"contentDetails": {"videoId": v}} for v in self.items]})
        return types.SimpleNamespace(insert=insert, list=list_)

    def playlistImages(self):
        return types.SimpleNamespace(insert=lambda part, body, media_body: Call({}, self.calls, ("image", body)))


LIBRARY = {
    "liveskimp01": {"artist": "skimp", "title": "skimp - Birdwatching live at Cool Beans", "channel": "chris sloan"},
    "topicjulia1": {"artist": "Julia Set", "title": "one", "channel": "Julia Set - Topic"},
    "fullsetsk01": {"artist": "skimp", "title": "skimp full set", "channel": "skimp"},
}


def fake_judge(artist, plays, found, info):
    picks = {
        "skimp": [{"number": 2, "tier": 2, "video_id": "liveskimp01", "start": None, "confident": True,
                   "note": "Cool Beans 2022"},
                  {"number": 3, "tier": 1, "video_id": "fullsetsk01", "start": "4:10", "confident": True,
                   "note": "full set"}],
        "Julia Set": [{"number": 4, "tier": 3, "video_id": "topicjulia1", "start": None, "confident": True,
                       "note": ""}],
    }
    return picks.get(artist, [])


class Catalog:
    def __init__(self):
        self.artists = MemoryTable(catalog.ARTISTS, "Artist", ("Tags",),
                                   [{"Artist": "skimp", "Bandcamp page": "https://skimp.bandcamp.com"}])
        self.releases = MemoryTable(catalog.RELEASES, ("Album", "Artist"), ("Tags",),
                                    [{"Album": "volume one", "Artist": "Julia Set",
                                      "Album link": "https://juliaset.bandcamp.com/album/volume-one"}])
        self.playlists = MemoryTable(catalog.PLAYLISTS, ("Episode", "#"))


def test_propose_review_then_create(tmp_path, monkeypatch):
    ep = make_episode(tmp_path, monkeypatch)
    (ep.folder / "MFYN_tracklist_03.png").write_bytes(b"png")
    cat, yt = Catalog(), FakeYouTube(LIBRARY)
    run = lambda answers: playlist.for_episode(ep, ask=lambda q: answers.pop(0), say=lambda *a: None,
                                               cat=cat, youtube=yt, judge=fake_judge)

    ok, summary = run([])
    assert ok and "1 band live, 1 other live, 1 official, 1 not found, 1 to decide" in summary
    rows = {r["#"]: r for r in cat.playlists.rows}
    assert rows["1"]["Use"] == "no" and rows["1"]["Note"] == "No match found."
    assert rows["2"]["Use"] == "ask" and rows["2"]["Uploader"] == "chris sloan"
    assert rows["3"]["Use"] == "yes" and rows["3"]["Link"].endswith("&t=250s")
    assert rows["4"]["Link"] == "https://music.youtube.com/watch?v=topicjulia1"
    assert rows["4"]["Bandcamp"] == "https://juliaset.bandcamp.com/album/volume-one"
    assert rows["2"]["Bandcamp"] == "https://skimp.bandcamp.com"
    searched = len(yt.searches)
    assert searched == 7          # one live search per artist (3), one per track (4)

    # Not reviewed yet: nothing is asked or made, and YouTube isn't searched again.
    ok, summary = run([])
    assert ok and summary == "waiting for your review: 1 row(s) to decide" and len(yt.searches) == searched

    rows["2"]["Use"] = "yes"
    ok, summary = run(["n"])
    assert ok and summary == "reviewed, not created yet" and not yt.calls

    ok, summary = run(["y"])
    assert ok, summary
    assert yt.items == ["liveskimp01", "fullsetsk01", "topicjulia1"]
    kind, body = yt.calls[0]
    assert kind == "playlist"
    assert body["snippet"]["title"] == "Music for Your Neighbors No. 3 – Normal Show-Skramish (5 November 2026)"
    assert "skimp: https://skimp.bandcamp.com" in body["snippet"]["description"]
    assert body["status"]["privacyStatus"] == "public"
    assert ("image", {"snippet": {"playlistId": "PL123", "type": "hero"}}) in yt.calls
    assert all(r["Playlist"] == "https://www.youtube.com/playlist?list=PL123" for r in cat.playlists.rows)

    ok, summary = run([])
    assert ok and summary.startswith("already made")


def test_a_full_set_goes_in_once_and_made_up_ids_are_dropped(tmp_path, monkeypatch):
    ep = make_episode(tmp_path, monkeypatch)
    numbered = list(enumerate(reaper.running_order(ep), 1))[1:3]
    found = {"fullsetsk01": {"title": "full set", "channel": "skimp"}}
    picks = [{"number": 2, "tier": 1, "video_id": "fullsetsk01", "start": None, "confident": True, "note": ""},
             {"number": 3, "tier": 1, "video_id": "invented123", "start": None, "confident": True, "note": ""}]
    rows = playlist.rows_for(ep, numbered, picks, found)
    assert rows[1]["Tier"] == "none found" and "wasn't in the search results" in rows[1]["Note"]
    rows[1].update(Link=rows[0]["Link"], Use="yes")
    playlist.mark_repeats(rows)
    assert rows[1]["Note"].startswith("Same video as #2")
    assert playlist.wanted_videos(rows) == ["fullsetsk01"]


def test_a_stopped_run_is_topped_up_later(tmp_path, monkeypatch):
    ep = make_episode(tmp_path, monkeypatch)
    cat, yt = Catalog(), FakeYouTube(LIBRARY)
    run = lambda answers: playlist.for_episode(ep, ask=lambda q: answers.pop(0), say=lambda *a: None,
                                               cat=cat, youtube=yt, judge=fake_judge)
    run([])
    for r in cat.playlists.rows:
        r["Use"] = "yes" if r["Link"] else "no"
    yt.fail_after = 1
    ok, summary = run(["y"])
    assert not ok and "1 video(s) added, then stopped" in summary
    yt.fail_after = None
    ok, summary = run(["y"])
    assert ok and yt.items == ["liveskimp01", "fullsetsk01", "topicjulia1"]
    assert [c for c in yt.calls if c[0] == "playlist"].__len__() == 1


def test_no_reaper_project(tmp_path, monkeypatch):
    ep = make_episode(tmp_path, monkeypatch)
    for p in ep.folder.glob("*.rpp"):
        p.unlink()
    ok, summary = playlist.for_episode(ep, cat=Catalog(), youtube=FakeYouTube({}), say=lambda *a: None)
    assert not ok and "Reaper project not found" in summary


def test_claude_reply_is_read(tmp_path):
    reply = {"is_error": False, "structured_output": {"picks": [{"number": 1, "tier": 3, "video_id": "x"}]}}
    seen = {}

    def fake_run(cmd, input, **kw):
        seen["cmd"], seen["input"] = cmd, input
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(reply), stderr="")
    play = reaper.Play(0, "Squee", "wasted", "squee")
    picks = playlist.ask_claude("Squee", [(6, play)], {"x": {"id": "x"}}, "Bandcamp page: q", run=fake_run,
                                claude="claude")
    assert picks == [{"number": 1, "tier": 3, "video_id": "x"}]
    assert "6. wasted (from squee)" in seen["input"] and "--json-schema" in seen["cmd"]


def test_description_has_no_angle_brackets(tmp_path):
    ep = episode.Episode(tmp_path, datetime.date(2026, 11, 5), "x")
    rows = [{"Use": "yes", "Artist": "<A>", "Bandcamp": ""}]
    assert "<" not in playlist.description(ep, rows)
