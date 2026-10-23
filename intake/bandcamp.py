"""Downloading purchases from Bandcamp's download pages.

A receipt link opens a page whose `pagedata` blob lists the purchased items and a
per-format download URL. Bandcamp prepares the file on demand: the `statdownload`
endpoint reports when it's ready and returns the final URL.
"""
import html
import json
import random
import re
import time
from dataclasses import dataclass

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
PAGEDATA = re.compile(r'id="pagedata"[^>]*data-blob="([^"]*)"')
STAT_JSON = re.compile(r"\{.*\}", re.S)


@dataclass
class Item:
    artist: str
    title: str
    format_url: str | None  # None until the item is available (e.g. pre-order)


def items(download_page_url, audio_format):
    page = requests.get(download_page_url, headers=HEADERS, timeout=60)
    page.raise_for_status()
    match = PAGEDATA.search(page.text)
    if not match:
        raise RuntimeError(
            "Bandcamp download page has no pagedata; the page layout may have changed.\n"
            + describe(page)
        )
    blob = json.loads(html.unescape(match.group(1)))
    result = []
    for item in blob.get("digital_items") or []:
        downloads = item.get("downloads") or {}
        result.append(Item(
            artist=item.get("artist") or "Unknown Artist",
            title=item.get("title") or "Untitled",
            format_url=(downloads.get(audio_format) or {}).get("url"),
        ))
    return result


def _ready_url(format_url, attempts=20, wait=15):
    """Ask Bandcamp to prepare the file and wait until it hands back the final URL."""
    stat_url = format_url.replace("/download/", "/statdownload/") + "&.vrs=1"
    for _ in range(attempts):
        resp = requests.get(f"{stat_url}&.rand={random.randrange(10**9)}", headers=HEADERS, timeout=60)
        resp.raise_for_status()
        # The response is JSON, sometimes wrapped in a JavaScript callback.
        match = STAT_JSON.search(resp.text)
        stat = json.loads(match.group(0)) if match else {}
        if stat.get("download_url"):
            return stat["download_url"]
        if stat.get("result") not in (None, "ok", "err_retry"):
            raise RuntimeError(f"Bandcamp couldn't prepare the download: {stat.get('result')}")
        time.sleep(wait)
    raise RuntimeError("Bandcamp didn't finish preparing the download in time")


def download(format_url, dest_dir):
    """Download the prepared file into dest_dir and return its path."""
    url = _ready_url(format_url)
    with requests.get(url, headers=HEADERS, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        name = _filename(resp.headers.get("Content-Disposition", "")) or "download.zip"
        path = dest_dir / name
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return path


def _filename(content_disposition):
    match = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition)
    if match:
        return requests.utils.unquote(match.group(1))
    match = re.search(r'filename="?([^";]+)"?', content_disposition)
    return match.group(1) if match else None


def describe(page):
    """Summarize a page's structure for the log, without its links or text,
    which can include signed download URLs."""
    text = page.text
    final = requests.utils.urlparse(page.url)
    title = re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I)
    ids = sorted(set(re.findall(r'\bid="([^"]{1,60})"', text)))
    data_attrs = sorted(set(re.findall(r"\b(data-[a-z0-9-]{1,40})=", text)))
    keywords = [k for k in (
        "pagedata", "data-blob", "digital_items", "download_items", "statdownload",
        "captcha", "cloudflare", "challenge", "log in", "login", "sign in", "expired",
    ) if k in text.lower()]
    return "\n".join([
        f"  status: {page.status_code}, final URL: {final.netloc}{final.path}",
        f"  redirects: {[r.status_code for r in page.history]}",
        f"  content-type: {page.headers.get('Content-Type')}, length: {len(text)}",
        f"  title: {title.group(1).strip()[:120] if title else None}",
        f"  element ids: {ids[:60]}",
        f"  data attributes: {data_attrs[:60]}",
        f"  keywords present: {keywords}",
    ])
