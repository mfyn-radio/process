import pytest

from fake_airtable import FakeAirtable
from intake import airtable_setup, catalog, config


class FakeMeta(FakeAirtable):
    """FakeAirtable plus the schema calls the setup makes."""

    def __init__(self, bases=()):
        super().__init__()
        self.bases = list(bases)      # [{"id", "name"}]
        self.schema = {}              # table name -> {"id", "name", "fields": [...]}
        self.base = None

    def request(self, method, path, params=None, body=None):
        self.calls += 1
        if path == "meta/bases" and method == "GET":
            return {"bases": self.bases}
        if path == "meta/bases":
            self.bases.append({"id": "appNEW", "name": body["name"]})
            for t in body["tables"]:
                self._add_table(t)
            return {"id": "appNEW"}
        if path.endswith("/tables") and method == "GET":
            return {"tables": [dict(t, fields=list(t["fields"])) for t in self.schema.values()]}
        if path.endswith("/tables"):
            return self._add_table(body)
        if path.endswith("/fields"):
            table = next(t for t in self.schema.values() if t["id"] == path.split("/")[-2])
            table["fields"].append(dict(body, id=f"fld{len(table['fields'])}"))
            return table["fields"][-1]
        raise AssertionError(path)

    def _add_table(self, body):
        t = {"id": f"tbl{len(self.schema)}", "name": body["name"], "fields": [dict(f) for f in body["fields"]]}
        self.schema[body["name"]] = t
        return t


@pytest.fixture(autouse=True)
def saved(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "AIRTABLE_FILE", tmp_path / "airtable.json")


def test_without_a_base_or_workspace_it_says_what_to_do():
    with pytest.raises(SystemExit) as e:
        airtable_setup.ensure_schema(FakeMeta())
    assert "MFYN Catalog" in str(e.value) and "wsp" in str(e.value)


def test_makes_the_base_with_every_table_and_link_and_saves_its_id():
    client = FakeMeta()
    assert airtable_setup.ensure_schema(client, workspace="wspX", tags=["punk"]) == "appNEW"
    assert set(client.schema) == {"Artists", "Labels", "Releases", "Events", "Episodes", "Playlist entries"}
    events = [f["name"] for f in client.schema["Events"]["fields"]]
    assert events[0] == "Title" and "Linked artists" in events
    releases = {f["name"]: f for f in client.schema["Releases"]["fields"]}
    assert releases["Linked label"]["options"]["linkedTableId"] == client.schema["Labels"]["id"]
    assert releases["Tags"]["options"]["choices"] == [{"name": "punk"}]
    assert '"appNEW"' in config.AIRTABLE_FILE.read_text()

    calls = client.calls   # a second run finds everything there and adds nothing
    airtable_setup.ensure_schema(client)
    assert client.calls - calls == 3


def test_fills_in_a_base_made_by_hand():
    client = FakeMeta(bases=[{"id": "appHAND", "name": "MFYN catalog"}])
    assert airtable_setup.ensure_schema(client) == "appHAND"
    assert "Linked artists" in [f["name"] for f in client.schema["Labels"]["fields"]]


class Sheet:
    def __init__(self, tabs):
        self.tabs = tabs

    def rows(self, tab):
        return self.tabs.get(tab, [])


def test_copy_links_releases_labels_and_events():
    sheet = Sheet({
        "Artists": [{"Artist": "Noverte", "Tags": "screamo, skramz", "Status": "Confirmed", "My notes": "great"},
                    {"Artist": "Shizune", "Tags": ""}, {"Artist": "", "Tags": ""}],
        "Labels": [{"Label": "PLEK.", "Status": "Not found"}],
        "Releases": [{"Album": "Noverte / Shizune SPLIT", "Artist": "Noverte / Shizune", "Label": "PLEK.",
                      "Tags": "screamo"},
                     {"Album": "Solo", "Artist": "Shizune", "Label": "Self-released"}],
        "Tags": [{"Tag": "screamo", "Artist": "Noverte / Shizune", "Album": "Noverte / Shizune SPLIT"}],
        "Events": [{"Event id": "e1", "Title": "Gig", "Acts": "Shizune, Others", "Tags": "skramz"}],
    })
    rows, extra, tags = airtable_setup.read_sheet(sheet)
    assert extra == {"artists": ["My notes"]} and tags == {"screamo", "skramz"}
    db = FakeAirtable()
    cat = catalog.Catalog(client=db)
    counts = airtable_setup.copy(cat, rows, extra)
    assert counts == {"Artists": 2, "Labels": 1, "Releases": 2, "Events": 1, "Episodes": 0, "Playlist entries": 0}

    ids = {f["Artist"]: r["id"] for r, f in zip(db.tables["Artists"], db.fields("Artists"))}
    noverte = db.fields("Artists")[0]
    assert noverte["Tags"] == ["screamo", "skramz"] and noverte["My notes"] == "great"
    split, solo = db.fields("Releases")
    assert split["Linked artists"] == [ids["Noverte"], ids["Shizune"]]
    assert split["Linked label"] == [db.tables["Labels"][0]["id"]]
    assert "Linked label" not in solo      # self-released: no Labels record to link
    assert db.fields("Labels")[0]["Linked artists"] == [ids["Noverte"], ids["Shizune"]]
    assert db.fields("Events")[0]["Linked artists"] == [ids["Shizune"]]

    calls = db.calls   # copying again changes nothing
    airtable_setup.copy(catalog.Catalog(client=db), rows, extra)
    assert db.calls - calls == 6   # the six tables are read; nothing is written
