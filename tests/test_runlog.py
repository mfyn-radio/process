import logging

import pytest

from intake import runlog
from intake.table import Table


class MemoryTable(Table):
    """A Table kept in memory instead of a Google Sheet."""

    def __init__(self, columns, key):
        self.tab, self.columns, self.list_fields = "t", columns, ()
        self.key = key if isinstance(key, tuple) else (key,)
        self.header = list(columns)
        self.rows = []
        self.appended = []  # rows written to the sheet

    def _append_row(self, values):
        self.appended.append(dict(zip(self.header, values)))

    def _write_cells(self, data):
        pass


@pytest.fixture
def sheet(monkeypatch):
    runs = MemoryTable(runlog.RUNS, ("Time", "Automation", "About"))
    last = MemoryTable(runlog.LAST_RUN, "Automation")
    monkeypatch.setattr(runlog.RunLog, "open", classmethod(lambda cls, name: cls(name, runs, last)))
    return runs, last


def test_ok_run_logs_its_rows_and_last_run(sheet):
    runs, last = sheet

    def main(run):
        run.add("Artist - Album", runlog.OK, "added")
        run.summary = "1 purchase email(s) checked"
        return 0

    assert runlog.track("Acquire", main) == 0
    assert [(r["Automation"], r["About"], r["Result"]) for r in runs.appended] == [("Acquire", "Artist - Album", "ok")]
    assert [(r["Automation"], r["Result"], r["Details"]) for r in last.rows] == [
        ("Acquire", "ok", "1 purchase email(s) checked")]


def test_last_run_is_overwritten_not_added(sheet):
    _, last = sheet
    runlog.track("Acquire", lambda run: 0)
    runlog.track("Acquire", lambda run: 1)
    runlog.track("Make Reels", lambda run: 0)
    assert [(r["Automation"], r["Result"]) for r in last.rows] == [("Acquire", "failed"), ("Make Reels", "ok")]


def test_early_failure_gets_a_row_with_its_errors(sheet):
    runs, last = sheet

    def main(run):
        logging.getLogger("reels").error("Show archive not found. Is Google Drive for desktop running?")
        return 1

    assert runlog.track("Make Reels", main) == 1
    assert [(r["About"], r["Result"]) for r in runs.appended] == [("(the run)", "failed")]
    assert "Show archive not found" in runs.appended[0]["Details"]
    assert last.rows[0]["Result"] == "failed"


def test_failure_already_logged_is_not_logged_twice(sheet):
    runs, _ = sheet

    def main(run):
        run.add("5_11_2026- Episode", runlog.FAILED, "1 failed")
        return 1

    runlog.track("Make Reels", main)
    assert [r["About"] for r in runs.appended] == ["5_11_2026- Episode"]


def test_crash_is_logged_and_raised(sheet):
    runs, last = sheet

    def main(run):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        runlog.track("Album Story", main)
    assert "RuntimeError: boom" in runs.appended[0]["Details"]
    assert last.rows[0]["Result"] == "failed"


def test_no_sheet_writes_nothing_and_never_fails():
    log = runlog.RunLog("Acquire")
    log.add("x", runlog.OK)
    log.finish(runlog.OK)


def test_sheet_errors_are_only_warnings(sheet, caplog):
    runs, _ = sheet
    runs._append_row = lambda values: (_ for _ in ()).throw(OSError("offline"))
    assert runlog.track("Acquire", lambda run: run.add("x", runlog.OK) or 0) == 0
    assert "offline" in caplog.text


def test_the_error_that_stopped_a_run_goes_to_its_log_file(sheet, caplog):
    runs, last = sheet

    def main(run):
        raise SystemExit("The saved Google sign-in is missing newer permissions.")

    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit):
        runlog.track("Event Calendar", main)
    assert "missing newer permissions" in caplog.text
    assert last.rows[0]["Result"] == "failed"
    assert "missing newer permissions" in last.rows[0]["Details"]
