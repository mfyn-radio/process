import json

from intake import captions, catalog
from test_catalog import MemoryTable

DETAILS = {
    "artist": "applied communications", "title": "donna deegan", "album": "bites the big one",
    "label": "Knife Hits", "release_date": "2026-09-12",
    "artist_instagram": "@old.handle", "artist_instagram_status": "Confirmed",
    "label_instagram": "@knifehits", "label_instagram_status": "Confirmed",
    "episode": {"name": "Official Unofficial", "air_date": "2026-11-05", "folder": "5_11_2026- Official Unofficial"},
}


class FakeCatalog:
    def __init__(self, artists=(), labels=()):
        self.artists = MemoryTable(catalog.ARTISTS, "Artist", ("Tags",), rows=artists)
        self.labels = MemoryTable(catalog.LABELS, "Label", rows=labels)


def test_caption_uses_the_template():
    assert captions.caption(DETAILS) == (
        "Music worth paying for, follow to find and support an artist\n\n"
        "Artist: @old.handle\n"
        "Song Title: donna deegan\n"
        "Album: bites the big one\n\n"
        "Label: @knifehits\n"
        "Release Date: 12 September 2026\n\n"
        "Air Date: 5 November 2026 – Official Unofficial\n")


def test_handles_are_looked_up_again_and_only_confirmed_ones_tagged():
    cat = FakeCatalog(
        artists=[{"Artist": "applied communications", "Instagram": "@new.handle", "Status": "Confirmed"}],
        labels=[{"Label": "Knife Hits", "Instagram": "@maybe", "Status": "Suggested"}])
    text = captions.caption(DETAILS, cat)
    assert "Artist: @new.handle\n" in text
    assert "Label: Knife Hits\n" in text


def test_no_instagram_self_released_and_missing_fields():
    details = dict(DETAILS, label="Self-released", release_date="", album="",
                   artist_instagram="", artist_instagram_status="No Instagram",
                   episode={"name": "", "air_date": "2026-11-05"})
    assert captions.caption(details) == (
        "Music worth paying for, follow to find and support an artist\n\n"
        "Artist: applied communications\n"
        "Song Title: donna deegan\n\n"
        "Label: Self-released\n\n"
        "Air Date: 5 November 2026\n")


def test_write_all_skips_reels_that_have_a_caption(tmp_path):
    (tmp_path / "A - One.json").write_text(json.dumps(DETAILS), encoding="utf-8")
    (tmp_path / "B - Two.json").write_text(json.dumps(DETAILS), encoding="utf-8")
    (tmp_path / "B - Two.txt").write_text("edited by hand", encoding="utf-8")
    assert captions.write_all(tmp_path) == 1
    assert (tmp_path / "A - One.txt").read_text(encoding="utf-8").startswith(captions.OPENING)
    assert (tmp_path / "B - Two.txt").read_text(encoding="utf-8") == "edited by hand"
