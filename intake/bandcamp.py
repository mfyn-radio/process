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
# The link Bandcamp shows once the file is ready (same selector as bcdl).
READY_LINK = (By.XPATH, "//a[@data-bind='attr: { href: downloadUrl }, visible: downloadReady() && !downloadError()']")
PARTIAL_SUFFIXES = (".crdownload", ".tmp")


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

        link = WebDriverWait(driver, prepare_timeout).until(EC.element_to_be_clickable(READY_LINK))
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
