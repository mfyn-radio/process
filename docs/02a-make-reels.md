# Step 2a: Make Reels

Turning an episode's tracks into 30-second Instagram Reels. A sub-automation of
[step 2, Create the show](02-create-show.md).

See also: [process overview](README.md) ·
[the Reel sketch](../processing/MFYN_Reel/README.md)

| | |
|---|---|
| **Trigger** | Step 2 triggers it once a show is ready. Until step 2 is automated, you double-click **MFYN – Make Reels** as step 2's last action |
| **Input** | The newest episode's `Tracks` folder in `MFYN_Show_Archive` |
| **Output** | One `Artist - Title.mp4` Reel per track, plus a `.json` of its details, in `MFYN_Reels\<episode>` |
| **Runs on** | The MFYN PC (Processing 4 and ffmpeg) |
| **Code** | [`intake/reels.py`](../intake/reels.py), the sketch [`processing/MFYN_Reel`](../processing/MFYN_Reel), started by [`scripts/make_reels.cmd`](../scripts/make_reels.cmd) |
| **Next** | Siblings under step 2: 2b, Instagram copy, then 2c, schedule the posts (neither built yet) |

## What it does

1. **Find the episode:** the newest one in `MFYN_Show_Archive`, going by the
   air date in its folder name. It lists the tracks and asks
   `Make Reels for these N track(s)? [Y/n]`.
2. **Confirm Instagram handles** in the [MFYN Artists sheet](01-acquire.md#the-mfyn-artists-sheet).
   It goes through each artist in the episode, then each label of their
   releases, and asks only about those not settled yet. It shows the
   suggested handle and their links (website, SoundCloud…) to help check.
   - **Enter:** confirm the suggested handle. Status becomes `Confirmed`.
     When there's no suggestion (`Not found`), Enter does nothing: type a
     handle or `-`.
   - **Type a handle** (with or without `@`): replace it. Status becomes
     `Confirmed`.
   - **`-`:** they have no Instagram. Status becomes `No Instagram`, and
     they're credited by name instead.

   Once confirmed (or marked `No Instagram`), an artist or label isn't asked
   about again in later episodes.
3. **Render:** your Reel sketch runs on the tracks that don't have a Reel yet.
   - Each Reel is **30 seconds** long, from the loudest stretch of the track.
   - It shows the title and artist from the tags, the embedded cover, the
     scope line, a progress bar and the ON AIR pulse.
   - A preview window shows each Reel as it renders, and closes when done.
4. **File the Reels** in `H:\My Drive\MFYN_Reels\<episode folder>\`, named
   `Artist - Title` (characters Windows doesn't allow become `_`; two tracks
   with the same name get ` (2)`, ` (3)`…):
   ```
   applied communications - donna deegan.mp4
   applied communications - donna deegan.json
   ```

## The details file (for step 2c)

Instagram strips metadata from uploads, so each Reel gets a `.json` file
beside it with what the post needs:

| Field | From |
|---|---|
| `artist`, `title`, `album`, `track_number`, `year` | the track's FLAC tags |
| `label`, `release_date`, `album_link`, `tags` | the Releases tab |
| `artist_instagram` (+ `_status`), `artist_website`, `artist_other_links` | the Artists tab |
| `label_instagram` (+ `_status`) | the Labels tab |
| `episode` | `name` and `air_date` from the folder name, and the `folder` itself |
| `source_track`, `clip_seconds`, `made` | the run itself |

The handles are as they were when the Reel was made. Step 2c should look them
up again in the sheet, in case one was corrected later.

## Running it

**The usual way:** double-click **MFYN – Make Reels** on the desktop. The
window stays open at the end so you can read the result. Press any key to
close it.

To set up the shortcut (one time):

1. In File Explorer, open `%USERPROFILE%\mfyn-process\scripts`.
2. Right-click `make_reels.cmd` and choose **Show more options → Send to →
   Desktop (create shortcut)**.
3. Rename the shortcut to **MFYN – Make Reels**.

**From Command Prompt**, in the repo folder:

```
python -m intake.reels                  # the newest episode
python -m intake.reels --episode NAME   # the episode whose folder name contains NAME
python -m intake.reels --skip-handles   # don't stop to confirm handles
```

**Re-running is safe.** Tracks that already have a Reel in `MFYN_Reels` are
skipped. To remake one, delete its `.mp4` and `.json`, then run again.

## Requirements on the PC

- **Processing 4**, plus **ffmpeg** (`winget install Gyan.FFmpeg`).
  - The automation finds Processing's command-line runner
    (`processing-java.exe`, or `Processing.exe cli` in newer versions) in the
    usual install folders.
  - If it can't, set the `MFYN_PROCESSING` environment variable to its full
    path.
- The repo's sketch is the master copy: `processing\MFYN_Reel` in
  `%USERPROFILE%\mfyn-process`. Changes reach the PC with `git pull`.
  `H:\My Drive\MFYN_Processing` is no longer used.
- Google Drive for desktop running, for `MFYN_Show_Archive` and `MFYN_Reels`.
- The Google sign-in from [setting up step 1](01-acquire.md#setting-it-up-on-the-pc),
  to read the MFYN Artists sheet. Without it the Reels are still made, with
  no handles.
- The Python packages in `requirements.txt` (Make Reels reads tags with
  `mutagen`).

## Troubleshooting

The log is `%APPDATA%\mfyn-intake\reels.log`. The run exits with an error
if any Reel failed.

| Message | What to do |
|---|---|
| `Show archive … not found` | Is Google Drive for desktop running and on `H:`? |
| `No episode folder … found` | Check the folder name: `5_11_2026- Episode Name` (day_month_year). |
| `… has no audio files in its Tracks folder` | Put the episode's FLACs in `Tracks`. |
| `Can't find Processing's command-line runner` | Set `MFYN_PROCESSING`, e.g. `setx MFYN_PROCESSING "C:\Program Files\Processing\Processing.exe"`, then open a new window. |
| `Processing exited with code …` / `No Reel was made for …` | Scroll up for the sketch's own messages, e.g. `Couldn't run ffmpeg`. Test the sketch by opening it in Processing and pressing Run. |
| `Couldn't open the MFYN Artists sheet` | The Reels are still made, without handles. See [step 1 troubleshooting](01-acquire-troubleshooting.md). |

## Not part of this step (yet)

- **The Album Story** (`processing\MFYN_Album`): a media-player Story for a
  featured album. It's in the repo but not automated.
- **Instagram copy and scheduling posts:** steps 2b and 2c, separate
  sub-automations of step 2 that read `MFYN_Reels`.
