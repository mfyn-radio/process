"""The MFYN Catalog base on Airtable, as tables with the same find, upsert, set
and rows as a Google Sheet tab (intake/table.py), so the automations read and
write it the same way. See docs/airtable.md.

Rows are plain text, as in the sheet: a multi-select (Tags) reads as
"a, b, c". Linked-record fields ("Linked artists" and so on) are what makes
the base relational. They're kept apart from the rows: the code gives names
and they're matched to records by name. A link only ever gains records, like
tags, so links made by hand stay.

Airtable's free plan allows 1,000 API calls a month, so each run has a
budget (config.AIRTABLE_MAX_CALLS), writes go 10 records to a call, and a
table is only read when it's used.
"""
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from . import config
from .alerts import key as match_key
from .table import merge, split_list

API = "https://api.airtable.com/v0"
BATCH = 10          # records per write call, Airtable's limit
PAUSE = 0.25        # seconds between calls; Airtable allows 5 a second per base

log = logging.getLogger("airtable")


class AirtableError(Exception):
    pass


class OverBudget(AirtableError):
    """The run has used its share of the month's API calls."""


def read_token():
    token = os.environ.get("AIRTABLE_TOKEN", "").strip()
    if not token and config.AIRTABLE_TOKEN_FILE.exists():
        token = config.AIRTABLE_TOKEN_FILE.read_text(encoding="utf-8-sig").strip()
    if not token:
        raise AirtableError(f"No Airtable token. Save it in {config.AIRTABLE_TOKEN_FILE}.")
    return token


def saved_base():
    """The MFYN Catalog base's id, saved by `python -m intake.airtable_setup`."""
    base = os.environ.get("MFYN_AIRTABLE_BASE", "").strip()
    if not base and config.AIRTABLE_FILE.exists():
        base = json.loads(config.AIRTABLE_FILE.read_text()).get("base", "")
    if not base:
        raise AirtableError("Airtable isn't set up on this PC yet. Run: python -m intake.airtable_setup")
    return base


class Client:
    """Calls to the Airtable Web API, counted against a budget."""

    def __init__(self, token, base=None, max_calls=None, opener=urllib.request.urlopen, sleep=time.sleep):
        self._token = token
        self.base = base
        self.max_calls = config.AIRTABLE_MAX_CALLS if max_calls is None else max_calls
        self.calls = 0
        self._open = opener
        self._sleep = sleep

    def request(self, method, path, params=None, body=None):
        if self.calls >= self.max_calls:
            raise OverBudget(f"stopped after {self.calls} Airtable calls, this run's budget")
        url = f"{API}/{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(3):
            self.calls += 1
            req = urllib.request.Request(url, data=data, method=method, headers={
                "Authorization": f"Bearer {self._token}", "Content-Type": "application/json"})
            try:
                with self._open(req, timeout=60) as resp:
                    out = json.loads(resp.read() or b"{}")
                self._sleep(PAUSE)
                return out
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:500]
                if e.code == 429 and attempt < 2:   # too many requests: Airtable asks for 30 s
                    self._sleep(30)
                    continue
                raise AirtableError(f"{method} {path.split('?')[0]}: HTTP {e.code} {detail}") from None

    def _table_path(self, table):
        return f"{self.base}/{urllib.parse.quote(table, safe='')}"

    def list_records(self, table):
        records, params = [], {"pageSize": 100}
        while True:
            page = self.request("GET", self._table_path(table), params)
            records += page.get("records", [])
            if not page.get("offset"):
                return records
            params["offset"] = page["offset"]

    def create(self, table, fields_list):
        made = []
        for i in range(0, len(fields_list), BATCH):
            chunk = [{"fields": f} for f in fields_list[i:i + BATCH]]
            made += self.request("POST", self._table_path(table),
                                 body={"records": chunk, "typecast": True})["records"]
        return made

    def update(self, table, changes):
        """changes: [(record id, fields)]"""
        for i in range(0, len(changes), BATCH):
            chunk = [{"id": rid, "fields": f} for rid, f in changes[i:i + BATCH]]
            self.request("PATCH", self._table_path(table), body={"records": chunk, "typecast": True})


def connect(max_calls=None):
    return Client(read_token(), saved_base(), max_calls)


@dataclass
class Link:
    """A linked-record field. `target` names the Catalog table it links to.
    With `source`, it's filled from that text column when nothing is given
    for it (split on commas if `split`). `create` makes a record in the target
    for a name it doesn't have; otherwise unknown names are skipped."""
    target: str
    source: str = None
    split: bool = False
    create: bool = False


def text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "yes" if value else ""
    return str(value)


class AirtableTable:
    """One table of the base, loaded whole when it's made."""

    def __init__(self, client, name, columns, key, list_fields=(), links=None, resolve=None, primary=None):
        self.client = client
        self.tab = self.name = name
        self.columns = list(columns)
        self.header = list(columns)
        self.key = key if isinstance(key, tuple) else (key,)
        self.list_fields = tuple(list_fields)
        self.links = dict(links or {})
        self.primary = primary or self.columns[0]
        self._resolve = resolve    # name of a Catalog table -> that AirtableTable
        self.rows, self.ids, self.linked, self._loaded = [], [], [], []
        for rec in client.list_records(name):
            fields = rec.get("fields", {})
            self.rows.append({c: text(fields.get(c)) for c in self.columns})
            self.ids.append(rec["id"])
            self.linked.append({f: list(fields.get(f) or []) for f in self.links})
            self._loaded.append(fields)

    def add_columns(self, names):
        """Also read and write these fields (columns someone added by hand)."""
        names = [n for n in names if n not in self.columns]
        self.columns += names
        self.header += names
        for i, row in enumerate(self.rows):
            fields = self._loaded[i] if i < len(self._loaded) else {}
            row.update({n: text(fields.get(n)) for n in names})

    @property
    def url(self):
        return f"https://airtable.com/{self.client.base}"

    # The same lookups as table.Table.
    def _key_of(self, row):
        return tuple((row.get(k) or "").strip().casefold() for k in self.key)

    def find(self, record):
        wanted = self._key_of(record)
        for i, row in enumerate(self.rows):
            if self._key_of(row) == wanted:
                return i, row
        return None, None

    def id_for(self, name, create=False):
        """The record whose primary field is `name`, matched ignoring case and
        accents; made if `create`. None if there isn't one."""
        wanted = match_key(name)
        if not wanted:
            return None
        for i, row in enumerate(self.rows):
            if match_key(row.get(self.primary, "")) == wanted:
                return self.ids[i]
        if create:
            self.upsert({self.primary: name})
            return self.ids[-1]
        return None

    def _link_ids(self, field, names):
        spec = self.links[field]
        target = self._resolve(spec.target)
        ids = []
        for name in names:
            rid = target.id_for(name, create=spec.create)
            if rid and rid not in ids:
                ids.append(rid)
        return ids

    def _wanted_links(self, record):
        """{link field: names} from the record, or from the link's source column."""
        wanted = {}
        for field, spec in self.links.items():
            names = record.pop(field, None)
            if names is None and spec.source and record.get(spec.source):
                value = record[spec.source]
                names = split_list(value) if spec.split and isinstance(value, str) else value
            if names:
                wanted[field] = [names] if isinstance(names, str) else list(names)
        return wanted

    def _fields(self, values, clear=False):
        """Row values as Airtable fields: lists for multi-selects. Empty values
        are left out, or with `clear` sent as empty so the cell is cleared."""
        out = {}
        for field, value in values.items():
            if field in self.list_fields:
                value = split_list(value) if isinstance(value, str) else list(value or [])
            if value not in (None, "", []):
                out[field] = value
            elif clear:
                out[field] = [] if field in self.list_fields else None
        return out

    def upsert(self, record):
        return self.upsert_many([record])[0]

    def upsert_many(self, records):
        """Add each record as a new row, or fill in its row's gaps, in as few
        calls as possible. Returns the rows afterwards."""
        new, updates, result = [], {}, []
        for record in records:
            record = dict(record)
            links = self._wanted_links(record)
            record = {k: (", ".join(v) if isinstance(v, list) and k not in self.list_fields else v)
                      for k, v in record.items() if k in self.columns}
            index, row = self.find(record)
            if row is None:
                pending = next((n for n in new if self._key_of(n[0]) == self._key_of(record)), None)
                if pending:   # the same row twice in one call
                    changes = merge(pending[0], record, self.list_fields)
                    pending[0].update(changes)
                    for field, names in links.items():
                        pending[1].setdefault(field, []).extend(names)
                    result.append(pending[0])
                    continue
                values = {c: (", ".join(record[c]) if isinstance(record.get(c), list) else (record.get(c) or ""))
                          for c in self.columns}
                new.append((values, links))
                result.append(values)
                continue
            changes = merge(row, record, self.list_fields)
            fields = self._fields(changes)
            for field, names in links.items():
                have = self.linked[index][field]
                added = [i for i in self._link_ids(field, names) if i not in have]
                if added:
                    fields[field] = have + added
                    self.linked[index][field] = have + added
            if fields:
                updates.setdefault(index, {}).update(fields)
                row.update(changes)
            result.append(row)
        if updates:
            self.client.update(self.name, [(self.ids[i], f) for i, f in updates.items()])
        if new:
            bodies = []
            for values, links in new:
                fields = self._fields(values)
                link_ids = {f: self._link_ids(f, names) for f, names in links.items()}
                fields.update({f: ids for f, ids in link_ids.items() if ids})
                bodies.append((values, fields, link_ids))
            made = self.client.create(self.name, [b[1] for b in bodies])
            for (values, _, link_ids), rec in zip(bodies, made):
                self.rows.append(values)
                self.ids.append(rec["id"])
                self.linked.append({f: link_ids.get(f, []) for f in self.links})
        return result

    def set(self, index, changes):
        """Write fields of an existing row (index into self.rows)."""
        fields = self._fields(changes, clear=True)
        if fields:
            self.client.update(self.name, [(self.ids[index], fields)])
        self.rows[index].update(changes)
