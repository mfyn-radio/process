import json

from intake import catalog, config, research, show_notes
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
    monkeypatch.setattr(config, "RESEARCH_DIR", tmp_path / "research")
    monkeypatch.setattr(research, "open_catalog", SheetCatalog)

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
    assert applied["research_file"].endswith("applied communications.md") and not applied["research_exists"]
    (album,) = applied["albums"]
    assert [t["position"] for t in album["tracks"]] == [1, 3]
    assert album["sheet"]["Label"] == "Some Label" and album["label"]["Instagram"] == "@somelabel"
    assert other["sheet"] == {} and other["albums"][0]["sheet"] == {}


def test_facts_without_the_sheet(tmp_path, monkeypatch, capsys):
    archive = episode_folder(tmp_path)
    (archive / "5_11_2026- Official Unofficial" / show_notes.NOTES_FILE).write_text("old notes")
    monkeypatch.setattr(config, "SHOW_ARCHIVE_DIR", archive)
    monkeypatch.setattr(config, "RESEARCH_DIR", tmp_path / "research")
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "Other Artist.md").write_text("# Other Artist")

    assert show_notes.main(["--no-sheet"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert not out["sheet_read"] and out["notes_exist"]
    assert [a["name"] for a in out["artists"]] == ["applied communications", "Other Artist"]
    assert [a["research_exists"] for a in out["artists"]] == [False, True]


def test_research_file_names_are_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RESEARCH_DIR", tmp_path)
    assert research.research_file("AC/DC").name == "AC_DC.md"
    assert research.research_file("Daufødt").name == "Daufødt.md"


def test_artist_facts_cover_all_their_releases(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "RESEARCH_DIR", tmp_path)
    monkeypatch.setattr(research, "open_catalog", SheetCatalog)
    assert research.main(["--artist", "applied communications"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["sheet_read"] and out["sheet"]["Location"] == "Brooklyn, New York"
    (release,) = out["releases"]
    assert release["sheet"]["Album"] == "bites the big one" and release["label"]["Instagram"] == "@somelabel"
    assert not out["research_exists"]
