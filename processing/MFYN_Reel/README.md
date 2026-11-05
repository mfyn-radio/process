# MFYN Reel generator (Processing)

Turns tagged audio files into 1080×1920 Instagram Reels in the MFYN white
dot-matrix player style: white dots on black, five grey levels, with the song
title the only element at full white. The reels include the track's audio, a
live scope line, a progress bar and the ON AIR pulse.

## One-time setup (Windows)

Runs on the MFYN PC. The [Make Reels doc](../../docs/02a-make-reels.md)
covers how the automation uses it.

1. Install **Processing 4** from processing.org.
2. Install **ffmpeg**: in a terminal run `winget install Gyan.FFmpeg`, then restart
   the PC (or log out and in) so Processing can find it. If it still can't, set
   `FFMPEG` / `FFPROBE` at the top of `MFYN_Reel.pde` to the full paths, e.g.
   `"C:\\ffmpeg\\bin\\ffmpeg.exe"` (note the double backslashes).
3. Keep this folder named `MFYN_Reel` (Processing needs the folder and the
   main `.pde` to share a name).

## Making reels

1. Put audio files in `MFYN_Reel/input/` (FLAC, MP3, WAV, M4A, AIFF, OGG).
2. Open `MFYN_Reel.pde` and press **Run**.
3. Finished videos appear in `MFYN_Reel/output/` as `<file name>_reel.mp4`.
   The window shows a preview while it renders, and closes itself when done.

Tracks that already have a video in `output/` are skipped, so you can keep
adding files to `input/` and re-run.

### What it reads from each file

| Field | Source |
|---|---|
| Title, artist | the file's tags (`TITLE`, `ARTIST`, falls back to `ALBUMARTIST`). The title takes up to two lines; the artist, 20% smaller, wraps onto as many lines as fit above the progress bar. Longer text is cut with "..." |
| Length | the file itself |
| Cover | embedded artwork, otherwise `<track name>.jpg/.png`, `cover.jpg/.png` or `folder.jpg/.png` next to the file |
| Start point | the loudest stretch of the track, skipping the first and last 30 s |

The pixel fonts only have the basic Latin letters. The sketch adds Ø, writes Æ,
Œ and ß as AE, OE and SS, and drops accents (É → E, Ù → U). Anything else,
such as non-Latin text, still comes out as `?`.

## Settings (top of `MFYN_Reel.pde`)

| Setting | Default | |
|---|---|---|
| `CLIP_SECONDS` | 30 | reel length, max 60 |
| `START_OVERRIDE` | -1 | -1 = auto, or a number of seconds into the track |
| `PREVIEW` | true | draw frames in the window while rendering |

Look settings live in their own tabs:

- `Cover`: `COVER_DIM` (cover brightness), `COVER_BLOOM` (glow on the cover's highlights)
- `Scope`: `SCOPE_GAIN` (wave height), `SCOPE_LOWPASS_HZ` (smoothness)
- `Player`: the five grey levels, layout positions (the player is centred in
  Instagram's safe area, between y 120 and 1575), `TITLE_P` (title size, 6 =
  design size), `ARTIST_P` (artist size, 4.8 = 20% smaller)
- `Glow`: `GLOW_TIGHT`, `GLOW_WIDE`, `GLOW_GAIN` (the halo around every lit dot)

## Running it without opening the editor

Normally the Make Reels automation does this for you. To do it by hand, use
`processing-java.exe` from the Processing install folder (newer versions of
Processing use `Processing.exe cli` instead). This renders everything in
`input/`:

```
"C:\Program Files\Processing\processing-java.exe" --sketch="C:\path\to\MFYN_Reel" --run
```

A window opens briefly while it renders, so the PC needs to be signed in.

## Command-line options

The Make Reels automation (`intake/reels.py`, step 2a of the intake and production process)
runs the sketch with options that override the settings:

```
"C:\Program Files\Processing\processing-java.exe" --sketch="C:\path\to\MFYN_Reel" --run input="<folder>" output="<folder>" seconds=30
```

`input` and `output` can be absolute paths; relative ones are inside the
sketch folder, as before.

## Files

- `MFYN_Reel.pde`: settings, the job queue, the preview window
- `Job.pde`: reads tags, cover and audio for one track; builds the static frame; renders frames
- `Player.pde`: layout, grey levels, header, title, progress bar, ON AIR pulse
- `Cover.pde`: the album cover, "Screen" treatment (full colour through the dot grid)
- `Glow.pde`: the two-layer glow around every lit dot (none on the cover)
- `Scope.pde`: the oscilloscope line
- `DotMatrix.pde`: dot-matrix text, accented letters, wrapping long titles and adding "..."
- `Canvas.pde`: image helpers (blending, blur, dot shapes)
- `Encoder.pde`: streams frames into ffmpeg and adds the audio
- `data/fonts.json`: PixelFonts (github.com/mcer12/PixelFonts) converted from BDF, which Processing can't read
