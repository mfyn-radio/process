# Archive cover

The orange archive cover for each episode, saved in the episode's own folder
in `MFYN_Show_Archive`. Part of [step 2, Create the show](02-create-show.md).

See also: [the archive sketch](../processing/MFYN_Archive/README.md)

| | |
|---|---|
| **Trigger** | The start of every **MFYN – Make Episode Content** run, after you confirm the tracks. Both images are always made together, by one sketch. No double-click of its own |
| **Input** | The episode folder's name, e.g. `5_11_2026-Normal Show-Skramish` |
| **Output** | `MFYN_archive_03.png` (2160×2160; the minimum is 1800) and the YouTube playlist image `MFYN_tracklist_03.png`, both in that episode folder |
| **Runs on** | The MFYN PC (Processing 4) |
| **Code** | [`intake/archive_cover.py`](../intake/archive_cover.py) and the sketch [`processing/MFYN_Archive`](../processing/MFYN_Archive) |

## Number, date and colour

- **Date:** from the folder name, written as it appears on the cover:
  `5_11_2026-...` becomes `5 NOVEMBER 2026`.
- **Number:** the 5 November 2026 episode is **No. 3**. Each later episode
  folder in `MFYN_Show_Archive` counts up by one, in air-date order: the next
  episode is No. 4, then No. 5. Episodes before 5 November 2026 get no cover
  automatically.
- **Colour:** a new random paper colour every time (any hue, soft to strong), always one the
  black ink reads well on. See the [sketch README](../processing/MFYN_Archive/README.md).
- The start is set in `intake/config.py` (`ARCHIVE_FIRST_DATE`,
  `ARCHIVE_FIRST_NUMBER`).

Because the number comes from the order of the folders, a folder added later
with an earlier date shifts the numbers of the episodes after it. Covers that
already exist are not remade, so check the number if you add an episode out of
order.

## The tracklist image (YouTube playlist)

`MFYN_tracklist_NN.png` is the square image for the episode's YouTube
playlist. It is the cover inverted: the cover's near-black ink (`#141210`) is
the paper, and `MFYN`, the number, the date and `TRACKLIST` are printed in
that episode's cover colour. It comes out of the same render as the cover, so
the two always match.

The YouTube Music app puts its back, edit and share buttons over the top of
the image and fades the bottom into the playlist title, so the type sits
further in than on the cover: between about y 260 and y 850 (in 1080 space),
instead of 120 to 997.

A cover made before the tracklist image existed has no tracklist image, and
the run says so. To make one by hand in the same colour, run the sketch with
that cover's number, date and `colour=#RRGGBB` (see the
[sketch README](../processing/MFYN_Archive/README.md)).

## Running it

It runs at the start of **MFYN – Make Episode Content**. The new cover and its
tracklist image open in the image viewer and you're asked `Keep this cover and
tracklist image?`. Press Enter (or `y`) to keep them, and both are saved in the
episode folder. Type `n` and another pair is made with a new colour, until you
keep one. An episode that already has its cover is skipped. To remake one,
delete its `MFYN_archive_NN.png` (and `MFYN_tracklist_NN.png`) and run again.

From Command Prompt, in the repo folder, it can also run on its own:

```
python -m intake.archive_cover                  # the newest episode
python -m intake.archive_cover --episode NAME   # the episode whose folder name contains NAME
```

For a cover the automation doesn't make (an older episode), use the sketch
directly: see its
[README](../processing/MFYN_Archive/README.md).
