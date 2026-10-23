"""Downloading purchases from Bandcamp's download pages with Chrome.

Bandcamp only serves these pages to real browsers, so this drives a normal
Chrome window: open the receipt's download link, pick the format, wait for
Bandcamp to prepare the file, and let Chrome download it.
"""
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

FORMAT_MENU = (By.ID, "format-type")
# The link Bandcamp shows once the file is ready. bcdl matches its exact
# data-bind; this only needs it to mention downloadUrl.
READY_LINK = (By.XPATH, "//a[contains(@data-bind, 'downloadUrl')]")
PARTIAL_SUFFIXES = (".crdownload", ".tmp")


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


class NotAvailable(Exception):
    """The download page has nothing to download yet (e.g. a pre-order)."""


class Browser:
    """One Chrome window, opened on first use and reused for every purchase."""

    def __init__(self, download_dir):
        self.download_dir = Path(download_dir)
        self._driver = None

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

    def download(self, download_page_url, audio_format, prepare_timeout=600, download_timeout=1800):
        """Download one purchase and return the path of the downloaded file."""
        driver = self._chrome()
        driver.get(download_page_url)
        try:
            menu = WebDriverWait(driver, 30).until(EC.presence_of_element_located(FORMAT_MENU))
        except TimeoutException:
            raise NotAvailable(f"no format menu on the download page (title: {driver.title!r})")
        Select(menu).select_by_value(audio_format)

        try:
            link = WebDriverWait(driver, prepare_timeout).until(_ready_link)
        except TimeoutException:
            raise TimeoutError("the download link never appeared.\n" + describe_links(driver))
        before = set(self.download_dir.iterdir())
        link.click()
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
