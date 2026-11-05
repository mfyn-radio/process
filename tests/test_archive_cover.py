import datetime
import stat
import sys

from intake import archive_cover, config, episode
from test_reels import FAKE_PROCESSING


def archive_with(tmp_path, *names):
    for n in names:
        (tmp_path / n).mkdir()
    return episode.all_in(tmp_path)


def test_numbers_start_at_3_on_5_november_and_count_up(tmp_path):
    eps = archive_with(tmp_path, "1_10_2026- Old One", "5_11_2026-Normal Show-Skramish",
                       "19_11_2026- Later", "12_11_2026- Next")
    numbers = {e.folder.name: archive_cover.number_for(e, eps) for e in eps}
    assert numbers == {"1_10_2026- Old One": None, "5_11_2026-Normal Show-Skramish": 3,
                       "12_11_2026- Next": 4, "19_11_2026- Later": 5}


def test_date_and_file_name():
    assert archive_cover.cover_date(datetime.date(2026, 11, 5)) == "5 November 2026"
    assert archive_cover.cover_name(3) == "MFYN_archive_03.png"
    assert archive_cover.cover_name(100) == "MFYN_archive_100.png"


def test_make_saves_in_the_episode_folder_once(tmp_path, monkeypatch):
    fake = tmp_path / "processing-java"
    fake.write_text(FAKE_PROCESSING.format(python=sys.executable))
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr(config, "PROCESSING", str(fake))
    archive = tmp_path / "archive"
    archive.mkdir()
    eps = archive_with(archive, "5_11_2026-Normal Show-Skramish", "12_11_2026- Next")
    answers, shown = iter(["n", "n", ""]), []
    made = archive_cover.make(eps[1], eps, ask=lambda p: next(answers), show=shown.append)
    assert made == archive / "12_11_2026- Next" / "MFYN_archive_04.png"
    assert made.read_text() == "12 November 2026"
    assert len(shown) == 3                       # two turned down, the third kept

    monkeypatch.setattr(config, "PROCESSING", str(tmp_path / "missing"))   # would fail if it ran again
    assert archive_cover.make(eps[1], eps, ask=None, show=None) == made
    assert archive_cover.make(archive_with(archive, "1_10_2026- Old")[0], episode.all_in(archive)) is None
