# Step 2: Create the show

The parent step. When a show is ready to make, this runs and triggers the
sub-automations, each its own step. Today the creating is manual, and you start
the one run that makes the content by hand.

| Sub-step | What it does | State |
|---|---|---|
| [Build Show](#build-show) | From the episode's Bandcamp playlist: the tracks copied from `MFYN_Library` into a desktop working folder, and a Reaper project with a track per artist, a Voice over track and a Music bed track | Built, not tried on the PC yet |
| [2a. Make Episode Content](02a-make-episode-content.md) | One run for the episode's baseline content: the pieces below | Built |
| [Archive cover](archive-cover.md) | `MFYN_archive_NN.png` and the YouTube playlist image `MFYN_tracklist_NN.png` in the episode folder | Built, runs at the start of 2a |
| Video posts | An ON AIR video post per track, in `MFYN_Posts` | Built, part of 2a |
| [2b. Instagram copy](02b-instagram-copy.md) | A caption for each video post | Built, part of 2a |
| [Album Stories](featured-album-story.md) | An Album Story per artist, in `MFYN_Stories` | Built, part of 2a |

When these have run, the production work is done and you reach the manual
stop: you review everything made for the post. Triggering the Publishing
Process (separate, not built yet) is up to you after that.

| | |
|---|---|
| **Input** | Albums in `MFYN_Library` |
| **Output** | The finished episode in `MFYN_Show_Archive`, with its tracks |
| **Done by** | You, for now. The parent automation isn't built yet. |
| **Triggers** | [Step 2a: Make Episode Content](02a-make-episode-content.md), for now by double-click |

## What happens

1. Select tracks for the show from `H:\My Drive\MFYN_Library`, as a playlist
   on MFYN's Bandcamp page.
2. Run [Build Show](#build-show) with the playlist's link, and make the show
   in the Reaper project it writes.
3. Archive it in `H:\My Drive\MFYN_Show_Archive`, in a folder named
   `D_M_YYYY- Episode Name`, for example `5_11_2026- Official Unofficial`.
4. Put the episode's tracks (the FLACs, copied from the library) in its
   `Tracks` folder. Step 2a also reads MP3, WAV, M4A, AIFF and OGG files.
5. **Last action:** double-click **MFYN – Make Episode Content** on the desktop.

## The episode folder

```
MFYN_Show_Archive\
  5_11_2026- Official Unofficial\
    Tracks\
      applied communications - applied communications bites the big one - 01 donna deegan.flac
      ...
```

- **Name:** the air date as **day_month_year**, then `- `, then the episode
  name. Step 2a reads both, and picks the episode with the latest air date.
- **Tracks:** copy them from the library as they are. Step 2a reads the
  artist, title and album from their FLAC tags, so don't strip the tags.

## Build Show

`intake.build_show` (issue #40, with #16). Double-click **MFYN – Build Show**
(`scripts\build_show.cmd`). It asks for:

- the episode's **Bandcamp playlist link**, like
  `https://bandcamp.com/music_for_your_neighbors/playlist/mfyn-december-2026`;
- the **air date**, as day_month_year (`3_12_2026`).

Then it:

1. reads the playlist in Chrome (Bandcamp blocks plain scripts), in its order;
2. finds each track in `MFYN_Library` by artist and title, ignoring case,
   accents and punctuation (the album breaks a tie);
3. if any are missing, runs [Acquire](01-acquire.md), which downloads new
   Bandcamp purchases as FLAC albums into the library, and looks again.
   **If some are still missing, it stops, lists them and copies nothing**:
   they haven't been bought yet. Buy them and run it again;
4. **copies** (never moves) the tracks, tags and all, from the library on
   Drive to the episode's folder on the PC:
   `C:\Users\admin\OneDrive\Desktop\MFYN_Workspace\2026_12_03\Tracks\01 - Artist - Title.flac`;
5. writes a Reaper project there, `20261203_MFYN.rpp`, with a **Voice over**
   track, a **Music bed** track, and one track per artist (named after the
   artist) holding their songs, placed back to back in playlist order. The
   file paths are relative, so the folder still opens in Reaper after it
   moves.

**The template.** If `MFYN_Workspace\MFYN_Template.rpp` exists, each project
starts from it: its settings, master FX chain and its **Voice over** and
**Music bed** tracks with their FX are kept; any other tracks in it are left
out. To make it: in Reaper, set up the master FX and those two tracks (named
exactly so), then **File → Save project as…** `MFYN_Template.rpp` in
`MFYN_Workspace`. Without it the project has no FX.

It never overwrites an episode folder: if `2026_12_03` is already in the
workspace, it stops. The YouTube playlist skips the Voice over and Music bed
tracks when it reads the running order.

| | |
|---|---|
| **Input** | A Bandcamp playlist link and the air date; albums in `MFYN_Library` (and new purchases, through Acquire) |
| **Output** | `MFYN_Workspace\YYYY_MM_DD\` with `Tracks\` and the `.rpp` (`MFYN_WORK_DIR` overrides the workspace) |
| **Log** | `%APPDATA%\mfyn-intake\build_show.log` (Acquire's run goes to its own log), and a row in the MFYN Run Log |

From Command Prompt, in the repo folder:

```
python -m intake.build_show --link URL --date 3_12_2026
python -m intake.build_show --no-acquire ...   # don't download missing tracks
```

To set up the shortcut (one time): right-click `scripts\build_show.cmd`,
choose **Show more options → Send to → Desktop (create shortcut)**, rename it
**MFYN – Build Show** and move it into `MFYN_Automation_Triggers` with the
others.
