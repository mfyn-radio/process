import json
from types import SimpleNamespace

from intake import bandcamp, wishlist
from intake.release_info import RawPage

ITEM = {"band_name": "Crowd Of Chairs", "item_title": "Night Bus", "added": "20 Nov 2026 10:11:12 GMT",
        "item_url": "https://crowdofchairs.bandcamp.com/album/night-bus?from=fanpub"}


def test_items_are_tidied_and_deduplicated():
    other = dict(ITEM, item_title="Day Tram", item_url="https://x.bandcamp.com/track/day-tram")
    assert wishlist.items([ITEM, other, ITEM, {"item_url": None}]) == [
        {"Artist": "Crowd Of Chairs", "Release": "Night Bus", "Wishlisted": "2026-11-20",
         "Bandcamp link": "https://crowdofchairs.bandcamp.com/album/night-bus"},
        {"Artist": "Crowd Of Chairs", "Release": "Day Tram", "Wishlisted": "2026-11-20",
         "Bandcamp link": "https://x.bandcamp.com/track/day-tram"},
    ]


def test_page_info_uses_the_album_pages_tags_and_location():
    ld = json.dumps({"@type": "MusicAlbum", "name": "Night Bus", "keywords": ["post-punk", "Rotterdam"],
                     "publisher": {"name": "Crowd Of Chairs", "foundingLocation": {"name": "Rotterdam, Netherlands"}}})
    raw = RawPage(url="https://crowdofchairs.bandcamp.com/album/night-bus", ld_json=[ld])
    assert wishlist.page_info(raw) == {"tags": ["post-punk", "Rotterdam"], "location": "Rotterdam, Netherlands"}


def test_row_splits_location_and_keeps_notes():
    item = wishlist.items([ITEM])[0]
    r = wishlist.row(item, {"tags": ["noise", "punk"], "location": "Ghent, Belgium"}, {"Notes": "play in Dec"})
    assert (r["Tags"], r["City"], r["Country"], r["Notes"]) == ("noise, punk", "Ghent", "Belgium", "play in Dec")
    assert wishlist.row(item, None)["Tags"] == ""


def test_read_pages_reads_only_new_pages_up_to_the_limit(monkeypatch):
    monkeypatch.setattr(wishlist, "pause", lambda *a: None)
    wanted = [{"Artist": "A", "Release": str(i), "Bandcamp link": f"https://a.bandcamp.com/album/{i}"} for i in range(5)]
    state = {"pages": {wanted[0]["Bandcamp link"]: {"tags": [], "location": ""}}}
    opened = []

    def read_page(url):
        opened.append(url)
        if url.endswith("/2"):
            raise TimeoutError("slow")
        return RawPage(url=url, tags=["ambient"], location="Antwerp, Belgium")

    read, failed = wishlist.read_pages(SimpleNamespace(read_page=read_page), wanted, state, limit=3)
    assert opened == [w["Bandcamp link"] for w in wanted[1:4]]
    assert (read, failed) == (2, 1)
    assert state["pages"][wanted[1]["Bandcamp link"]]["location"] == "Antwerp, Belgium"
    assert wanted[2]["Bandcamp link"] not in state["pages"]   # tried again next run


class FakeDriver:
    def __init__(self, blob, pages):
        self.blob, self.pages, self.tokens = blob, pages, []
        self.current_url, self.title = "https://bandcamp.com/fan/wishlist", "fan"

    def get(self, url):
        self.opened = url

    def execute_script(self, script):
        return "complete" if "readyState" in script else json.dumps(self.blob)

    def set_script_timeout(self, seconds):
        pass

    def execute_async_script(self, script, fan_id, token):
        self.tokens.append(token)
        return self.pages.pop(0)


def test_wishlist_reads_the_page_then_asks_for_the_rest():
    blob = {"fan_data": {"fan_id": 7},
            "wishlist_data": {"sequence": ["a1", "a2"], "last_token": "t2", "item_count": 3},
            "item_cache": {"wishlist": {"a1": {"item_url": "u1"}, "a2": {"item_url": "u2"}}}}
    driver = FakeDriver(blob, [{"items": [{"item_url": "u3"}], "more_available": False, "last_token": "t3"}])
    browser = bandcamp.Browser("downloads")
    browser._driver = driver
    assert [i["item_url"] for i in browser.wishlist("https://bandcamp.com/fan/")] == ["u1", "u2", "u3"]
    assert driver.opened == "https://bandcamp.com/fan/wishlist"
    assert driver.tokens == ["t2"]


def test_a_short_wishlist_needs_no_more_pages():
    blob = {"fan_data": {"fan_id": 7}, "wishlist_data": {"sequence": ["a1"], "last_token": "t1", "item_count": 1},
            "item_cache": {"wishlist": {"a1": {"item_url": "u1"}}}}
    driver = FakeDriver(blob, [])
    browser = bandcamp.Browser("downloads")
    browser._driver = driver
    assert len(browser.wishlist("https://bandcamp.com/fan")) == 1
    assert driver.tokens == []
