"""A tab of a Google Sheet as a table: a header row, then one row per record.

Columns are found by their header, so they can be reordered or added to by
hand. The automation only ever fills empty cells and adds tags; it never
overwrites a value someone has typed.
"""


def column_letter(index):
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def split_list(value):
    return [v.strip() for v in (value or "").split(",") if v.strip()]


def merge(existing, record, list_fields=()):
    """The cells to change so `existing` (a row) takes in `record`.

    Empty cells are filled. For list_fields (comma-separated, like tags) new
    items are added to the end. Everything else is left as it is."""
    changes = {}
    for field, value in record.items():
        if value in (None, "", []):
            continue
        current = existing.get(field, "")
        if field in list_fields:
            items = split_list(current)
            known = {i.casefold() for i in items}
            added = [v for v in value if v.casefold() not in known]
            if added:
                changes[field] = ", ".join(items + added)
        elif not current.strip():
            changes[field] = value
    return changes


class Table:
    def __init__(self, sheets, spreadsheet_id, tab, columns, key, list_fields=()):
        self._sheets = sheets
        self._id = spreadsheet_id
        self.tab = tab
        self.columns = columns
        self.key = key if isinstance(key, tuple) else (key,)
        self.list_fields = list_fields
        self._ensure_tab()
        self._load()

    def _values(self):
        return self._sheets.spreadsheets().values()

    def _ensure_tab(self):
        meta = self._sheets.spreadsheets().get(spreadsheetId=self._id, fields="sheets.properties.title").execute()
        if self.tab not in [s["properties"]["title"] for s in meta["sheets"]]:
            self._sheets.spreadsheets().batchUpdate(spreadsheetId=self._id, body={"requests": [{"addSheet": {
                "properties": {"title": self.tab, "gridProperties": {"frozenRowCount": 1}},
            }}]}).execute()

    def _load(self):
        rows = self._values().get(spreadsheetId=self._id, range=f"'{self.tab}'").execute().get("values", [])
        self.header = rows[0] if rows else []
        missing = [c for c in self.columns if c not in self.header]
        if missing:
            start = column_letter(len(self.header))
            self._values().update(
                spreadsheetId=self._id, range=f"'{self.tab}'!{start}1",
                valueInputOption="RAW", body={"values": [missing]},
            ).execute()
            self.header = self.header + missing
        self.rows = [dict(zip(self.header, r + [""] * (len(self.header) - len(r)))) for r in rows[1:]]

    def _key_of(self, row):
        return tuple((row.get(k) or "").strip().casefold() for k in self.key)

    def find(self, record):
        wanted = self._key_of(record)
        for i, row in enumerate(self.rows):
            if self._key_of(row) == wanted:
                return i, row
        return None, None

    def upsert(self, record):
        """Add the record as a new row, or fill in the existing row's gaps.
        Returns the row's contents afterwards."""
        record = {k: (", ".join(v) if isinstance(v, list) and k not in self.list_fields else v)
                  for k, v in record.items()}
        index, row = self.find(record)
        if row is None:
            values = {k: (", ".join(v) if isinstance(v, list) else (v or "")) for k, v in record.items()}
            self._append_row([values.get(c, "") for c in self.header])
            self.rows.append({c: values.get(c, "") for c in self.header})
            return self.rows[-1]
        changes = merge(row, record, self.list_fields)
        if changes:
            self.set(index, changes)
        return row

    def set(self, index, changes):
        """Write cells of an existing row (index into self.rows)."""
        self._write_cells([{
            "range": f"'{self.tab}'!{column_letter(self.header.index(field))}{index + 2}",
            "values": [[value]],
        } for field, value in changes.items()])
        self.rows[index].update(changes)

    def _append_row(self, values):
        self._values().append(
            spreadsheetId=self._id, range=f"'{self.tab}'!A1", valueInputOption="RAW",
            insertDataOption="INSERT_ROWS", body={"values": [values]},
        ).execute()

    def _write_cells(self, data):
        self._values().batchUpdate(spreadsheetId=self._id, body={"valueInputOption": "RAW", "data": data}).execute()
