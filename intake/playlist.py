"""YouTube playlist: an episode as a playlist of the bands' own videos.

A sub-script of Make Episode Content, which asks "Do you want a YouTube
playlist?". It also runs on its own:

    python -m intake.playlist                  # the newest episode in MFYN_Show_Archive
    python -m intake.playlist --episode NAME   # the episode whose folder name contains NAME

It works in two runs, so you can check the picks first:

1. **Propose.** The running order comes from the episode's Reaper project
   (intake.reaper). For every track it looks on YouTube for, in this order:
   1. a live video on the band's own channel,
   2. a live video by someone else (a fan, a venue), held for your yes,
   3. the official track on YouTube Music (the "Artist - Topic" upload).
   Claude Code on the PC (`claude -p`) judges the search results. The proposal
   goes in the Playlists tab of the MFYN Artists sheet, one row per track.
2. **Create.** Once every row's Use is yes or no, the next run asks
   "Create the YouTube playlist?" and makes it on MFYN's channel, with each
   band's Bandcamp link in the description and the episode's
   MFYN_tracklist_NN.png as its image. The playlist's link goes in the rows.

Re-running is safe: an episode is only searched once, and a playlist that's
already made is only topped up with what's missing. See docs/youtube-playlist.md.
"""
import argparse
import json
import logging
import re
import subprocess
import sys
import tempfile

from . import archive_cover, config, episode, flyer, google_auth, reaper, reels, runlog

log = logging.getLogger("playlist")

TIERS = {1: "1 band's own live", 2: "2 someone else's live", 3: "3 official track", 0: "none found"}
YES, NO, ASK = "yes", "no", "ask"
VIDEO_ID = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/|/live/)([A-Za-z0-9_-]{11})")

PROMPT = """You're helping Music for Your Neighbors (MFYN), an independent radio show \
from Rotterdam, turn an episode into a YouTube playlist that sends listeners to \
the bands. These tracks by {artist} were played, numbered by their place in the \
episode:

{tracks}

What MFYN knows about {artist}:
{about}

Candidate YouTube videos, from searches for the artist's live videos and for \
each track (JSON):
{candidates}

For every numbered track, pick one candidate video, by this order of preference:
1. A live video on the band's own YouTube channel.
2. A live video by someone else: a fan, a venue, a festival, a live session channel.
3. The official recording on YouTube Music: the upload by the "{artist} - Topic" \
channel (its description says "Provided to YouTube by"), from the same album if \
there's a choice.

Rules:
- Only pick videos from the candidates, by their id. Never make up an id.
- A full-set or multi-song live video counts for every track it contains. Match \
the song in its title, or in a setlist or timestamps in its description. Give \
the same id for each track it covers, and the start time (like 14:05) of the \
song if the description gives one.
- Live titles are messy ("Glitter // Stockholm 2025", "grindcore neck/birdwatching"). \
A live video only counts for a track if that song is in it.
- Check the channel is really the band's own before calling it tier 1: its name, \
or links to the band's Bandcamp, website or Instagram. A name that only looks \
alike is not enough; if it's likely but not certain, use tier 1 and set \
confident to false.
- Other artists often share the name. Use the album, the genre and the Topic \
channel to make sure it's this {artist}.
- If nothing fits a track, give tier 0 and no id.
- Set confident to false whenever you're unsure of the band, the song or the \
channel. Keep note short: what the video is (event, year, who filmed it), or why \
nothing fits."""

SCHEMA = {
    "type": "object",
    "properties": {"picks": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "number": {"type": "integer", "description": "The track's number in the episode"},
            "tier": {"type": "integer", "enum": [0, 1, 2, 3]},
            "video_id": {"type": ["string", "null"]},
            "start": {"type": ["string", "null"], "description": "Where the song starts in the video, like 14:05"},
            "confident": {"type": "boolean"},
            "note": {"type": "string"},
        },
        "required": ["number", "tier", "video_id", "start", "confident", "note"],
        "additionalProperties": False,
    }}},
    "required": ["picks"],
    "additionalProperties": False,
}


# --- YouTube ---------------------------------------------------------------

def youtube_service(creds):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def search(youtube, query):
    """Video ids for a search (100 quota units)."""
    reply = youtube.search().list(part="id", q=query, type="video",
                                  maxResults=config.PLAYLIST_SEARCH_RESULTS).execute()
    return [i["id"]["videoId"] for i in reply.get("items", []) if i.get("id", {}).get("videoId")]


def videos(youtube, ids):
    """Title, channel, description and length of videos (1 unit per 50)."""
    found = {}
    ids = list(dict.fromkeys(ids))
    for start in range(0, len(ids), 50):
        reply = youtube.videos().list(part="snippet,contentDetails", id=",".join(ids[start:start + 50])).execute()
        for v in reply.get("items", []):
            s = v.get("snippet", {})
            found[v["id"]] = {
                "id": v["id"], "title": s.get("title", ""), "channel": s.get("channelTitle", ""),
                "published": s.get("publishedAt", "")[:10], "length": v.get("contentDetails", {}).get("duration", ""),
                "description": (s.get("description") or "")[:1500],
            }
    return found


def candidates(youtube, artist, plays):
    """Every video the searches for this artist turn up: one search for their
    live videos, and one per track for the track itself."""
    ids = []
    for query in [f'"{artist}" live'] + [f"{artist} {p.title}" for p in plays]:
        try:
            ids += search(youtube, query)
        except Exception as e:
            log.warning("YouTube search for %r failed: %s", query, e)
    return videos(youtube, ids) if ids else {}


# --- Picking ---------------------------------------------------------------

def about(artist, plays, cat):
    """What the MFYN Artists sheet knows about the artist, to help tell their
    channel from someone else's."""
    lines = []
    if cat is not None:
        _, row = cat.artists.find({"Artist": artist})
        for field in ("Bandcamp page", "Website", "Instagram", "Other links", "Location", "Tags"):
            if row and row.get(field, "").strip():
                lines.append(f"{field}: {row[field].strip()}")
    albums = sorted({p.album for _, p in plays if p.album})
    if albums:
        lines.append("Albums played from: " + ", ".join(albums))
    return "\n".join(lines) or "(nothing)"


def ask_claude(artist, plays, found, info, run=subprocess.run, claude=None):
    """Claude Code's picks for one artist's tracks, as a list of dicts."""
    claude = claude or flyer.find_claude()
    tracks = "\n".join(f"{n}. {p.title}" + (f" (from {p.album})" if p.album else "") for n, p in plays)
    text = PROMPT.format(artist=artist, tracks=tracks, about=info,
                         candidates=json.dumps(list(found.values()), ensure_ascii=False, indent=1))
    cmd = [claude, "-p", "--output-format", "json", "--json-schema", json.dumps(SCHEMA),
           "--tools", "", "--no-session-persistence", "--strict-mcp-config"]
    if config.EVENTS_MODEL:
        cmd += ["--model", config.EVENTS_MODEL]
    with tempfile.TemporaryDirectory(prefix="mfyn-playlist-") as tmp:
        result = run(cmd, input=text, cwd=tmp, capture_output=True, text=True, encoding="utf-8", timeout=900)
    if result.returncode and not result.stdout:
        raise RuntimeError(f"Claude Code exited with {result.returncode}: {result.stderr[:300]}")
    try:
        reply = json.loads(result.stdout)
    except ValueError:
        raise RuntimeError(f"Claude Code didn't reply with JSON: {result.stdout[:300]!r}")
    output = reply.get("structured_output")
    if reply.get("is_error") or not isinstance(output, dict):
        raise RuntimeError(f"Claude Code failed: {reply.get('subtype')} {str(reply.get('result'))[:300]!r}")
    return output.get("picks") or []


def link(video_id, tier, start=None):
    if tier == 3:
        return f"https://music.youtube.com/watch?v={video_id}"
    url = f"https://www.youtube.com/watch?v={video_id}"
    seconds = to_seconds(start)
    return f"{url}&t={seconds}s" if seconds else url


def to_seconds(start):
    if not start or not re.fullmatch(r"\d{1,2}(:\d{2}){1,2}", start.strip()):
        return 0
    total = 0
    for part in start.strip().split(":"):
        total = total * 60 + int(part)
    return total


def video_id(url):
    match = VIDEO_ID.search(url or "")
    return match.group(1) if match else None


def default_use(tier, confident):
    """Tier 1 and 3 picks Claude is sure of go in; someone else's video, or
    anything it's unsure of, waits for your yes; nothing found stays out."""
    if tier == 0:
        return NO
    return YES if tier in (1, 3) and confident else ASK


def rows_for(ep, numbered, picks, found, cat=None):
    """The Playlists rows for one artist's tracks."""
    by_number = {p.get("number"): p for p in picks if isinstance(p, dict)}
    rows = []
    for n, play in numbered:
        pick = by_number.get(n) or {}
        tier = pick.get("tier") if pick.get("tier") in TIERS else 0
        vid = pick.get("video_id")
        note = (pick.get("note") or "").strip()
        if tier and vid not in found:
            note = f"Claude picked a video that wasn't in the search results ({vid}). {note}".strip()
            tier, vid = 0, None
        video = found.get(vid, {}) if tier else {}
        start = pick.get("start") if tier else None
        if start and to_seconds(start):
            note = f"Starts at {start}. {note}".strip()
        rows.append({
            "Episode": ep.folder.name, "#": str(n), "Artist": play.artist, "Track": play.title, "Album": play.album,
            "Tier": TIERS[tier], "Use": default_use(tier, bool(pick.get("confident"))),
            "Link": link(vid, tier, start) if tier else "", "Video": video.get("title", ""),
            "Uploader": video.get("channel", ""), "Note": note or ("No match found." if not tier else ""),
            "Bandcamp": bandcamp_link(cat, play.artist, play.album),
        })
    return rows


def bandcamp_link(cat, artist, album):
    """The artist's Bandcamp page, or the album's page, from the MFYN Artists sheet."""
    if cat is None:
        return ""
    _, row = cat.artists.find({"Artist": artist})
    if row and row.get("Bandcamp page", "").strip():
        return row["Bandcamp page"].strip()
    _, release = cat.releases.find({"Album": album, "Artist": artist})
    return (release or {}).get("Album link", "").strip()


def mark_repeats(rows):
    """A full-set video goes in the playlist once, at the first track it covers."""
    seen = {}
    for row in rows:
        vid = video_id(row["Link"])
        if not vid:
            continue
        if vid in seen:
            row["Note"] = f"Same video as #{seen[vid]}, so it's only in the playlist once. {row['Note']}".strip()
        else:
            seen[vid] = row["#"]


def propose(ep, plays, youtube, cat, judge=ask_claude, say=print):
    """Search, pick and write the proposal rows. Returns the rows."""
    numbered = list(enumerate(plays, 1))
    by_artist = {}
    for n, play in numbered:
        by_artist.setdefault(play.artist.casefold(), []).append((n, play))
    rows = []
    for group in by_artist.values():
        artist = group[0][1].artist
        say(f"  {artist}: searching YouTube for {len(group)} track(s)")
        found = candidates(youtube, artist, [p for _, p in group])
        picks = []
        if found:
            try:
                picks = judge(artist, group, found, about(artist, group, cat))
            except Exception as e:
                log.warning("Couldn't pick videos for %s: %s", artist, e)
        rows += rows_for(ep, group, picks, found, cat)
    rows.sort(key=lambda r: int(r["#"]))
    mark_repeats(rows)
    today = runlog.now()[:10]
    for row in rows:
        cat.playlists.upsert(dict(row, Added=today))
    return rows


# --- Creating --------------------------------------------------------------

def episode_rows(cat, ep):
    rows = [r for r in cat.playlists.rows if r.get("Episode", "").strip() == ep.folder.name]
    return sorted(rows, key=lambda r: int(r["#"]) if r.get("#", "").strip().isdigit() else 10 ** 6)


def wanted_videos(rows):
    """The video ids to put in the playlist, in running order, each once."""
    ids = []
    for row in rows:
        vid = video_id(row.get("Link"))
        if row.get("Use", "").strip().lower() == YES and vid and vid not in ids:
            ids.append(vid)
    return ids


def title(ep, number):
    date = archive_cover.cover_date(ep.air_date)
    name = f" – {ep.name}" if ep.name else ""
    show = f"Music for Your Neighbors No. {number}" if number else "Music for Your Neighbors"
    return f"{show}{name} ({date})"[:150]


def description(ep, rows):
    lines = [f"Music for Your Neighbors, the independent radio show from Rotterdam, aired "
             f"{archive_cover.cover_date(ep.air_date)}. The episode's music, live where we could find it.",
             "", "Support the bands on Bandcamp:"]
    seen = set()
    for row in rows:
        if row.get("Use", "").strip().lower() != YES or row["Artist"].casefold() in seen:
            continue
        seen.add(row["Artist"].casefold())
        bandcamp = row.get("Bandcamp", "").strip()
        lines.append(f"{row['Artist']}: {bandcamp}" if bandcamp else row["Artist"])
    text = "\n".join(lines).replace("<", "").replace(">", "")
    return text[:5000]


def existing_items(youtube, playlist_id):
    ids, token = [], None
    while True:
        reply = youtube.playlistItems().list(part="contentDetails", playlistId=playlist_id, maxResults=50,
                                             pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in reply.get("items", [])]
        token = reply.get("nextPageToken")
        if not token:
            return ids


def set_cover(youtube, playlist_id, image):
    """The playlist's image. Returns True if YouTube took it."""
    from googleapiclient.http import MediaFileUpload
    try:
        youtube.playlistImages().insert(
            part="snippet", body={"snippet": {"playlistId": playlist_id, "type": "hero"}},
            media_body=MediaFileUpload(str(image), mimetype="image/png")).execute()
        return True
    except Exception as e:
        log.warning("YouTube didn't take %s as the playlist image (%s). Add it by hand: open the playlist in "
                    "YouTube Studio, then Edit, then the image.", image.name, e)
        return False


def create(ep, rows, youtube, cat, number):
    """Make the playlist, or add what's missing to it. Returns (ok, url, summary)."""
    wanted = wanted_videos(rows)
    if not wanted:
        return False, "", "no rows with Use = yes and a YouTube link"
    url = next((r["Playlist"].strip() for r in rows if r.get("Playlist", "").strip()), "")
    playlist_id = playlist_id_from(url)
    new = not playlist_id
    if new:
        made = youtube.playlists().insert(part="snippet,status", body={
            "snippet": {"title": title(ep, number), "description": description(ep, rows)},
            "status": {"privacyStatus": config.PLAYLIST_PRIVACY},
        }).execute()
        playlist_id = made["id"]
        url = f"https://www.youtube.com/playlist?list={playlist_id}"
        # Saved straight away, so a later run tops this playlist up instead of making another.
        for row in rows:
            index, _ = cat.playlists.find(row)
            if index is not None:
                cat.playlists.set(index, {"Playlist": url})
        log.info("Made the playlist %s", url)
    there = set(existing_items(youtube, playlist_id)) if not new else set()
    added = 0
    for vid in wanted:
        if vid in there:
            continue
        try:
            youtube.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
            added += 1
        except Exception as e:
            log.error("Couldn't add %s to the playlist: %s. Run again later (tomorrow, if it's YouTube's daily "
                      "quota) to add the rest.", vid, e)
            return False, url, f"{url}: {added} video(s) added, then stopped: {e}"
    cover_note = ""
    if new and number is not None:
        image = ep.folder / archive_cover.tracklist_name(number)
        if not image.exists():
            cover_note = f", no image ({image.name} isn't made yet)"
            log.warning("%s isn't in the episode folder, so the playlist has no image yet.", image.name)
        elif not set_cover(youtube, playlist_id, image):
            cover_note = ", image not set: add it by hand"
    return True, url, f"{url}: {added} video(s) added, {len(wanted)} in all{cover_note}"


# --- The step --------------------------------------------------------------

def counts(rows):
    def tier(row):
        first = row.get("Tier", "").strip()[:1]
        return int(first) if first.isdigit() else 0
    tiers = {t: sum(1 for r in rows if tier(r) == t) for t in TIERS}
    asks = sum(1 for r in rows if r.get("Use", "").strip().lower() not in (YES, NO))
    return tiers, asks


def episode_number(ep):
    try:
        return archive_cover.number_for(ep, episode.all_in(config.SHOW_ARCHIVE_DIR))
    except Exception:
        return None


def open_services():
    creds = google_auth.credentials([google_auth.DRIVE, google_auth.YOUTUBE])
    from . import catalog
    return catalog.Catalog(creds), youtube_service(creds)


def for_episode(ep, ask=input, say=print, cat=None, youtube=None, judge=ask_claude):
    """The episode's YouTube playlist: propose it, or create it once reviewed.
    Returns (ok, summary)."""
    if cat is None or youtube is None:
        try:
            cat, youtube = open_services()
        except SystemExit as e:
            log.error("Can't reach Google: %s", e.code)
            return False, f"not signed in to Google with YouTube: {e.code}"
    sheet = f"the Playlists tab of {config.ARTISTS_SHEET}"
    if hasattr(cat.playlists, "_id"):
        sheet += f" (https://docs.google.com/spreadsheets/d/{cat.playlists._id})"

    rows = episode_rows(cat, ep)
    if not rows:
        plays = reaper.running_order(ep)
        if not plays:
            log.error("No Reaper project (.rpp named like %s_...) with tracks found in %s.",
                      f"{ep.air_date:%Y%m%d}", ep.folder)
            return False, "no running order: Reaper project not found"
        say(f"\nRunning order from the Reaper project: {len(plays)} track(s).")
        rows = propose(ep, plays, youtube, cat, judge, say)
        tiers, asks = counts(rows)
        log.info("Proposed the playlist in %s: %d band's own live, %d someone else's live, %d official, "
                 "%d not found. %d row(s) need your yes or no in the Use column.",
                 sheet, tiers[1], tiers[2], tiers[3], tiers[0], asks)
        return True, (f"proposal for review: {tiers[1]} band live, {tiers[2]} other live, {tiers[3]} official, "
                      f"{tiers[0]} not found, {asks} to decide")

    tiers, asks = counts(rows)
    if asks:
        log.info("The playlist proposal has %d row(s) still to decide. Set Use to yes or no in %s, then run "
                 "this again.", asks, sheet)
        return True, f"waiting for your review: {asks} row(s) to decide"
    done = next((r["Playlist"] for r in rows if r.get("Playlist", "").strip()), "")
    wanted = wanted_videos(rows)
    if done:
        there = set(existing_items(youtube, playlist_id_from(done)))
        if all(v in there for v in wanted):
            log.info("The playlist is already made: %s", done)
            return True, f"already made: {done}"
        question = f"Add the {sum(v not in there for v in wanted)} missing video(s) to the playlist? [y/N] "
    else:
        question = f"Create the YouTube playlist from the reviewed list ({len(wanted)} video(s))? [y/N] "
    if ask(question).strip().lower() not in ("y", "yes"):
        return True, "reviewed, not created yet"
    ok, url, summary = create(ep, rows, youtube, cat, episode_number(ep))
    (log.info if ok else log.error)("YouTube playlist: %s", summary)
    return ok, summary


def playlist_id_from(url):
    return url.split("list=", 1)[1].split("&")[0] if "list=" in url else ""


def main(argv=None, ask=input):
    return runlog.track("YouTube Playlist", lambda run: _main(argv, ask, run))


def _main(argv, ask, run):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--episode", help="the episode whose folder name contains this")
    args = parser.parse_args(argv)
    reels.setup_logging(config.PLAYLIST_LOG_FILE)
    if not config.SHOW_ARCHIVE_DIR.is_dir():
        log.error("Show archive %s not found. Is Google Drive for desktop running?", config.SHOW_ARCHIVE_DIR)
        return 1
    ep = episode.find(config.SHOW_ARCHIVE_DIR, args.episode)
    if ep is None:
        log.error("No episode folder (named like 5_11_2026- Episode Name) found in %s", config.SHOW_ARCHIVE_DIR)
        return 1
    log.info("Episode: %s", ep.folder.name)
    ok, summary = for_episode(ep, ask=ask)
    run.summary = summary
    run.add(ep.folder.name, runlog.OK if ok else runlog.FAILED, summary)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
