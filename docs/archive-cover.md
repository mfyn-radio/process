# Archive cover

The orange archive cover for each episode, saved in the episode's own folder
in `MFYN_Show_Archive`. Part of [step 2, Create the show](02-create-show.md).

See also: [the archive sketch](../processing/MFYN_Archive/README.md)

| | |
|---|---|
| **Trigger** | The start of every **MFYN – Make Reels** run, after you confirm the tracks. No double-click of its own |
| **Input** | The episode folder's name, e.g. `5_11_2026-Normal Show-Skramish` |
| **Output** | `MFYN_archive_03.png` (1080×1080) in that episode folder |
| **Runs on** | The MFYN PC (Processing 4) |
| **Code** | [`intake/archive_cover.py`](../intake/archive_cover.py) and the sketch [`processing/MFYN_Archive`](../processing/MFYN_Archive) |

## Number and date

- **Date:** from the folder name, written as it appears on the cover:
  `5_11_2026-...` becomes `5 NOVEMBER 2026`.
- **Number:** the 5 November 2026 episode is **No. 3**. Each later episode
  folder in `MFYN_Show_Archive` counts up by one, in air-date order: the next
  episode is No. 4, then No. 5. Episodes before 5 November 2026 get no cover
  automatically.
- The start is set in `intake/config.py` (`ARCHIVE_FIRST_DATE`,
  `ARCHIVE_FIRST_NUMBER`).

Because the number comes from the order of the folders, a folder added later
with an earlier date shifts the numbers of the episodes after it. Covers that
already exist are not remade, so check the number if you add an episode out of
order.

## Running it

It runs at the start of **MFYN – Make Reels**. An episode that already has its
cover is skipped. To remake one, delete its `MFYN_archive_NN.png` and run again.

From Command Prompt, in the repo folder, it can also run on its own:

```
python -m intake.archive_cover                  # the newest episode
python -m intake.archive_cover --episode NAME   # the episode whose folder name contains NAME
```

For a cover the automation doesn't make (an older episode, or a print-size
2160 version), use the sketch directly: see its
[README](../processing/MFYN_Archive/README.md).
