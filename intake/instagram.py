"""Reading MFYN's saved Instagram posts with Chrome.

Instagram has no API for saved posts, so a real Chrome window on the MFYN PC
opens the collection, signed in as MFYN. The sign-in lives in its own Chrome
profile (config.INSTAGRAM_PROFILE_DIR), made once with --setup-instagram.
Pages are opened slowly and only a few per run, so it looks like a person.
"""
import html
import random
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

POST_LINK = re.compile(r"/(?:p|reel)/([A-Za-z0-9_-]+)")
# og:description reads: '12 likes, 3 comments - venue on November 1, 2026: "caption"'
OG_DESCRIPTION = re.compile(r'^.*? - (?P<account>[A-Za-z0-9._]+) on (?P<date>[^:]+): [“"](?P<caption>.*)[”"]\.?$', re.S)


@dataclass
class Post:
    shortcode: str
    url: str
    account: str = ""
    posted: str = ""      # as Instagram words it, e.g. "November 1, 2026"
    caption: str = ""
    image_url: str = ""
    image: bytes = b""
    image_type: str = "image/jpeg"


def shortcodes(hrefs):
    """Post shortcodes from a page's links, in page order, without repeats."""
    seen = []
    for href in hrefs:
        m = POST_LINK.search(href or "")
        if m and m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def parse_description(text):
    """(account, posted, caption) from a post's og:description."""
    text = html.unescape(text or "").strip()
    m = OG_DESCRIPTION.match(text)
    if not m:
        return "", "", text
    return m.group("account"), m.group("date").strip(), m.group("caption").strip()


def pause(low=3.0, high=8.0):
    time.sleep(random.uniform(low, high))


class Browser:
    """One Chrome window on the Instagram profile, opened on first use."""

    def __init__(self, profile_dir):
        self.profile_dir = profile_dir
        self._driver = None

    def _chrome(self):
        if self._driver is None:
            Path(self.profile_dir).mkdir(parents=True, exist_ok=True)
            options = webdriver.ChromeOptions()
            options.add_argument(f"--user-data-dir={self.profile_dir}")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--log-level=3")
            options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
            # ChromeDriver's own log, next to the profile, for when Chrome won't start.
            log = Path(f"{self.profile_dir}.log")
            service = Service(log_output=str(log), service_args=["--verbose"])
            try:
                self._driver = webdriver.Chrome(options=options, service=service)
            except SessionNotCreatedException:
                raise SystemExit(
                    "Chrome wouldn't start on the Instagram profile. Usually another Chrome is still using it: "
                    "close any Chrome window the automation opened (or end it in Task Manager) and try again. "
                    f"Details are in {log}")
        return self._driver

    def close(self):
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    def _open(self, url):
        driver = self._chrome()
        driver.get(url)
        WebDriverWait(driver, 30).until(lambda d: d.execute_script("return document.readyState") == "complete")
        pause(2, 4)  # Instagram fills the page in after it "loads"
        return driver

    def sign_in(self):
        """Open Instagram so MFYN can sign in; the profile remembers it."""
        self._open("https://www.instagram.com/accounts/login/")
        input("Sign in to Instagram as MFYN in the Chrome window, then press Enter here... ")

    def signed_in(self, driver):
        return "/accounts/login" not in driver.current_url

    def collection(self, url, known, limit):
        """Shortcodes in the collection that aren't in `known`, newest first,
        at most `limit`. Scrolls until it reaches posts it already knows."""
        driver = self._open(url)
        if not self.signed_in(driver):
            raise SystemExit("Instagram isn't signed in. Run: python -m intake.events --setup-instagram")
        found = []
        for _ in range(10):
            hrefs = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "a[href]")]
            codes = shortcodes(hrefs)
            found = [c for c in codes if c not in known]
            if len(found) >= limit or len(found) < len(codes):
                break  # enough, or we've reached posts read before
            before = len(codes)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            pause()
            if len(shortcodes(a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, "a[href]"))) == before:
                break  # the end of the collection
        return found[:limit]

    def post(self, shortcode):
        """Read one post: its caption and its (first) image."""
        url = f"https://www.instagram.com/p/{shortcode}/"
        driver = self._open(url)

        def meta(prop):
            els = driver.find_elements(By.CSS_SELECTOR, f'meta[property="{prop}"]')
            return els[0].get_attribute("content") if els else ""

        account, posted, caption = parse_description(meta("og:description"))
        times = driver.find_elements(By.CSS_SELECTOR, "time[datetime]")
        post = Post(shortcode, url, account, posted, caption, meta("og:image"))
        if times:
            post.posted = times[0].get_attribute("datetime")[:10] or post.posted
        if post.image_url:
            request = urllib.request.Request(post.image_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=60) as resp:
                post.image = resp.read()
                post.image_type = resp.headers.get_content_type() or "image/jpeg"
        pause()
        return post
