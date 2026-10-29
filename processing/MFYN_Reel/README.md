# MFYN Reel generator (Processing)

Turns tagged audio files into 1080×1920 Instagram Reels in the MFYN orange
dot-matrix player style. The reels include the track's audio, a live scope
line, a progress bar and the ON AIR pulse.

## One-time setup (macOS)

1. Install **Processing 4** from processing.org.
2. Install **ffmpeg**: `brew install ffmpeg`
   (the sketch looks in `/opt/homebrew/bin` and `/usr/local/bin`; if yours is
   elsewhere, set `FFMPEG` / `FFPROBE` at the top of `MFYN_Reel.pde`).
3. Keep this folder named `MFYN_Reel` (Processing needs the folder and the
   main `.pde` to share a name).

## One-time setup (Windows)

1. Install **Processing 4** from processing.org.
2. Install **ffmpeg**: in a terminal run `winget install Gyan.FFmpeg`, then restart
   the PC (or log out and in) so Processing can find it. If it still can't, set
   `FFMPEG` / `FFPROBE` at the top of `MFYN_Reel.pde` to the full paths, e.g.
   `"C:\\ffmpeg\\bin\\ffmpeg.exe"` (note the double backslashes).
3. Keep this folder named `MFYN_Reel`.

To render from the command line on Windows, use `processing-java.exe` from the
Processing install folder:

```
"C:\Program Files\Processing\processing-java.exe" --sketch="C:\path\to\MFYN_Reel" --run
```

Task Scheduler can run that command on a schedule.

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
| Title, artist | the file's tags (`TITLE`, `ARTIST`, falls back to `ALBUMARTIST`) |
| Length | the file itself |
| Cover | embedded artwork, otherwise `<track name>.jpg/.png`, `cover.jpg/.png` or `folder.jpg/.png` next to the file |
| Start point | the loudest stretch of the track, skipping the first and last 30 s |

## Settings (top of `MFYN_Reel.pde`)

| Setting | Default | |
|---|---|---|
| `CLIP_SECONDS` | 30 | reel length, max 60 |
| `START_OVERRIDE` | -1 | -1 = auto, or a number of seconds into the track |
| `PREVIEW` | true | draw frames in the window while rendering |

Look settings live in their own tabs:

- `Cover`: `COVER_TARGET` (brightness), `COVER_DIM`, `COVER_BLOCK` (pixel size)
- `Scope`: `SCOPE_GAIN` (wave height), `SCOPE_LOWPASS_HZ` (smoothness)
- `Player`: palette and layout positions

## Running it without opening the editor

In Processing, choose **Tools → Install "processing-java"**. Then this
renders everything in `input/` from Terminal:

```
processing-java --sketch="/path/to/MFYN_Reel" --run
```

You can call that command from anything that can run a shell command:
a Shortcuts automation, a Folder Action on `input/`, a `launchd` job, or a
cron entry. A window opens briefly while it renders, so the Mac needs to be
logged in.

## Command-line options

The Make Reels automation (`intake/reels.py`, step 2a of the intake process)
runs the sketch with options that override the settings:

```
processing-java --sketch=".../MFYN_Reel" --run input="<folder>" output="<folder>" seconds=30
```

`input` and `output` can be absolute paths; relative ones are inside the
sketch folder, as before.

## Files

- `MFYN_Reel.pde`: settings, the job queue, the preview window
- `Job.pde`: reads tags, cover and audio for one track; builds the static frame; renders frames
- `Player.pde`: layout, palette, header, title, progress bar, ON AIR pulse
- `Cover.pde`: the album cover treatment
- `Scope.pde`: the oscilloscope line
- `DotMatrix.pde`: dot-matrix text, wrapping long titles and adding "..."
- `Canvas.pde`: image helpers (blending, blur, dot shapes)
- `Encoder.pde`: streams frames into ffmpeg and adds the audio
- `data/fonts.json`: PixelFonts (github.com/mcer12/PixelFonts) converted from BDF, which Processing can't read
