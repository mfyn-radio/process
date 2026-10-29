import datetime
import json

from intake import config, create_show, playlist, reels
from test_reels import flac

LD_PLAYLIST = json.dumps({
    "@type": "MusicPlaylist",
    "name": "mfyn nov 2026",
    "track": {"@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "position": 2, "item": {
            "@type": "MusicRecording", "name": "Toxic", "byArtist": {"name": "Daufødt"}, "inAlbum": {"name": "Glitter"}}},
        {"@type": "ListItem", "position": 1, "item": {
            "@type": "MusicRecording", "name": "Glitter", "byArtist": {"name": "Daufødt"}, "inAlbum": {"name": "Glitter"},
            "@id": "https://daufodt.bandcamp.com/track/glitter"}},
    ]},
})

BLOB = json.dumps({
    "fan_data": {"name": "Music for Your Neighbors"},
    "recommendations": [{"title": f"Other {i}", "band_name": "Someone"} for i in range(5)],
    "playlist_data": {"title": "mfyn nov 2026", "tracks": [
        {"track_title": "donna deegan", "band_name": "applied communications", "album_title": "bites the big one"},
        {"track_title": "Glitter", "band_name": "Daufødt", "album_title": "Glitter"},
    ]},
})


def test_parse_json_ld_playlist_in_order():
    tracks = playlist.parse([LD_PLAYLIST])
    assert [(t.artist, t.title, t.album) for t in tracks] == [("Daufødt", "Glitter", "Glitter"), ("Daufødt", "Toxic", "Glitter")]
    assert tracks[0].url == "https://daufodt.bandcamp.com/track/glitter"


def test_parse_embedded_blob_prefers_the_playlist_list():
    escaped = BLOB.replace('"', "&quot;")  # as it comes out of an HTML attribute
    tracks = playlist.parse(['{"@type": "WebPage"}'], [escaped])
    assert [t.title for t in tracks] == ["donna deegan", "Glitter"]
    assert tracks[0].album == "bites the big one"


def test_private_playlist_page():
    # What Bandcamp answered for a private playlist, trimmed.
    page = ('<title>Error</title><h2>Sorry, that something isn’t here.</h2><script data-status="404" '
            'data-class="&quot;Endpoints::AccessError&quot;" data-message="&quot;failed private_viewing_screened '
            'before_call&quot;"></script>')
    assert playlist.is_private(page)
    assert not playlist.is_private("<html>a normal page</html>")


def test_parse_nothing():
    assert playlist.parse(["not json"], ['{"a": 1}']) == []


def library(tmp_path):
    lib = tmp_path / "library"
    glitter = lib / "Daufødt - Glitter"
    glitter.mkdir(parents=True)
    flac(glitter / "Daufødt - Glitter - 01 Glitter.flac", "Daufødt", "Glitter", "Glitter")
    flac(glitter / "Daufødt - Glitter - 03 Toxic.flac", "Daufødt", "Toxic", "Glitter")
    ac = lib / "applied communications - applied communications bites the big one"
    ac.mkdir()
    # File name and album differ from the playlist; the title tag still matches.
    flac(ac / "applied communications - bites the big one - 01 donna deegan.flac",
         "applied communications", "Donna Deegan", "applied communications bites the big one")
    single = lib / "Someone - A Single"
    single.mkdir()
    (single / "Someone - A Single.flac").write_bytes(b"not really audio")
    (lib / ".partial - Daufødt - Glitter").mkdir()
    return lib


def test_find_file(tmp_path):
    lib = library(tmp_path)
    find = lambda *t: create_show.find_file(lib, playlist.PlaylistTrack(*t))
    assert find("Daufødt", "Toxic", "Glitter").name == "Daufødt - Glitter - 03 Toxic.flac"
    assert find("Daufødt", "Glitter", "Glitter").name == "Daufødt - Glitter - 01 Glitter.flac"
    assert find("applied communications", "donna deegan", "bites the big one").name.endswith("donna deegan.flac")
    assert find("Someone", "A Single", "").name == "Someone - A Single.flac"  # by file name
    assert find("Daufødt", "Not On It", "Glitter") is None
    assert find("Nobody", "Toxic", "Elsewhere") is None


def test_placeholder_names(tmp_path):
    day = datetime.date(2026, 11, 12)
    assert create_show.episode_folder(tmp_path, day).name == "12_11_2026- Normal Show"
    flac_dir = tmp_path / "5_11_2026- Normal Show" / "Tracks"
    flac_dir.mkdir(parents=True)
    flac(flac_dir / "a.flac", "A", "B")
    assert create_show.episode_folder(tmp_path, day).name == "12_11_2026- Normal Show 1"
    (tmp_path / "1_1_2027- Normal Show 4" / "Tracks").mkdir(parents=True)
    (tmp_path / "1_1_2027- Normal Show 4" / "Tracks" / "x.flac").write_bytes(b"")
    (tmp_path / "2_1_2027- Renamed Show").mkdir()
    assert create_show.episode_folder(tmp_path, day).name == "12_11_2026- Normal Show 5"
    # An empty placeholder is filled rather than making another.
    (tmp_path / "3_1_2027- Normal Show 5").mkdir()
    assert create_show.episode_folder(tmp_path, day).name == "3_1_2027- Normal Show 5"
    assert create_show.episode_folder(tmp_path, day, "Spooky: Special").name == "12_11_2026- Spooky_ Special"


def test_create_show_end_to_end(tmp_path, monkeypatch):
    lib = library(tmp_path)
    archive = tmp_path / "archive"
    (archive / "5_11_2026- Normal Show" / "Tracks").mkdir(parents=True)  # emptied, so it's reused
    monkeypatch.setattr(config, "LIBRARY_DIR", lib)
    monkeypatch.setattr(config, "SHOW_ARCHIVE_DIR", archive)
    monkeypatch.setattr(config, "APP_DIR", tmp_path / "app")
    monkeypatch.setattr(config, "CREATE_SHOW_LOG_FILE", tmp_path / "app" / "create_show.log")
    handed_over = []
    monkeypatch.setattr(reels, "main", lambda argv, ask: handed_over.append(argv) or 0)

    tracks = playlist.parse([LD_PLAYLIST])
    assert create_show.main(["https://bandcamp.com/x/playlist/y"], read=lambda url, ask: tracks) == 0
    copied = sorted(p.name for p in (archive / "5_11_2026- Normal Show" / "Tracks").iterdir())
    assert copied == ["Daufødt - Glitter - 01 Glitter.flac", "Daufødt - Glitter - 03 Toxic.flac"]
    assert handed_over == [["--episode", "5_11_2026- Normal Show"]]

    # A missing track stops it before anything is created.
    missing = tracks + [playlist.PlaylistTrack("Nobody", "Nothing", "None")]
    assert create_show.main(["link", "--date", "19_11_2026"], read=lambda url, ask: missing) == 1
    assert not (archive / "19_11_2026- Normal Show 1").exists()
    assert len(handed_over) == 1


def test_find_prefers_the_exact_folder(tmp_path):
    for name in ("5_11_2026- Normal Show", "12_11_2026- Normal Show 1"):
        (tmp_path / name).mkdir()
    assert create_show.episode.find(tmp_path, "5_11_2026- Normal Show").name == "Normal Show"
    assert create_show.episode.find(tmp_path, "normal show").name == "Normal Show 1"


def test_private_playlist_asks_to_sign_in_once(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DIR", tmp_path)
    monkeypatch.setattr(config, "CHROME_PROFILE_DIR", tmp_path / "chrome-profile")
    pages = iter([([], [], "Endpoints::AccessError private_viewing_screened"), ([LD_PLAYLIST], [], "<html>")])
    seen = []

    class FakeBrowser:
        def __init__(self, download_dir, profile_dir=None):
            seen.append(("profile", profile_dir))
        def read_playlist(self, url):
            return next(pages)
        def open(self, url):
            seen.append(("open", url))
        def close(self):
            seen.append(("close",))

    monkeypatch.setattr(create_show.bandcamp, "Browser", FakeBrowser)
    asked = []
    tracks = create_show.read_playlist("link", ask=asked.append)
    assert [t.title for t in tracks] == ["Glitter", "Toxic"]
    assert len(asked) == 1
    assert seen == [("profile", tmp_path / "chrome-profile"), ("open", config.BANDCAMP_LOGIN), ("close",)]


def test_profile_in_use_is_reported_not_raised(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(config, "CHROME_PROFILE_DIR", tmp_path / "chrome-profile")

    class BusyBrowser:
        def __init__(self, download_dir, profile_dir=None):
            pass
        def read_playlist(self, url):
            raise create_show.bandcamp.ProfileInUse("session not created: Chrome failed to start: crashed.")
        def close(self):
            pass

    monkeypatch.setattr(create_show.bandcamp, "Browser", BusyBrowser)
    assert create_show.read_playlist("link", ask=lambda p: "") == []
    assert "still open" in caplog.text
