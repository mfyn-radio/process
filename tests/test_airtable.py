import io
import json
import urllib.error

import pytest

from fake_airtable import FakeAirtable
from intake import airtable, catalog, config, event_calendar


# --- the Web API client ---

class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def opener(pages):
    """An urlopen that answers with `pages` in turn; HTTPError codes are raised."""
    seen = []

    def urlopen(req, timeout):
        seen.append(req)
        answer = pages.pop(0)
        if isinstance(answer, int):
            raise urllib.error.HTTPError(req.full_url, answer, "error", {}, io.BytesIO(b'{"error":"x"}'))
        return FakeResponse(json.dumps(answer).encode())
    urlopen.seen = seen
    return urlopen


def test_list_records_follows_pages_and_sends_the_token():
    urlopen = opener([{"records": [{"id": "rec1"}], "offset": "o1"}, {"records": [{"id": "rec2"}]}])
    client = airtable.Client("secret", "appX", opener=urlopen, sleep=lambda s: None)
    assert [r["id"] for r in client.list_records("Playlist entries")] == ["rec1", "rec2"]
    assert client.calls == 2
    first, second = urlopen.seen
    assert first.full_url == "https://api.airtable.com/v0/appX/Playlist%20entries?pageSize=100"
    assert "offset=o1" in second.full_url
    assert first.get_header("Authorization") == "Bearer secret"


def test_writes_go_ten_records_a_call_with_typecast():
    urlopen = opener([{"records": [{"id": f"r{i}"} for i in range(10)]}, {"records": [{"id": "r10"}]}])
    client = airtable.Client("t", "appX", opener=urlopen, sleep=lambda s: None)
    made = client.create("Artists", [{"Artist": str(i)} for i in range(11)])
    assert len(made) == 11 and client.calls == 2
    body = json.loads(urlopen.seen[0].data)
    assert body["typecast"] is True and len(body["records"]) == 10


def test_budget_stops_the_run():
    client = airtable.Client("t", "appX", max_calls=1, opener=opener([{"records": []}]), sleep=lambda s: None)
    client.list_records("Artists")
    with pytest.raises(airtable.OverBudget):
        client.list_records("Artists")


def test_too_many_requests_waits_and_retries_and_errors_hide_the_token():
    waits = []
    client = airtable.Client("secret", "appX", opener=opener([429, {"records": []}]), sleep=waits.append)
    client.list_records("Artists")
    assert 30 in waits
    client = airtable.Client("secret", "appX", opener=opener([422]), sleep=lambda s: None)
    with pytest.raises(airtable.AirtableError) as e:
        client.create("Artists", [{"Artist": "A"}])
    assert "422" in str(e.value) and "secret" not in str(e.value)


def test_token_and_base_come_from_files(tmp_path, monkeypatch):
    monkeypatch.delenv("AIRTABLE_TOKEN", raising=False)
    monkeypatch.delenv("MFYN_AIRTABLE_BASE", raising=False)
    monkeypatch.setattr(config, "AIRTABLE_TOKEN_FILE", tmp_path / "airtable_token.txt")
    monkeypatch.setattr(config, "AIRTABLE_FILE", tmp_path / "airtable.json")
    with pytest.raises(airtable.AirtableError):
        airtable.read_token()
    (tmp_path / "airtable_token.txt").write_text("﻿patXYZ \n")   # Notepad's BOM and a newline
    (tmp_path / "airtable.json").write_text('{"base": "appABC"}')
    assert airtable.read_token() == "patXYZ" and airtable.saved_base() == "appABC"


# --- tables behind the sheet's interface ---

def test_catalog_reads_only_the_tables_it_needs():
    db = FakeAirtable()
    cat = catalog.Catalog(client=db)
    assert db.calls == 3          # Artists, Releases, Labels
    cat.events
    cat.events
    assert db.calls == 4


def test_rows_read_like_the_sheet_and_typed_values_stay():
    db = FakeAirtable({"Artists": [{"Artist": "Solo", "Instagram": "@mine", "Tags": ["punk", "Rotterdam"]}]})
    cat = catalog.Catalog(client=db)
    [row] = cat.artists.rows
    assert row["Tags"] == "punk, Rotterdam" and row["Location"] == ""
    cat.artists.upsert({"Artist": "SOLO", "Instagram": "@scraped", "Location": "Leeds", "Tags": ["noise", "punk"]})
    [stored] = db.fields("Artists")
    assert stored["Instagram"] == "@mine" and stored["Location"] == "Leeds"
    assert stored["Tags"] == ["punk", "Rotterdam", "noise"]


def test_set_can_clear_a_field():
    """Step 2a's "No Instagram" empties the handle."""
    db = FakeAirtable({"Artists": [{"Artist": "Solo", "Instagram": "@wrong", "Status": "Suggested"}]})
    cat = catalog.Catalog(client=db)
    cat.artists.set(0, {"Instagram": "", "Status": catalog.NO_INSTAGRAM})
    assert db.fields("Artists") == [{"Artist": "Solo", "Status": "No Instagram"}]
    assert cat.artists.rows[0]["Instagram"] == ""


def test_links_only_grow_so_hand_made_links_stay():
    db = FakeAirtable({"Artists": [{"Artist": "A"}, {"Artist": "B"}],
                       "Labels": [{"Label": "L", "Linked artists": ["recArt1"]}]})   # B, linked by hand
    cat = catalog.Catalog(client=db)
    cat.labels.upsert({"Label": "L", "Linked artists": ["a"]})
    assert db.fields("Labels")[0]["Linked artists"] == ["recArt1", "recArt0"]
    calls = db.calls
    cat.labels.upsert({"Label": "L", "Linked artists": ["A", "B"]})   # nothing new: no call
    assert db.calls == calls


def test_unknown_names_are_not_made_up_as_artists():
    db = FakeAirtable({"Artists": [{"Artist": "Daufødt"}]})
    cat = catalog.Catalog(client=db)
    body = {"id": "ev1", "summary": "Gig", "start": {"date": "2026-12-01"}, "end": {"date": "2026-12-01"},
            "extendedProperties": {"private": {"acts": "DAUFODT, Stranger", "tags": "punk"}}}
    cat.events.upsert(event_calendar.row(body, "2026-11-21"))
    [event] = db.fields("Events")
    assert event["Linked artists"] == [db.tables["Artists"][0]["id"]]
    assert event["Tags"] == ["punk"] and event["Acts"] == "DAUFODT, Stranger"
    assert len(db.fields("Artists")) == 1


def test_playlist_rows_link_their_episode_artist_and_release():
    db = FakeAirtable({"Artists": [{"Artist": "Squee"}], "Releases": [{"Album": "Glitter", "Artist": "Squee"}]})
    cat = catalog.Catalog(client=db)
    rows = [{"Episode": "5_11_2026- Skramz-ish", "#": str(i), "Artist": "Squee", "Track": f"t{i}",
             "Album": "Glitter"} for i in (1, 2)]
    for r in rows:
        cat.playlists.upsert(r)
    assert db.fields("Episodes") == [{"Episode": "5_11_2026- Skramz-ish"}]   # made once
    episode_id = db.tables["Episodes"][0]["id"]
    for stored in db.fields("Playlist entries"):
        assert stored["Linked episode"] == [episode_id]
        assert stored["Linked artist"] == [db.tables["Artists"][0]["id"]]
        assert stored["Linked release"] == [db.tables["Releases"][0]["id"]]
    index, _ = cat.playlists.find({"Episode": "5_11_2026- Skramz-ish", "#": "2"})
    cat.playlists.set(index, {"Playlist": "https://youtube.com/playlist?list=x"})
    assert db.fields("Playlist entries")[1]["Playlist"].endswith("list=x")


def test_upsert_many_batches_new_rows():
    db = FakeAirtable()
    cat = catalog.Catalog(client=db)
    calls = db.calls
    cat.artists.upsert_many([{"Artist": f"A{i}"} for i in range(12)] + [{"Artist": "a0", "Location": "X"}])
    assert db.calls - calls == 2 and len(db.fields("Artists")) == 12
    assert db.fields("Artists")[0] == {"Artist": "A0", "Location": "X"}
