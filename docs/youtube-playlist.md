# YouTube playlist

Each episode as a playlist on MFYN's YouTube channel, made of the bands' own
videos where they exist. It's the **Listen** slide of the episode's Instagram
Highlight; the Bandcamp playlist is the **Support** slide. People who won't
stream on Bandcamp can listen here, and the description sends them to each
band's Bandcamp. (Re-uploading the whole episode was ruled out: Content ID
would claim parts of it, and the bands' own uploads pay the bands.)

A sub-script of [Make Episode Content](02a-make-episode-content.md), which asks
`Do you want a YouTube playlist?`. Issue
[#41](https://github.com/mfyn-radio/process/issues/41).

| | |
|---|---|
| **When** | After the show has aired, when the Reaper project has the final running order. Make Episode Content runs then too |
| **Input** | The episode's Reaper project in `MFYN_Show_Archive` (`20261105_….rpp`), the MFYN Catalog, and `MFYN_tracklist_NN.png` for the image |
| **Output** | A proposal in the **Playlist entries** table of the MFYN Catalog (Airtable), then a public playlist on mfyn@'s YouTube channel |
| **Runs on** | The MFYN PC (Claude Code judges the search results) |
| **Code** | [`intake/playlist.py`](../intake/playlist.py), with [`intake/reaper.py`](../intake/reaper.py) for the running order |
| **Log** | `%APPDATA%\mfyn-intake\playlist.log` on its own, `content.log` from Make Episode Content |

## How it works

It takes two runs, so nothing goes on YouTube before you've checked it.

### Run 1: the proposal

1. **Running order.** It reads the Reaper project whose name starts with the
   air date (`20261105_…`), so a stray `no.rpp` is ignored. Every item goes in
   order of its position; the `voice` track and muted items are left out, and a
   track split into several items counts once. The project is used, not the
   `Tracks` folder, because tracks played straight from `MFYN_Library` aren't in
   `Tracks`, and not the show notes, which are written before the show.

   The paths saved in the project often no longer work (the folder was
   renamed, an `.mp3` became a `.flac`), so each file is found again by name in
   `Tracks` or its album folder in `MFYN_Library`, and its tags are read.
   Otherwise the artist and title come from the file name.
2. **Search.** For each artist, one YouTube search for their live videos, and
   one per track for the track itself. That's about 30 searches for a 20-track
   episode. YouTube's free allowance is 10,000 units a day and a search costs
   100, so about one episode a day fits easily.
3. **Pick.** Claude Code on the PC (`claude -p`, on the Claude subscription)
   looks at the results for each artist, with what the MFYN Catalog knows
   about them (Bandcamp, website, Instagram), and picks per track:
   1. a live video on the **band's own channel**;
   2. a live video by **someone else** (a fan, a venue);
   3. the **official track** on YouTube Music (the `Artist - Topic` upload).

   A full-set video counts for every song in it, and goes in the playlist once,
   at the first track it covers. Claude only picks from the search results, and
   says when it isn't sure (is this really the band's channel? is it the same
   band, or another one with the same name?).
4. **The Playlist entries table.** One record per track, under the episode's folder name:

   | Column | |
   |---|---|
   | `#`, `Artist`, `Track`, `Album` | the running order |
   | `Tier` | `1 band's own live`, `2 someone else's live`, `3 official track` or `none found` |
   | `Use` | `yes`, `no` or `ask` (see below) |
   | `Link`, `Video`, `Uploader`, `Note` | the pick. The note says where a song starts in a full set, or that the same video is already in at an earlier track |
   | `Bandcamp` | the artist's Bandcamp page (or the album's), from the Artists and Releases tabs, for the description |
   | `Playlist` | filled in once the playlist is made |

   `Use` starts as `yes` for tier 1 and 3 picks Claude is sure of, `ask` for
   tier 2 and anything it's unsure of, and `no` when nothing was found.

### Your review

In the Playlist entries table (MFYN Catalog on Airtable), open the links and set every `Use` to `yes` or `no`. You
can also paste a better YouTube link into `Link` (and set `Use` to `yes`), for
a track where nothing was found, say.

### Run 2: create it

Run it again (Make Episode Content and answer yes to the playlist question,
or on its own, below). While any row is still `ask`, it says how many and
stops. Once they're all decided it asks:

```
Create the YouTube playlist from the reviewed list (15 video(s))? [y/N]
```

On a yes it makes a public playlist on mfyn@'s channel:

- **Title:** `Music for Your Neighbors No. 3 – <episode name> (5 November 2026)`.
  Rename it on YouTube if you like; that doesn't affect later runs.
- **Description:** the episode, then each band with their Bandcamp link.
- **Videos:** the `yes` rows, in running order, each video once.
- **Image:** `MFYN_tracklist_NN.png` from the episode folder. If YouTube
  doesn't accept it, the run says so: add it by hand in YouTube Studio.

The playlist's link goes in the `Playlist` column. That's the link for the
Instagram Story's link sticker.

**Re-running is safe.** An episode that has rows isn't searched again. A
playlist that's made isn't made again; if a run stopped partway (YouTube's
daily quota, say), the next run asks to add the missing videos. To start an
episode's proposal over, delete its records from the Playlist entries table.

## Running it

Usually from **MFYN – Make Episode Content**. On its own, from Command Prompt
in the repo folder:

```
python -m intake.playlist                  # the newest episode
python -m intake.playlist --episode NAME   # the episode whose folder name contains NAME
```

## Setting it up

One time, before the first run:

1. In the [Google Cloud console](https://console.cloud.google.com/apis/library/youtube.googleapis.com?project=mfyn-library-agent),
   turn on **YouTube Data API v3** for `mfyn-library-agent`.
2. mfyn@ needs a YouTube channel, and YouTube must be turned on for
   nothingflatdigital.com in the Google Admin console (**Apps → Additional
   Google services → YouTube**).
3. Sign in again on the PC, to add the YouTube permission:
   `python -m intake.acquire --setup %APPDATA%\mfyn-intake\client_secret.json`,
   choosing mfyn@. If mfyn@ has more than one channel, Google asks which one:
   choose MFYN's.

Until then the run stops with `not signed in to Google with YouTube`, and the
rest of Make Episode Content carries on.

## Troubleshooting

| Message | What to do |
|---|---|
| `not signed in to Google with YouTube` | Do [Setting it up](#setting-it-up), step 3 (and steps 1 and 2 if not done) |
| `No Reaper project … found` | The episode folder needs its `.rpp`, named starting with the air date like `20261105_…` (or be the only `.rpp` there) |
| `YouTube search for … failed` | Usually the daily quota (it resets at 09:00 Amsterdam time). Delete that episode's rows and run again tomorrow |
| `Couldn't pick videos for …` | Claude Code failed for that artist; their rows say `none found`. Fill in links by hand, or delete the episode's rows and run again |
| `Couldn't add … to the playlist` | Run again later; it adds the rest to the same playlist |
| `YouTube didn't take … as the playlist image` | Add `MFYN_tracklist_NN.png` by hand in YouTube Studio |

Still to check (in [#41](https://github.com/mfyn-radio/process/issues/41)):
whether someone else's live videos, which aren't tagged as music, play inside
the playlist in the YouTube Music app.
