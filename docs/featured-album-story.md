# Album Stories

A featured-album Instagram Story: the album of an artist in the episode, as a
media player with one of its tracks playing. [Make Episode Content](02a-make-episode-content.md)
makes one for every artist in the episode, when you ask it to. Posting it, with the Bandcamp link
sticker, is part of the Publishing Process.

See also: [process overview](README.md) ·
[the Album sketch](../processing/MFYN_Story_Album/README.md)

| | |
|---|---|
| **Trigger** | **MFYN – Make Episode Content**, when you answer yes to `Album Story videos?`. A one-off Story for any album can be made from Command Prompt |
| **Input** | For each artist in the episode, the album in `MFYN_Library` of the track you played |
| **Output** | `Artist - Title.mp4` (named after the featured track), a still `.png` and a `.json` of its details, in `MFYN_Stories\<episode folder>`, the same layout as `MFYN_Posts` |
| **Runs on** | The MFYN PC (Processing 4 and ffmpeg) |
| **Code** | [`intake/stories.py`](../intake/stories.py) and the sketch [`processing/MFYN_Story_Album`](../processing/MFYN_Story_Album), run by [`intake/content.py`](../intake/content.py) |
| **Next** | You review it, then post it with the album link as a sticker |

## What it does

1. **One Story per artist:** for each artist in the episode, the album of the
   track you played is found in `MFYN_Library`, by its album and title tags,
   in the folder Bandcamp named `Artist - Album`. If you played several of
   their tracks, one of those albums is picked at random. The album art is
   already in that folder. Because the album always comes from this
   episode's tracks, an album from an earlier show is never featured.
2. **A random track to feature:** any track of that album, not only the one
   you played. The sketch highlights it as the track playing.
3. **Instagram handles** for the artist and label are confirmed with the rest
   of the episode's, at the start of the run.
4. **Render:** the Album sketch runs on a copy of the album. The Story is
   **30 seconds** from the loudest stretch of the featured track: the media
   player (cover, album info, tracklist with the featured track highlighted,
   moving seek bar) over the rotating dot-matrix globe, which pulses with the
   track. A preview window shows it as it renders.
5. **File it** under the episode, in `H:\My Drive\MFYN_Stories\<episode folder>\`,
   named `Artist - Title` after the featured track, like the video posts:
   ```
   CADY - Umbrella.mp4
   CADY - Umbrella.png    <- the first frame, for a still Story
   CADY - Umbrella.json
   ```

An artist whose album isn't in the library gets no Story; the run says so and
carries on.

## The details file (for Publishing)

| Field | From |
|---|---|
| `artist`, `album`, `featured_track` (number, title, file), `year` | the tracks' tags |
| `label`, `release_date`, `album_link`, `tags` | the Releases tab |
| `artist_instagram` (+ `_status`), `label_instagram` (+ `_status`) | the Artists and Labels tabs |
| `episode` | `name` and `air_date` from the folder name, and the `folder` itself |
| `library_folder`, `clip_seconds`, `made` | the run itself |
| `episode_artist` | the artist as the episode's tracks name them, so a re-run knows they have their Story (not in one-off Stories) |

`album_link` is the Bandcamp page for the link sticker. The handles are as they
were when the Story was made; look them up again before posting.

## Running it

**The usual way:** it's part of **MFYN – Make Episode Content**; see
[running it](02a-make-episode-content.md#running-it).

**Re-running is safe.** An artist who already has a Story in the episode's
folder is skipped. To remake theirs, with a new random track, delete its
`.mp4` and `.json`, then run again.

**A one-off Story** for any album in the library, from Command Prompt in the
repo folder. You pick the album and the featured track:

```
python -m intake.stories                          # asks for the album and track
python -m intake.stories --album NAME --track N   # the album whose folder name contains NAME, track N of its list
python -m intake.stories --episode NAME           # file it under the episode whose folder name contains NAME
python -m intake.stories --skip-handles           # don't stop to confirm handles
```

Featuring a different track from the same album makes a second Story next to
the first. If that track already has a Story in the episode's folder, it says
so and stops.

## Requirements on the PC

The same as [Make Episode Content](02a-make-episode-content.md#requirements-on-the-pc): Processing 4
and ffmpeg, the repo at `%USERPROFILE%\mfyn-process`, Google Drive for desktop,
and the Google sign-in (without it the Story is still made, without handles or
the album link).

## Troubleshooting

The log is `%APPDATA%\mfyn-intake\content.log` (`stories.log` for a one-off Story).

| Message | What to do |
|---|---|
| `Library … not found` | Is Google Drive for desktop running and on `H:`? |
| `… no album of theirs from this episode is in …` | See [Make Episode Content troubleshooting](02a-make-episode-content.md#troubleshooting). |
| `No album in the library matches …` (one-off) | Type a different part of the name. Albums still downloading (`.partial - …`) aren't listed. |
| `Can't find Processing's command-line runner` | Set `MFYN_PROCESSING`; see [Make Episode Content troubleshooting](02a-make-episode-content.md#troubleshooting). |
| `Processing exited with code …` / `No Story was made for …` | Scroll up for the sketch's own messages. Test the sketch by opening it in Processing and pressing Run. |
