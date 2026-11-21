"""An in-memory Airtable for tests: the same list, create and update as
intake.airtable.Client, counting calls the same way."""
import itertools


class FakeAirtable:
    base = "appTEST"

    def __init__(self, tables=None):
        self.tables = {name: [{"id": f"rec{name[:3]}{i}", "fields": dict(f)} for i, f in enumerate(rows)]
                       for name, rows in (tables or {}).items()}
        self.calls = 0
        self._ids = itertools.count(1000)

    def fields(self, table):
        return [r["fields"] for r in self.tables.get(table, [])]

    def by_id(self, table, rid):
        return next(r["fields"] for r in self.tables[table] if r["id"] == rid)

    def list_records(self, table):
        self.calls += 1
        return [{"id": r["id"], "fields": dict(r["fields"])} for r in self.tables.get(table, [])]

    def create(self, table, fields_list):
        made = []
        for i in range(0, len(fields_list), 10):
            self.calls += 1
            for fields in fields_list[i:i + 10]:
                rec = {"id": f"rec{next(self._ids)}", "fields": dict(fields)}
                self.tables.setdefault(table, []).append(rec)
                made.append({"id": rec["id"], "fields": dict(fields)})
        return made

    def update(self, table, changes):
        for i in range(0, len(changes), 10):
            self.calls += 1
            for rid, fields in changes[i:i + 10]:
                rec = next(r for r in self.tables[table] if r["id"] == rid)
                for k, v in fields.items():
                    if v in (None, []):
                        rec["fields"].pop(k, None)
                    else:
                        rec["fields"][k] = v
