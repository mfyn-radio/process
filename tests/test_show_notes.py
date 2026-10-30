import json

from intake import catalog, config, show_notes
from test_catalog import MemoryTable
from test_reels import flac


class SheetCatalog:
    def __init__(self):
        self.artists = MemoryTable(catalog.ARTISTS, "Artist", ("Tags",), [
            {"Artist": "applied communications", "Instagram": "@applied", "Status": "Confirmed",
             "Location": "Brooklyn, New York"},
        ])
        self.releases = MemoryTable(catalog.RELEASES, ("Album", "Artist"), ("Tags",), [
            {"Album": "bites the big one", "Artist": "applied communications", "Label": "Some Label",
             "Release date": "2026-10-01", "Tags": "ambient, drone"},
        ])
        self.labels = MemoryTable(catalog.LABELS, "Label", rows=[
            {"Label": "Some Label", "Instagram": "@somelabel", "Status": "Suggested"},
        ])


def episode_folder(tmp_path):
    tracks = tmp_path / "5_11_2026- Official Unofficial" / "Tracks"
    tracks.mkdir(parents=True)
    flac(tracks / "01.flac", "applied communications", "donna deegan", "bites the big one")
    flac(tracks / "02.flac", "Other Artist", "Song Two", "Other Album")
    flac(tracks / "03.flac", "applied communications", "second one", "bites the big one")
    return tmp_path


def test_facts_group_by_artist_and_album_with_sheet_rows(tmp_path, monkeypatch, capsys):
    archive = episode_folder(tmp_path)
    monkeypatch.setattr(config, "SHOW_ARCHIVE_DIR", archive)
    monkeypatch.setattr(show_notes.google_auth, "credentials", lambda: None)
    monkeypatch.setattr(show_notes.catalog, "Catalog", lambda creds: SheetCatalog())

    assert show_notes.main([]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["episode"] == {"name": "Official Unofficial", "air_date": "2026-11-05",
                              "folder": "5_11_2026- Official Unofficial"}
    assert out["notes_file"].endswith("Show Notes.md") and not out["notes_exist"]
    assert out["sheet_read"]
    assert [(t["position"], t["title"]) for t in out["running_order"]] == [
        (1, "donna deegan"), (2, "Song Two"), (3, "second one")]

    applied, other = out["artists"]
    assert applied["sheet"]["Instagram"] == "@applied"
    (album,) = applied["albums"]
    assert [t["position"] for t in album["tracks"]] == [1, 3]
    assert album["sheet"]["Label"] == "Some Label" and album["label"]["Instagram"] == "@somelabel"
    assert other["sheet"] == {} and other["albums"][0]["sheet"] == {}


def test_facts_without_the_sheet(tmp_path, monkeypatch, capsys):
    archive = episode_folder(tmp_path)
    (archive / "5_11_2026- Official Unofficial" / show_notes.NOTES_FILE).write_text("old notes")
    monkeypatch.setattr(config, "SHOW_ARCHIVE_DIR", archive)

    assert show_notes.main(["--no-sheet"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert not out["sheet_read"] and out["notes_exist"]
    assert [a["name"] for a in out["artists"]] == ["applied communications", "Other Artist"]
