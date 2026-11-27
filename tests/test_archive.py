import datetime

import pytest

from intake import archive, config, content


def workspace(tmp_path):
    work, arch = tmp_path / "MFYN_Workspace", tmp_path / "MFYN_Show_Archive"
    (work / "2026_December_3" / "Tracks").mkdir(parents=True)
    (work / "2026_December_3" / "Tracks" / "01 - A - Song.flac").write_bytes(b"flac" * 100)
    (work / "2026_December_3" / "2026_December.rpp").write_text("<REAPER_PROJECT\n>")
    (work / "2026_December_3" / "2026_December_show_cards.md").write_text("# Show cards")
    (work / "2026_December_3" / "MFYN December.wav").write_bytes(b"wav" * 1000)
    (work / "2026_December_3" / "2026_December.rpp-bak").write_text("old")
    (work / "2026_December_3" / "Tracks" / "01 - A - Song.flac.reapeaks").write_bytes(b"pk")
    (work / "2026_December_3" / "Backups").mkdir()
    (work / "2026_December_3" / "Backups" / "x.rpp").write_text("old")
    arch.mkdir()
    return work, arch


def test_air_date():
    from pathlib import Path
    assert archive.air_date(Path("2026_December_3")) == datetime.date(2026, 12, 3)
    assert archive.air_date(Path("2026_december_03 final")) == datetime.date(2026, 12, 3)
    assert archive.air_date(Path("2026_December")) is None
    assert archive.air_date(Path("2026_February_31")) is None


def test_archives_everything_but_reapers_caches_and_keeps_the_local_folder(tmp_path):
    work, arch = workspace(tmp_path)
    answers = iter(["y", "", "Holiday Noise"])
    ep = archive.offer(ask=lambda q: next(answers), say=lambda *a: None, work_dir=work, archive_dir=arch,
                       remove_local=False)
    dest = arch / "3_12_2026- Holiday Noise"
    assert ep.folder == dest and ep.air_date == datetime.date(2026, 12, 3) and ep.name == "Holiday Noise"
    assert sorted(str(p.relative_to(dest)).replace("\\", "/") for p in dest.rglob("*") if p.is_file()) == [
        "2026_December.rpp", "2026_December_show_cards.md", "MFYN December.wav", "Tracks/01 - A - Song.flac"]
    assert (work / "2026_December_3").is_dir()
    assert len(ep.tracks()) == 1
    # Archived now, so it isn't offered again.
    assert archive.pending(work, arch) == []


def test_removes_the_local_folder_when_set(tmp_path):
    work, arch = workspace(tmp_path)
    answers = iter(["y", "Name"])
    assert archive.offer(ask=lambda q: next(answers), say=lambda *a: None, work_dir=work, archive_dir=arch,
                         remove_local=True)
    assert not (work / "2026_December_3").exists()


def test_never_overwrites_and_says_no(tmp_path):
    work, arch = workspace(tmp_path)
    (arch / "3_12_2026- Name").mkdir()
    (arch / "3_12_2026- Name" / "keep.txt").write_text("mine")
    assert archive.pending(work, arch) == []     # same air date is already in the archive
    with pytest.raises(FileExistsError):
        archive.copy_folder(work / "2026_December_3", arch / "3_12_2026- Name")
    assert (arch / "3_12_2026- Name" / "keep.txt").read_text() == "mine"


def test_no_means_nothing_happens_and_undated_folders_are_pointed_out(tmp_path):
    work, arch = workspace(tmp_path)
    assert archive.offer(ask=lambda q: "n", say=lambda *a: None, work_dir=work, archive_dir=arch) is None
    assert list(arch.iterdir()) == []
    (work / "2026_December_3").rename(work / "2026_December")
    said = []
    assert archive.offer(ask=lambda q: pytest.fail("asked"), say=said.append, work_dir=work, archive_dir=arch) is None
    assert "add the air day" in said[0]


def test_make_episode_content_archives_first_and_works_on_that_episode(tmp_path, monkeypatch):
    work, arch = workspace(tmp_path)
    monkeypatch.setattr(config, "WORK_DIR", work)
    monkeypatch.setattr(config, "SHOW_ARCHIVE_DIR", arch)
    monkeypatch.setattr(config, "CONTENT_LOG_FILE", tmp_path / "content.log")
    monkeypatch.setattr(content.reels, "read_track", lambda p: type("T", (), {"artist": "A", "title": "Song"})())
    answers = iter(["y", "Holiday Noise", "n"])     # archive it, its name, then no content
    assert content.main([], ask=lambda q: next(answers), say=lambda *a: None) == 0
    assert (arch / "3_12_2026- Holiday Noise" / "Tracks" / "01 - A - Song.flac").is_file()
