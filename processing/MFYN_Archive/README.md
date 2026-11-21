# MFYN archive cover (Processing)

The cover for archived MFYN radio shows: `MFYN` in black ink on coloured card,
with the episode number, the date and `RADIO ARCHIVE`. A 2160×2160 PNG: the
cover must be at least 1800×1800, and 2160 is twice the 1080 design size, so
the layout and grain scale exactly. Only the number and the date change per
episode.

**Every cover gets a new random paper colour**: any hue, from soft to strong,
picked fresh each time the cover is rendered. A colour is only used if the black ink reads
well on it (a contrast ratio of at least 5 at the paper's darkest corner). The
ranges are in `Spec.pde`. Set `RANDOM_COLOUR` to false for the original orange
on every cover. The paper texture and the type are the same on every cover.

This cover is the brand anchor, so it is kept apart from the video post and Story
sketches: it shares no code or settings with them, every look constant is in
`Spec.pde`, the fonts are bundled in `data/`, and the paper uses a fixed random
seed. Re-rendering an episode gives the identical file.

Normally the [archive cover](../../docs/archive-cover.md) automation runs this
for you: Make Episode Content makes each episode's cover in its folder in
`MFYN_Show_Archive`, numbered from No. 3 (5 November 2026). The steps below
are for running the sketch by hand, for example for an older episode or a
print-size version.

## One-time setup (Windows)

Install **Processing 4** from processing.org. Nothing else is needed: no
ffmpeg, and the fonts are in `data/`. Keep this folder named `MFYN_Archive`
(Processing needs the folder and the main `.pde` to share a name).

## Making covers

1. List the episodes in `input/episodes.csv`, one per line, number then date:
   ```
   # number,date
   2,8 October 2026
   3,15 October 2026
   ```
   Lines starting with `#` are ignored. The date is written as it should
   read (day, month spelled out, four-digit year) and is upper-cased on the
   cover. The number is zero padded: `2` becomes `NO. 02`.
2. Open `MFYN_Archive.pde` and press **Run**.
3. Each cover appears in `output/` as `MFYN_archive_02.png`, with its
   YouTube playlist image `MFYN_tracklist_02.png` (below) next to it. The
   window shows each cover when it is done and closes itself at the end.

Episodes that already have a cover in `output/` are skipped, so you can keep
adding lines and re-run. To remake a cover, delete its PNG.

`input/episodes.csv` is kept in the repo, so the list of archive episodes
travels with it.

## Settings (top of `MFYN_Archive.pde`)

| Setting | Default | |
|---|---|---|
| `SIZE` | 2160 | the cover's width and height in pixels: a multiple of 1080, at least 1800 (so 2160 or 3240) |
| `SEED` | 7 | the paper's random seed. Leave it, so every episode prints on the same paper |
| `TRACKLIST_SEED` | 8 | the same for the tracklist image |
| `LABEL` | `RADIO ARCHIVE` | the bottom-right label |
| `RANDOM_COLOUR` | true | a new random paper colour on every cover; false = orange `#F07C0E` on every cover |
| `PREVIEW` | true | show each cover in the window |

The design itself (colours, type, positions, paper and ink) is in `Spec.pde`.

## Running it without opening the editor

```
"C:\Program Files\Processing\processing-java.exe" --sketch="C:\path\to\MFYN_Archive" --run
```

(newer versions of Processing use `Processing.exe cli` instead of
`processing-java.exe`). For a single cover, without the CSV:

```
"C:\Program Files\Processing\processing-java.exe" --sketch="C:\path\to\MFYN_Archive" --run number=2 "date=8 October 2026"
```

`input=<folder>`, `output=<folder>` and `size=<px>` override the settings.
`colour=#RRGGBB` uses that paper colour instead of a random one, for example
to make the tracklist image for a cover that already exists.

## The tracklist image

The square image for the episode's YouTube playlist, written in the same run
as the cover and in the same colour: the cover inverted. The paper is the
cover's ink colour, `#141210`, and the type is printed flat in the cover's
paper colour (at `TL_INK_LEVEL`, a touch under it). It uses the same paper
texture, ink treatment and fonts, with its own seed, and `TRACKLIST` in place
of `RADIO ARCHIVE`.

Its positions are in `Spec.pde` (`TL_WORDMARK_BASELINE`, `TL_LINE1_BASELINE`,
`TL_LINE2_BASELINE`): `MFYN` is moved down and the two small lines up, so the
type sits between about y 260 and y 850, clear of the YouTube Music app's
buttons at the top and its title fade at the bottom.

## Files

- `MFYN_Archive.pde`: settings, the episode list, rendering a cover and its tracklist image, the preview window
- `Spec.pde`: every design constant
- `Paper.pde`: the orange card (tooth, grain, mottling, fibres, light falloff, vignette)
- `Colour.pde`: the random paper colour and its contrast check
- `Ink.pde`: the type, drawn glyph by glyph at 4× and averaged down, and the ink treatment
- `Fields.pde`: noise, Gaussian blur and bicubic upscaling
- `data/`: Inter Display Black and Inter Bold (SIL Open Font License, `Inter-LICENSE.txt`)

## How it was checked

Against the approved episode 2 cover from the design handoff
(`MFYN_archive_02_1080.png`), with the orange paper:

- All four ink boxes match: `MFYN` x 83-1005, y 120-360; `NO. 02` x 80-225,
  y 909-937; the date x 80-455, y 969-997; `RADIO ARCHIVE` x 655-1000.
- The paper measures the same as the approved cover: about rgb (234, 121, 14)
  in the middle, (225, 116, 14) top left and (204, 106, 12) bottom right.
- The grain has the same strength at 1080 and at 2160 as the handoff's
  references, so a print-size cover has the same grain, not finer grain.
- With `RANDOM_COLOUR` off, re-rendering gives an identical file, and the
  cover is byte-identical to the one made before the tracklist image was
  added.
- A 2160 cover renders within 256 MB of memory (the text is drawn in slices).
- The longest date, `28 SEPTEMBER 2026`, ends at x 535, about 120 px before
  `RADIO ARCHIVE`. `NO. 100` ends at x 248.

The random numbers come from Java, not numpy, so the grain pattern is not
pixel for pixel the same as the Python reference. Its look is.
