# Step 2a: Make Episode Content

One run that makes an episode's baseline content: the archive cover and
YouTube playlist image, an ON AIR video post and caption for every track, and
an Album Story for every artist. A sub-automation of
[step 2, Create the show](02-create-show.md). (It replaces the separate
Make Reels and Make Album Story double-clicks.)

See also: [process overview](README.md) ·
[archive cover](archive-cover.md) · [Instagram copy](02b-instagram-copy.md) ·
[Album Stories](featured-album-story.md) ·
[the ON AIR video post sketch](../processing/MFYN_VideoPost_OnAir/README.md)

| | |
|---|---|
| **Trigger** | Step 2 triggers it once a show is ready. Until step 2 is automated, you double-click **MFYN – Make Episode Content** as step 2's last action |
| **Input** | The newest episode's `Tracks` folder in `MFYN_Show_Archive`, and the albums those tracks come from in `MFYN_Library` |
| **Output** | In the episode folder: `MFYN_archive_NN.png` and `MFYN_tracklist_NN.png`. In `MFYN_Posts\<episode>`: per track, `Artist - Title.mp4`, `.json` and `.txt`. In `MFYN_Stories\<episode>`: per artist, an Album Story `.mp4`, `.png` and `.json` |
| **Runs on** | The MFYN PC (Processing 4 and ffmpeg) |
| **Code** | [`intake/content.py`](../intake/content.py), which runs [`archive_cover.py`](../intake/archive_cover.py), [`reels.py`](../intake/reels.py), [`captions.py`](../intake/captions.py) and [`stories.py`](../intake/stories.py); started by [`scripts/make_content.cmd`](../scripts/make_content.cmd) |
| **Next** | You review it all at the manual stop, before the Publishing Process starts |

## What it does

1. **Find the episode:** the newest one in `MFYN_Show_Archive`, going by the
   air date in its folder name. It lists the tracks and asks
   `Make the content for these N track(s)? [Y/n]`.
2. **Archive cover and YouTube playlist image:** made in the episode folder,
   if they aren't there yet. Both open in the image viewer and you keep them
   or ask for a new colour; see [archive cover](archive-cover.md).
3. **Pick each artist's Album Story:** for every artist in the episode, the
   album of the track you played (one of them at random, if you played
   several of theirs), found in `MFYN_Library`, and a **random track from that
   album** to feature. Artists who already have a Story for this episode are
   skipped. An artist whose album isn't in the library gets no Story; the
   run says so and carries on.
4. **Confirm Instagram handles** in the [MFYN Artists sheet](01-acquire.md#the-mfyn-artists-sheet),
   once for everyone in the posts and the Stories.
   It goes through each artist, then each label of their releases, and asks
   only about those not settled yet. It shows the suggested handle and their
   links (website, SoundCloud…) to help check.
   - **Enter:** confirm the suggested handle. Status becomes `Confirmed`.
     When there's no suggestion (`Not found`), Enter does nothing: type a
     handle or `-`.
   - **Type a handle** (with or without `@`): replace it. Status becomes
     `Confirmed`.
   - **`-`:** they have no Instagram. Status becomes `No Instagram`, and
     they're credited by name instead.

   Once confirmed (or marked `No Instagram`), an artist or label isn't asked
   about again in later episodes.
5. **Render the video posts:** the ON AIR sketch runs on the tracks that don't have a video post yet.
   - Each video is **30 seconds** long, 1080×1920, from the loudest stretch of the track.
   - The player is in the exact centre of the frame, so it fits the full-screen Reel, the profile grid (middle 3:4) and a feed crop (middle 4:5).
   - It shows the title and artist from the tags, the embedded cover, the
     scope line, a progress bar and the ON AIR pulse.
   - A preview window shows each video as it renders, and closes when done.

   They're filed in `H:\My Drive\MFYN_Posts\<episode folder>\`, named
   `Artist - Title` (characters Windows doesn't allow become `_`; two tracks
   with the same name get ` (2)`, ` (3)`…):
   ```
   applied communications - donna deegan.mp4
   applied communications - donna deegan.json
   ```
6. **Captions:** [step 2b](02b-instagram-copy.md) writes a `.txt` caption
   next to every video post that doesn't have one yet.
7. **Render the Album Stories:** the Album sketch runs once per artist picked
   in step 3, with the featured track highlighted as playing; see
   [Album Stories](featured-album-story.md). They're filed in
   `H:\My Drive\MFYN_Stories\<episode folder>\`, named after the featured track.
8. **Summary:** what was made and what failed, for each part.

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

`python -m intake.reels` (same options) still makes only the cover, video
posts and captions, and `python -m intake.stories` makes a one-off Story for
any album; see [Album Stories](featured-album-story.md#running-it).

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
  to read the MFYN Artists sheet. Without it the video posts and Stories are still made, with
  no handles or album links.
- The Python packages in `requirements.txt` (the run reads tags with
  `mutagen`).

## Troubleshooting

The log is `%APPDATA%\mfyn-intake\content.log`. The run exits with an error
if the cover, a video post or a Story failed, or the library wasn't found.

| Message | What to do |
|---|---|
| `Show archive … not found` | Is Google Drive for desktop running and on `H:`? |
| `No episode folder … found` | Check the folder name: `5_11_2026- Episode Name` (day_month_year). |
| `… has no audio files in its Tracks folder` | Put the episode's FLACs in `Tracks`. |
| `Can't find Processing's command-line runner` | Set `MFYN_PROCESSING`, e.g. `setx MFYN_PROCESSING "C:\Program Files\Processing\Processing.exe"`, then open a new window. |
| `Processing exited with code …` / `No video post was made for …` | Scroll up for the sketch's own messages, e.g. `Couldn't run ffmpeg`. Test the sketch by opening it in Processing and pressing Run. |
| `… no album of theirs from this episode is in …` | That artist's album isn't in `MFYN_Library` under a folder named after the album (Bandcamp's `Artist - Album`), or the episode track's album or title tag differs from the library's. |
| `No Story was made for …` | Scroll up for the Album sketch's messages. |
| `Couldn't open the MFYN Artists sheet` | The video posts and Stories are still made, without handles. See [step 1 troubleshooting](01-acquire-troubleshooting.md). |

## Not part of this step (yet)

- **Scheduling posts:** part of the Publishing Process, which starts after
  your review.
