"""Reading Bandcamp purchase emails."""
import base64
import datetime
import html
import re
from dataclasses import dataclass

DOWNLOAD_LINK = re.compile(r"https://bandcamp\.com/download\?[^\s\"'<>]*payment_id=\d+[^\s\"'<>]*")
RELEASE_DATE = re.compile(r"Releases ([A-Z][a-z]+ \d{1,2}, \d{4})")
SELLER = re.compile(r"Thanks for purchasing from (.+?)!")


@dataclass
class Purchase:
    message_id: str
    seller: str | None
    download_url: str
    release_date: datetime.date | None  # set for pre-orders

    def is_released(self, today):
        return self.release_date is None or self.release_date <= today


def body_text(payload):
    """All text/plain and text/html parts of a Gmail message payload, joined."""
    texts = []
    data = payload.get("body", {}).get("data")
    if data and payload.get("mimeType", "").startswith("text/"):
        texts.append(base64.urlsafe_b64decode(data).decode("utf-8", "replace"))
    for part in payload.get("parts", []):
        texts.append(body_text(part))
    return "\n".join(texts)


def parse(message_id, text):
    """Pull the download link and any pre-order release date out of a receipt."""
    text = html.unescape(text)
    link = DOWNLOAD_LINK.search(text)
    if not link:
        return None
    seller = SELLER.search(text)
    release = RELEASE_DATE.search(text)
    release_date = None
    if release:
        release_date = datetime.datetime.strptime(release.group(1), "%B %d, %Y").date()
    return Purchase(message_id, seller.group(1).strip() if seller else None, link.group(0), release_date)
