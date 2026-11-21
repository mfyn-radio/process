# Step 2a: Make Episode Content

One shortcut for an episode's baseline content. It is an **orchestrator**: it
asks which sub-scripts you want for this episode and runs them in order. Each
sub-script, and each Processing sketch behind it, stays independent: you can
edit or run one on its own without touching the others. A sub-automation of
[step 2, Create the show](02-create-show.md).

See also: [process overview](README.md) ·
[archive cover](archive-cover.md) · [Instagram copy](02b-instagram-copy.md) ·
[Album Stories](featured-album-story.md) ·
[the ON AIR video post sketch](../processing/MFYN_VideoPost_OnAir/README.md)

| | |
|---|---|
| **Trigger** | You, double-clicking **MFYN – Make Episode Content** on the PC, as step 2's last action |
| **Input** | The newest episode in `MFYN_Show_Archive` (or the one you name) |
| **Output** | Whatever the sub-scripts you chose make (below) |
| **Runs on** | The MFYN PC (Processing 4 and ffmpeg) |
| **Code** | [`intake/content.py`](../intake/content.py), started by [`scripts/make_content.cmd`](../scripts/make_content.cmd) |
| **Next** | You review it all at the manual stop, before the Publishing Process starts |

## The sub-scripts

They run in this order. The first always runs; for the others you're asked
first (Enter means yes), since not every item fits every episode.

| Question | Sub-script | Sketch | Makes |
|---|---|---|---|
| *(always)* | [`archive_cover.py`](../intake/archive_cover.py): [archive cover](archive-cover.md) | `MFYN_Archive` | `MFYN_archive_NN.png` and the YouTube playlist cover `MFYN_tracklist_NN.png`, in the episode folder. One sketch, because the two depend on each other |
| `Do you want ON AIR posts?` | [`reels.py`](../intake/reels.py), then [`captions.py`](../intake/captions.py) ([2b](02b-instagram-copy.md)) | `MFYN_VideoPost_OnAir` | Per track: `Artist - Title.mp4`, `.json` and a `.txt` caption, in `MFYN_Posts\<episode>` |
| `Album Story videos?` | [`stories.py`](../intake/stories.py): [Album Stories](featured-album-story.md) | `MFYN_Story_Album` | Per artist: an Album Story `.mp4`, `.png` and `.json`, in `MFYN_Stories\<episode>` |
| `Do you want a YouTube playlist?` | [`playlist.py`](../intake/playlist.py): [YouTube playlist](youtube-playlist.md) | | A playlist proposal for your review in the Playlists tab of the MFYN Artists sheet, then the playlist on YouTube. Runs after the archive cover, whose playlist cover it uses |

A sub-script that isn't built yet isn't asked about. One that fails doesn't
stop the others; the summary at the end lists each one as ok or FAILED.

## What it does

1. **Find the episode:** the newest one in `MFYN_Show_Archive`, going by the
   air date in its folder name. It lists the tracks and asks
   `Make the content for this episode (N track(s))? [Y/n]`.
2. **Ask the questions** above.
3. **Run the sub-scripts** you chose, in order. Each confirms the Instagram
   handles it needs (see below), then makes its items. Anything already made
   is skipped.
4. **Summary:** each sub-script, ok or FAILED, with what it made. It also
   goes in the [run log](run-log.md).

### Instagram handles

The ON AIR posts and the Album Stories each check the
[MFYN Catalog](01-acquire.md#the-mfyn-catalog) for the artists
and labels they credit, and ask only about those not settled yet. It shows
the suggested handle and their links (website, SoundCloud…) to help check.

- **Enter:** confirm the suggested handle. Status becomes `Confirmed`. When
  there's no suggestion (`Not found`), Enter does nothing: type a handle or `-`.
- **Type a handle** (with or without `@`): replace it. Status becomes `Confirmed`.
- **`-`:** they have no Instagram. Status becomes `No Instagram`, and they're
  credited by name instead.

Once confirmed (or marked `No Instagram`), an artist or label isn't asked
about again, so an artist confirmed for the posts isn't asked about again
for their Story.

## ON AIR posts

The ON AIR sketch runs on the tracks that don't have a video post yet.

- Each video is **30 seconds** long, 1080×1920, from the loudest stretch of the track.
- The player is in the exact centre of the frame, so it fits the full-screen Reel, the profile grid (middle 3:4) and a feed crop (middle 4:5).
- It shows the title and artist from the tags, the embedded cover, the
  scope line, a progress bar and the ON AIR pulse.
- A preview window shows each video as it renders, and closes when done.

They're filed in `H:\My Drive\MFYN_Posts\<episode folder>\`, named
`Artist - Title` (characters Windows doesn't allow become `_`; two tracks
with the same name get ` (2)`, ` (3)`…), then [step 2b](02b-instagram-copy.md)
writes a `.txt` caption next to each one that doesn't have one yet:

```
applied communications - donna deegan.mp4
applied communications - donna deegan.json
applied communications - donna deegan.txt
```

## The video post details file (for captions and Publishing)

Instagram strips metadata from uploads, so each video post gets a `.json` file
beside it with what the post needs:

| Field | From |
|---|---|
| `artist`, `title`, `album`, `track_number`, `year` | the track's FLAC tags |
| `label`, `release_date`, `album_link`, `tags` | the Releases tab |
| `artist_instagram` (+ `_status`), `artist_website`, `artist_other_links` | the Artists tab |
| `label_instagram` (+ `_status`) | the Labels tab |
| `episode` | `name` and `air_date` from the folder name, and the `folder` itself |
| `source_track`, `clip_seconds`, `made` | the run itself |

The handles are as they were when the video post was made. Whatever uses them later should look
them up again in the sheet, in case one was corrected later.

## Running it

**The usual way:** double-click **MFYN – Make Episode Content** on the
desktop. The window stays open at the end so you can read the result. Press
any key to close it.

To set up the shortcut (one time):

1. In File Explorer, open `%USERPROFILE%\mfyn-process\scripts`.
2. Right-click `make_content.cmd` and choose **Show more options → Send to →
   Desktop (create shortcut)**.
3. Rename the shortcut to **MFYN – Make Episode Content**. (Delete the old
   **MFYN – Make Reels** and **MFYN – Make Album Story** shortcuts: their
   scripts are gone.)

**From Command Prompt**, in the repo folder:

```
python -m intake.content                  # the newest episode
python -m intake.content --episode NAME   # the episode whose folder name contains NAME
python -m intake.content --skip-handles   # don't stop to confirm handles
```

Each sub-script also runs on its own, with the same `--episode` option:

```
python -m intake.archive_cover --episode NAME        # the archive cover and playlist cover
python -m intake.reels --episode NAME                # the ON AIR posts and captions
python -m intake.stories --per-artist --episode NAME # the Album Stories
```

`python -m intake.stories` without `--per-artist` makes a one-off Story for
any album; see [Album Stories](featured-album-story.md#running-it).

### Adding a sub-script

Write it as a module in `intake/` with one entry point,
`for_episode(ep, ask=input, ...) -> (ok, summary)`, that does its whole job
for the episode and skips what already exists. It can also take
`skip_handles` and `rng`, which the orchestrator passes on to the
sub-scripts that ask for them. Then add one line to `STEPS` in
`intake/content.py`: the module, what it makes, and its question.

**Re-running is safe.** Anything already made is skipped: the cover, video
posts and captions that exist, and artists who already have a Story. To remake
a video post, delete its `.mp4` and `.json`; to remake an artist's Story,
delete its `.mp4` and `.json` in `MFYN_Stories`; then run again.

## Requirements on the PC

- **Processing 4**, plus **ffmpeg** (`winget install Gyan.FFmpeg`).
  - The automation finds Processing's command-line runner
    (`processing-java.exe`, or `Processing.exe cli` in newer versions) in the
    usual install folders.
  - If it can't, set the `MFYN_PROCESSING` environment variable to its full
    path.
- The repo's sketch is the master copy: `processing\MFYN_VideoPost_OnAir` in
  `%USERPROFILE%\mfyn-process`. Changes reach the PC with `git pull`.
  `H:\My Drive\MFYN_Processing` is a copy made by `scripts\sync_sketches.cmd`:
  make sketch changes in the repo ([working on the PC](working-on-the-pc.md)).
- Google Drive for desktop running, for `MFYN_Show_Archive`, `MFYN_Library`, `MFYN_Posts` and `MFYN_Stories`.
- The Google sign-in from [setting up step 1](01-acquire.md#setting-it-up-on-the-pc),
  to read the MFYN Catalog. Without it the video posts and Stories are still made, with
  no handles or album links.
- The Python packages in `requirements.txt` (the run reads tags with
  `mutagen`).

## Troubleshooting

The log is `%APPDATA%\mfyn-intake\content.log`. The run exits with an error
if any sub-script failed; the summary says which.

| Message | What to do |
|---|---|
| `Show archive … not found` | Is Google Drive for desktop running and on `H:`? |
| `No episode folder … found` | Check the folder name: `5_11_2026- Episode Name` (day_month_year). |
| `… has no audio files in its Tracks folder` | Put the episode's FLACs in `Tracks`. |
| `Can't find Processing's command-line runner` | Set `MFYN_PROCESSING`, e.g. `setx MFYN_PROCESSING "C:\Program Files\Processing\Processing.exe"`, then open a new window. |
| `Processing exited with code …` / `No video post was made for …` | Scroll up for the sketch's own messages, e.g. `Couldn't run ffmpeg`. Test the sketch by opening it in Processing and pressing Run. |
| `… no album of theirs from this episode is in …` | No folder in `MFYN_Library` whose name holds the album or the artist (Bandcamp's `Artist - Album`) has a track with the same album tag (for a single with no album tag: the same artist and title). Check the episode track's tags against the library's. |
| `No Story was made for …` | Scroll up for the Album sketch's messages. |
| `Couldn't open the MFYN Catalog base` | The video posts and Stories are still made, without handles. See [step 1 troubleshooting](01-acquire-troubleshooting.md). |

## Not part of this step (yet)

- **Scheduling posts:** part of the Publishing Process, which starts after
  your review.
