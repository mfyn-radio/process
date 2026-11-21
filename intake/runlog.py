"""The MFYN Run Log Google Sheet: what the automations have done, for the
status page. See docs/run-log.md.

Tabs:
- Runs: one row each time an automation finishes something (an album added,
  an episode's video posts made, a Story made) or fails at it.
- Last run: one row per automation, overwritten on every run, so a stopped
  Task Scheduler task shows up as a stale time.

The log is a convenience. Writing to it never stops an automation: if the
sheet can't be reached, a warning goes to the automation's own log file and
the run carries on.
"""
import datetime
import logging

from googleapiclient.discovery import build

from . import config, google_auth
from .catalog import find_or_create
from .table import Table

OK, FAILED, EXCLUDED = "ok", "failed", "excluded"

RUNS = ["Time", "Automation", "About", "Result", "Details"]
LAST_RUN = ["Automation", "Last run", "Result", "Details"]

log = logging.getLogger("runlog")


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


class RunLog:
    """Rows for one automation ("Acquire", "Make Episode Content", ...)."""

    def __init__(self, automation, runs=None, last_run=None):
        self.automation = automation
        self.runs = runs
        self.last_run = last_run
        self.summary = ""      # what the run did, for Last run's Details
        self.added_failure = False

    @classmethod
    def open(cls, automation):
        """The run log, or one that writes nothing if the sheet can't be opened."""
        try:
            creds = google_auth.credentials()
            drive = build("drive", "v3", credentials=creds, cache_discovery=False)
            sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
            sheet_id = find_or_create(drive, sheets, config.RUN_LOG_SHEET, "Runs")
            return cls(automation,
                       Table(sheets, sheet_id, "Runs", RUNS, key=("Time", "Automation", "About")),
                       Table(sheets, sheet_id, "Last run", LAST_RUN, key="Automation"))
        except (Exception, SystemExit) as e:
            log.warning("Couldn't open the %s sheet (%s). This run won't be logged there.", config.RUN_LOG_SHEET, e)
            return cls(automation)

    def add(self, about, result, details=""):
        """A row in Runs: what this was about (an album, an episode) and how it went."""
        self.added_failure = self.added_failure or result == FAILED
        if self.runs is None:
            return
        try:
            row = {"Time": now(), "Automation": self.automation, "About": about,
                   "Result": result, "Details": details}
            self.runs._append_row([row.get(c, "") for c in self.runs.header])
        except Exception as e:
            log.warning("Couldn't write to the %s sheet (%s).", config.RUN_LOG_SHEET, e)

    def finish(self, result, details=""):
        """Overwrite this automation's row in Last run."""
        if self.last_run is None:
            return
        try:
            row = {"Automation": self.automation, "Last run": now(), "Result": result, "Details": details}
            index, existing = self.last_run.find(row)
            if existing is None:
                self.last_run.upsert(row)
            else:
                self.last_run.set(index, {k: v for k, v in row.items() if k != "Automation"})
        except Exception as e:
            log.warning("Couldn't write to the %s sheet (%s).", config.RUN_LOG_SHEET, e)

    def failed(self, errors):
        """The run as a whole failed. Adds a row unless one was already added."""
        details = "; ".join(errors)
        if not self.added_failure:
            self.add("(the run)", FAILED, details)
        self.finish(FAILED, details)


class _Errors(logging.Handler):
    """Keeps the ERROR lines logged during a run, for the log's Details."""

    def __init__(self):
        super().__init__(logging.ERROR)
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage().strip())


def track(automation, run_main):
    """Run an automation's main(run) and log how it ended.

    run_main gets the RunLog, to add rows for what it did, and returns the exit
    code. Last run is always updated. A run that failed without adding a
    failed row of its own (it stopped early, or crashed) gets one, with the
    errors it logged."""
    run = RunLog.open(automation)
    errors = _Errors()
    logging.getLogger().addHandler(errors)
    try:
        code = run_main(run)
    except (KeyboardInterrupt, SystemExit) as e:
        if isinstance(e, SystemExit) and e.code:   # e.g. not signed in to Google
            run.failed(errors.lines + [str(e.code)])
        raise
    except Exception as e:
        run.failed(errors.lines + [f"{type(e).__name__}: {e}"])
        raise
    finally:
        logging.getLogger().removeHandler(errors)
    if code:
        run.failed(errors.lines)
    else:
        run.finish(OK, run.summary)
    return code
