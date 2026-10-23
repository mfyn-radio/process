import base64
import datetime

from intake import library, purchase_email

RECEIPT = """Thanks for purchasing from Room40!

Steven Hess + Rutger Zuydervelt, Re:construct, digital album, $10.00 USD

   Releases October 30, 2026

Download your purchase here:

    https://bandcamp.com/download?from=receipt&payment_id=1288705861&sig=cda74423a15c1944b337d2ffec5d0afe
"""


def test_parse_receipt():
    p = purchase_email.parse("m1", RECEIPT)
    assert p.download_url == "https://bandcamp.com/download?from=receipt&payment_id=1288705861&sig=cda74423a15c1944b337d2ffec5d0afe"
    assert p.seller == "Room40"
    assert p.release_date == datetime.date(2026, 10, 30)
    assert not p.is_released(datetime.date(2026, 10, 29))
    assert p.is_released(datetime.date(2026, 10, 30))


def test_parse_html_receipt_unescapes_link():
    html = '<a href="https://bandcamp.com/download?from=receipt&amp;payment_id=1&amp;sig=ab">Download</a>'
    p = purchase_email.parse("m2", html)
    assert p.download_url == "https://bandcamp.com/download?from=receipt&payment_id=1&sig=ab"
    assert p.release_date is None


def test_parse_non_purchase():
    assert purchase_email.parse("m3", "New release from Toxic State Records") is None


def test_body_text_walks_parts():
    enc = lambda s: base64.urlsafe_b64encode(s.encode()).decode()
    payload = {"mimeType": "multipart/alternative", "parts": [
        {"mimeType": "text/plain", "body": {"data": enc("plain")}},
        {"mimeType": "text/html", "body": {"data": enc("<b>html</b>")}},
    ]}
    assert "plain" in purchase_email.body_text(payload)
    assert "<b>html</b>" in purchase_email.body_text(payload)


def test_folder_name():
    assert library.folder_name("Acidic Male", "Flesh Reversal") == "Acidic Male - Flesh Reversal"
    assert library.folder_name("AC/DC", 'What? "Live"') == "AC_DC - What_ _Live_"
    assert library.folder_name("Artist ", "Album.") == "Artist - Album"


def test_parse_seller_with_dash():
    text = ("Thanks for purchasing from Music for Your Neighbors - Archive!\n\n"
            "https://bandcamp.com/download?from=receipt&payment_id=2&sig=cd")
    assert purchase_email.parse("m4", text).seller == "Music for Your Neighbors - Archive"
