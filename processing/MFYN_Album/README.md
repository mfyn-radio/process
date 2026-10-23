# MFYN Album Story generator (Processing)

Turns an album folder into a 1080×1920 Instagram Story: the silver media
player (cover, album info, tracklist with the featured track highlighted,
pause button, moving seek bar) over the rotating dot-matrix globe, which
glows and pulses with the featured track. The video has the featured
track's audio. A still PNG of the first frame is saved next to it for posting
as a static story.

## One-time setup

Same as the Reel sketch:

- **macOS:** install Processing 4 from processing.org and ffmpeg with `brew install ffmpeg`.
- **Windows:** install Processing 4, run `winget install Gyan.FFmpeg`, then restart the PC.
  If Processing still can't find ffmpeg, set `FFMPEG` / `FFPROBE` at the top of
  `MFYN_Album.pde` to the full paths, e.g. `"C:\\ffmpeg\\bin\\ffmpeg.exe"`.

Keep this folder named `MFYN_Album` (Processing needs the folder and the main
`.pde` to share a name).

## Making a story

1. Make one folder per album inside `MFYN_Album/input/`, and put the album's
   tracks in it (FLAC, MP3, WAV, M4A, AIFF or OGG, tagged as Bandcamp delivers them).
2. Pick the featured track: add a text file called `featured.txt` to the
   album folder containing either the track number (`6`) or part of the title
   (`umbrella`). Without it, track 1 is featured.
3. Open `MFYN_Album.pde` and press **Run**.
4. `output/<album folder>_story.mp4` and `output/<album folder>_story.png` appear.
   Albums that already have a video in `output/` are skipped.

```
input/
  CADY - Limitations of the Human Form/
    01 An Audience of Loved Ones.flac
    ...
    10 Constellation Indifference.flac
    featured.txt        <- contains: 6
    cover.jpg           <- optional, see below
```

### What it reads

| On the card | Source |
|---|---|
| Album title, artist | `ALBUM` and `ALBUM_ARTIST` tags (falls back to `ARTIST`, then the folder name) |
| Released | `DATE` tag; a full date shows as 24.07.2026, a year on its own as 2026 |
| Tracklist | every track's `TITLE`, ordered by the `TRACK` number |
| Cover | an image in the album folder (`cover.jpg`, `folder.jpg`, `front.jpg` or any jpg/png), otherwise the artwork embedded in the tracks |
| Audio, seek bar, glow | the featured track, starting at its loudest stretch |

Albums with more than 14 tracks show a 14-track window around the featured track,
so the player stays inside the Story safe zone.

## Settings

Top of `MFYN_Album.pde`:

| Setting | Default | |
|---|---|---|
| `CLIP_SECONDS` | 15 | story length, max 60 |
| `START_OVERRIDE` | -1 | -1 = auto, or a number of seconds into the featured track |
| `PREVIEW` | true | draw frames in the window while rendering |
| `SAVE_STILL` | true | also save the PNG |

Top of `Globe.pde`: globe position and size, grid spacing, rotation speed,
line brightness, unlit-dot brightness, how strongly the player blocks the
globe's light (`OCC_STRENGTH`) and how much light spills onto its edges
(`WRAP_STRENGTH`).

Top of `Skin.pde`: the player's colours and layout.

## Running it without opening the editor

Like the Reel sketch:

```
processing-java --sketch="/path/to/MFYN_Album" --run
```

(on Windows: `"C:\Program Files\Processing\processing-java.exe" --sketch="C:\path\to\MFYN_Album" --run`)

## Files

- `MFYN_Album.pde`: settings, the album queue, the preview window
- `Album.pde`: reads tags, cover and audio; picks the featured track and start; renders frames
- `Skin.pde`: the media player (frames, buttons, album info, tracklist, seek bar)
- `Globe.pde`: the dot-matrix globe, its glow and the music pulse
- `Blur.pde`: blurs and the audio low-pass filter
- `Encoder.pde`: streams frames into ffmpeg and adds the audio
- `data/`: Michroma and Silkscreen (Google Fonts, SIL Open Font License)
