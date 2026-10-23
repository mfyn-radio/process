# Step 2: Create the show

Manual. Picking tracks from the library, making the episode, and archiving it.

| | |
|---|---|
| **Input** | Albums in `MFYN_Library` |
| **Output** | The finished episode in `MFYN_Show_Archive`, with its tracks |
| **Done by** | You |
| **Next** | [Step 3: Make Reels](03-make-reels.md), started with a double-click |

## What happens

1. Select tracks for the show from `H:\My Drive\MFYN_Library`.
2. Create the show.
3. Archive it in `H:\My Drive\MFYN_Show_Archive`, in a folder named
   `D_M_YYYY- Episode Name`, for example `5_11_2026- Official Unofficial`.
4. Put the episode's tracks (the FLACs, copied from the library) in its
   `Tracks` folder.
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
  name. Step 3 reads both, and picks the episode with the latest air date.
- **Tracks:** copy them from the library as they are. Step 3 reads the
  artist, title and album from their FLAC tags, so don't strip the tags.
