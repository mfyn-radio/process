"""Downloading purchases from Bandcamp's download pages with Chrome.

Bandcamp only serves these pages to real browsers, so this drives a normal
Chrome window: open the receipt's download link, pick the format, wait for
Bandcamp to prepare the file, and let Chrome download it.
"""
import json
import re
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from .release_info import RawPage

FORMAT_MENU = (By.ID, "format-type")
# The link Bandcamp shows once the file is ready (its data-bind mentions
# downloadUrl, as bcdl's selector expects).
READY_LINK = (By.XPATH, "//a[contains(@data-bind, 'downloadUrl')]")
PARTIAL_SUFFIXES = (".crdownload", ".tmp")
ALBUM_URL = re.compile(r"https://[^/]+/(album|track)/[^/?#]+")


def _ready_link(driver):
    """The first visible download link with a real address, once Bandcamp has one."""
    for link in driver.find_elements(*READY_LINK):
        href = link.get_attribute("href") or ""
        if link.is_displayed() and href.startswith("http"):
            return link
    return False


def describe_links(driver):
    """Summarize the page's visible links and buttons for the log, without
    their addresses, which are signed download URLs."""
    lines = [f"  page title: {driver.title!r}"]
    for el in driver.find_elements(By.XPATH, "//a | //button"):
        if not el.is_displayed():
            continue
        lines.append("  <{}> text={!r} class={!r} data-bind={!r} has-href={}".format(
            el.tag_name, el.text.strip()[:40], el.get_attribute("class"),
            (el.get_attribute("data-bind") or "")[:100], bool(el.get_attribute("href")),
        ))
    return "\n".join(lines[:40])


# Asks Bandcamp for the next page of a fan's wishlist, from inside the fan page,
# the way the page's own "view all" button does.
WISHLIST_ITEMS_SCRIPT = """
const [fanId, token, done] = arguments;
fetch('/api/fancollection/1/wishlist_items', {
  method: 'POST', credentials: 'include', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({fan_id: fanId, older_than_token: token, count: 100}),
}).then(r => r.ok ? r.json() : {error: 'HTTP ' + r.status}).then(done, e => done({error: String(e)}));
"""


class NotAvailable(Exception):
    """The download page has nothing to download yet (e.g. a pre-order)."""


class Browser:
    """One Chrome window, opened on first use and reused for every purchase."""

    def __init__(self, download_dir):
        self.download_dir = Path(download_dir)
        self._driver = None
        self.last_album_url = None  # album page linked from the last download page

    def _chrome(self):
        if self._driver is None:
            options = webdriver.ChromeOptions()
            # Keep Chrome's own console messages out of the log.
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            options.add_experimental_option("prefs", {
                "download.default_directory": str(self.download_dir),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
            })
            self._driver = webdriver.Chrome(options=options)
        return self._driver

    def close(self):
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    def read_page(self, url):
        """Read a Bandcamp album (or artist) page for the MFYN Artists sheet."""
        driver = self._chrome()
        driver.get(url)
        WebDriverWait(driver, 30).until(lambda d: d.execute_script("return document.readyState") == "complete")

        def texts(css):
            return [el.get_attribute("textContent").strip() for el in driver.find_elements(By.CSS_SELECTOR, css)]

        def first_text(css):
            found = [t for t in texts(css) if t]
            return found[0] if found else None

        seller_links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "#band-links a")]
        if not seller_links:
            # Older or unusual layouts: fall back to every external link on the page.
            seller_links = [a.get_attribute("href") for a in driver.find_elements(By.TAG_NAME, "a")]
        return RawPage(
            url=driver.current_url,
            ld_json=texts('script[type="application/ld+json"]'),
            seller_links=seller_links,
            seller_name=first_text("#band-name-location .title"),
            location=first_text("#band-name-location .location"),
            bio=first_text("#bio-text"),
            tags=[t for t in texts("a.tag") if t],
        )

    def wishlist(self, fan_page, max_pages=50):
        """Every item on a fan's public wishlist, newest first, as Bandcamp's own
        item dicts (item_title, band_name, item_url, added, ...)."""
        driver = self._chrome()
        driver.get(fan_page.rstrip("/") + "/wishlist")
        WebDriverWait(driver, 30).until(lambda d: d.execute_script("return document.readyState") == "complete")
        blob = driver.execute_script("const el = document.getElementById('pagedata'); return el && el.dataset.blob;")
        if not blob:
            raise RuntimeError(f"no fan data on {driver.current_url} (title: {driver.title!r})")
        blob = json.loads(blob)
        fan_id = (blob.get("fan_data") or {}).get("fan_id")
        data = blob.get("wishlist_data") or {}
        cached = (blob.get("item_cache") or {}).get("wishlist") or {}
        items = [cached[key] for key in data.get("sequence", []) if key in cached]
        token = data.get("last_token")
        more = bool(token) and len(items) < (data.get("item_count") or 0)
        driver.set_script_timeout(60)
        for _ in range(max_pages):
            if not (more and fan_id):
                break
            page = driver.execute_async_script(WISHLIST_ITEMS_SCRIPT, fan_id, token)
            if page.get("error"):
                raise RuntimeError(f"Bandcamp didn't send more wishlist items: {page['error']}")
            items += page.get("items") or []
            token, more = page.get("last_token"), page.get("more_available")
        return items

    def find_album(self, seller_page, title):
        """The album page for `title` on a seller's Bandcamp page, if listed."""
        if not seller_page or not title:
            return None
        driver = self._chrome()
        driver.get(seller_page.rstrip("/") + "/music")
        wanted = title.casefold()
        for a in driver.find_elements(By.CSS_SELECTOR, "a[href*='/album/'], a[href*='/track/']"):
            if wanted in (a.get_attribute("textContent") or "").casefold():
                return a.get_attribute("href").split("?")[0]
        return None

    def download(self, download_page_url, audio_format, prepare_timeout=600, download_timeout=1800):
        """Download one purchase and return the path of the downloaded file."""
        driver = self._chrome()
        driver.get(download_page_url)
        try:
            menu = WebDriverWait(driver, 30).until(EC.presence_of_element_located(FORMAT_MENU))
        except TimeoutException:
            raise NotAvailable(f"no format menu on the download page (title: {driver.title!r})")
        Select(menu).select_by_value(audio_format)
        # The download page links to the album's own page; keep it for the sheet.
        self.last_album_url = next((
            href.split("?")[0] for href in
            (a.get_attribute("href") or "" for a in driver.find_elements(By.TAG_NAME, "a"))
            if ALBUM_URL.match(href)
        ), None)

        try:
            link = WebDriverWait(driver, prepare_timeout).until(_ready_link)
        except TimeoutException:
            raise TimeoutError("the download link never appeared.\n" + describe_links(driver))
        before = set(self.download_dir.iterdir())
        # Click through JavaScript: Bandcamp's page footer can sit on top of the
        # link, and a normal click would land on the footer instead.
        driver.execute_script("arguments[0].click();", link)
        return self._wait_for_file(before, download_timeout)

    def _wait_for_file(self, before, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            new = [p for p in self.download_dir.iterdir() if p not in before]
            done = [p for p in new if not p.name.endswith(PARTIAL_SUFFIXES)]
            if done and len(done) == len(new):
                return done[0]
            time.sleep(2)
        raise TimeoutError("Chrome didn't finish the download in time")
