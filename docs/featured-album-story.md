# Make Album Story

A featured-album Instagram Story, made from an album in `MFYN_Library`. You
pick the album and the featured track; the rest is automatic. Posting it, with
the Bandcamp link sticker, is part of the Publishing Process.

See also: [process overview](README.md) ·
[the Album sketch](../processing/MFYN_Album/README.md)

| | |
|---|---|
| **Trigger** | You, double-clicking **MFYN – Make Album Story**, whenever you want to feature an album |
| **Input** | An album folder in `MFYN_Library`, and the featured track you pick |
| **Output** | `Artist - Album - Track.mp4`, a still `.png` and a `.json` of its details, in `MFYN_Stories\Artist - Album` |
| **Runs on** | The MFYN PC (Processing 4 and ffmpeg) |
| **Code** | [`intake/stories.py`](../intake/stories.py), the sketch [`processing/MFYN_Album`](../processing/MFYN_Album), started by [`scripts/make_story.cmd`](../scripts/make_story.cmd) |
| **Next** | You review it, then post it with the album link as a sticker |

## What it does

1. **Pick the album:** type part of its name. If more than one album in the
   library matches, it lists them and you pick one by number.
2. **Pick the featured track** by its number in the tracklist it shows.
3. **Confirm Instagram handles** for the artist and label, if they aren't
   settled yet, the same way as [Make Reels](02a-make-reels.md#what-it-does).
4. **Render:** the Album sketch runs on a copy of the album. The Story is
   **15 seconds** from the loudest stretch of the featured track: the media
   player (cover, album info, tracklist with the featured track highlighted,
   moving seek bar) over the rotating dot-matrix globe, which pulses with the
   track. A preview window shows it as it renders.
5. **File it** in `H:\My Drive\MFYN_Stories\<album folder>\`:
   ```
   CADY - Limitations of the Human Form - Umbrella.mp4
   CADY - Limitations of the Human Form - Umbrella.png    <- the first frame, for a still Story
   CADY - Limitations of the Human Form - Umbrella.json
   ```

## The details file (for Publishing)

| Field | From |
|---|---|
| `artist`, `album`, `featured_track` (number, title, file), `year` | the tracks' tags |
| `label`, `release_date`, `album_link`, `tags` | the Releases tab |
| `artist_instagram` (+ `_status`), `label_instagram` (+ `_status`) | the Artists and Labels tabs |
| `library_folder`, `clip_seconds`, `made` | the run itself |

`album_link` is the Bandcamp page for the link sticker. The handles are as they
were when the Story was made; look them up again before posting.

## Running it

**The usual way:** double-click **MFYN – Make Album Story** on the desktop.
Press Enter at any question to stop. The window stays open at the end so you
can read the result.

To set up the shortcut (one time):

1. In File Explorer, open `%USERPROFILE%\mfyn-process\scripts`.
2. Right-click `make_story.cmd` and choose **Show more options → Send to →
   Desktop (create shortcut)**.
3. Rename the shortcut to **MFYN – Make Album Story**.

**From Command Prompt**, in the repo folder:

```
python -m intake.stories                          # asks for the album and track
python -m intake.stories --album NAME --track N   # the album whose folder name contains NAME, track N of its list
python -m intake.stories --skip-handles           # don't stop to confirm handles
```

**Re-running is safe.** If that album and track already have a Story, it says
so and stops. To remake it, delete its `.mp4`, then run again. Featuring a
different track from the same album makes a second Story next to the first.

## Requirements on the PC

The same as [Make Reels](02a-make-reels.md#requirements-on-the-pc): Processing 4
and ffmpeg, the repo at `%USERPROFILE%\mfyn-process`, Google Drive for desktop,
and the Google sign-in (without it the Story is still made, without handles or
the album link).

## Troubleshooting

The log is `%APPDATA%\mfyn-intake\stories.log`.

| Message | What to do |
|---|---|
| `Library … not found` | Is Google Drive for desktop running and on `H:`? |
| `No album in the library matches …` | Type a different part of the name. Albums still downloading (`.partial - …`) aren't listed. |
| `Can't find Processing's command-line runner` | Set `MFYN_PROCESSING`; see [Make Reels troubleshooting](02a-make-reels.md#troubleshooting). |
| `Processing exited with code …` / `No Story was made for …` | Scroll up for the sketch's own messages. Test the sketch by opening it in Processing and pressing Run. |
