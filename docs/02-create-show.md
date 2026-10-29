# Step 2: Create the show

The parent step. When a show is ready to make, this runs and triggers the
sub-automations, each its own step. Today the creating is manual, and you start
the one sub-automation that exists by hand.

| Sub-step | What it does | State |
|---|---|---|
| [2a. Make Reels](02a-make-reels.md) | The episode's tracks become Reels | Built |
| 2b. Instagram copy | A caption for each Reel | Not built |

When these have run, the production work is done and you reach the manual
stop: you review everything made for the post. Triggering the Publishing
Process (separate, not built yet) is up to you after that.

| | |
|---|---|
| **Input** | Albums in `MFYN_Library` |
| **Output** | The finished episode in `MFYN_Show_Archive`, with its tracks |
| **Done by** | You, for now. The parent automation isn't built yet. |
| **Triggers** | [Step 2a: Make Reels](02a-make-reels.md), for now by double-click; 2b when built |

## What happens

1. Select tracks for the show from `H:\My Drive\MFYN_Library`.
2. Create the show.
3. Archive it in `H:\My Drive\MFYN_Show_Archive`, in a folder named
   `D_M_YYYY- Episode Name`, for example `5_11_2026- Official Unofficial`.
4. Put the episode's tracks (the FLACs, copied from the library) in its
   `Tracks` folder. Step 2a also reads MP3, WAV, M4A, AIFF and OGG files.
5. **Last action:** double-click **MFYN – Make Reels** on the desktop.

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
