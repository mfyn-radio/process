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


def test_clean():
    assert library.clean("Acidic Male - Flesh Reversal") == "Acidic Male - Flesh Reversal"
    assert library.clean('AC/DC - What? "Live"') == "AC_DC - What_ _Live_"
    assert library.clean("Artist - Album.") == "Artist - Album"


def test_parse_seller_with_dash():
    text = ("Thanks for purchasing from Music for Your Neighbors - Archive!\n\n"
            "https://bandcamp.com/download?from=receipt&payment_id=2&sig=cd")
    assert purchase_email.parse("m4", text).seller == "Music for Your Neighbors - Archive"


def test_add_unzips_album_and_removes_zip(tmp_path):
    import zipfile
    zpath = tmp_path / "Artist - Album.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("Artist - Album - 01 Song.flac", b"flac")
        zf.writestr("cover.jpg", b"jpg")
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / ".partial - Artist - Album").mkdir()  # left over from an interrupted run
    files = library.add(lib, "Artist - Album", zpath)
    assert [f.name for f in files] == ["Artist - Album - 01 Song.flac", "cover.jpg"]
    assert not zpath.exists()
    assert sorted(p.name for p in lib.iterdir()) == ["Artist - Album"]


def test_add_single_track(tmp_path):
    track = tmp_path / "Artist - Track.flac"
    track.write_bytes(b"flac")
    lib = tmp_path / "lib"
    lib.mkdir()
    files = library.add(lib, "Artist - Track", track)
    assert [f.name for f in files] == ["Artist - Track.flac"]


def test_handle_from_links():
    from intake.release_info import handle_from_links
    assert handle_from_links([
        "https://appliedcommunications.bandcamp.com/music",
        "https://www.instagram.com/p/C123/",            # a post, not an account
        "https://www.instagram.com/applied.comms/?hl=en",
    ]) == "@applied.comms"
    assert handle_from_links(["https://twitter.com/x", None]) is None


def test_bandcamp_page_from_comment():
    from intake.tags import PAGE_URL
    assert PAGE_URL.search("Visit https://appliedcommunications.bandcamp.com").group(0) == \
        "https://appliedcommunications.bandcamp.com"


def test_split_links_drops_spotify_and_instagram():
    from intake.release_info import split_links
    website, others = split_links([
        "https://open.spotify.com/artist/1", "https://www.instagram.com/someone",
        "https://someone.net/", "https://soundcloud.com/someone", "https://www.youtube.com/@someone",
        "https://music.apple.com/x", "https://another-site.org",
    ])
    assert website == "https://someone.net/"
    assert others == ["https://soundcloud.com/someone", "https://www.youtube.com/@someone"]
