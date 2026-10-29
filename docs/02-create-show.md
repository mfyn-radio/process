# Step 2: Create the show

A Bandcamp playlist becomes an episode folder in `MFYN_Show_Archive`, with the
tracks copied from `MFYN_Library`. Then it goes straight on to Make Reels.

| | |
|---|---|
| **Trigger** | You double-click **MFYN – Create Show** and paste the playlist link |
| **Input** | A Bandcamp playlist on the `music_for_your_neighbors` fan account, e.g. <https://bandcamp.com/music_for_your_neighbors/playlist/mfynnov2026> |
| **Output** | `MFYN_Show_Archive\D_M_YYYY- Normal Show N\Tracks\` with the playlist's FLACs |
| **Runs on** | The MFYN PC (Chrome, like step 1) |
| **Code** | [`intake/create_show.py`](../intake/create_show.py), [`intake/playlist.py`](../intake/playlist.py), started by [`scripts/create_show.cmd`](../scripts/create_show.cmd) |
| **Next** | [Step 3: Make Reels](03-make-reels.md), started automatically |

## What happens

1. **Make the playlist on Bandcamp** from tracks MFYN owns, in running order.
   It can stay private (see [the Chrome profile](#the-chrome-profile)).
2. **Double-click MFYN – Create Show** and paste the playlist's link. The
   `?from=collection…` part of the link doesn't matter.
3. **Read the playlist:** Chrome opens the link, because Bandcamp blocks plain
   scripts, and the tracks are read in order. It uses its own Chrome profile,
   signed in to Bandcamp.
4. **Find each track in the library:**
   1. Look for the `Artist - Album` folder.
   2. Inside it, match the FLAC by its title tag, then by its file name.

   Every track is listed with the file it matched. **If any track isn't
   found, nothing is created.** Usually the album hasn't been downloaded yet:
   run Acquire, or wait for the hourly run, and try again.
5. **Create the episode folder** with a placeholder name you change later
   (see below), and copy the FLACs into its `Tracks` folder, unchanged.
6. **Make Reels** runs on that episode: it asks `Make Reels for these N
   track(s)?`, then for any Instagram handles that aren't confirmed yet.

## The episode folder

```
MFYN_Show_Archive\
  5_11_2026- Normal Show\
    Tracks\
      Daufødt - Glitter - 01 Glitter.flac
      Daufødt - Glitter - 02 Stemmene i hodet.flac
      Daufødt - Glitter - 03 Toxic.flac
```

- **Name:** the air date as **day_month_year**, then `- `, then the episode
  name. Step 3 reads both.
  - **Date:** today's date, unless you give one: `--date 12_11_2026`.
  - **Name:** a placeholder, numbered: `Normal Show`, then `Normal Show 1`,
    `Normal Show 2`… Rename the folder (and fix the date) whenever you like.
    The next number is one more than the highest `Normal Show` folder in the
    archive.
  - **An empty `Normal Show` folder is reused:** if a placeholder folder has
    no tracks in it, the tracks go there, keeping its date, instead of making
    another one.
- **Tracks:** copied from the library as they are, with Bandcamp's file
  names. Step 3 reads the artist, title and album from their FLAC tags, so
  don't strip the tags.
- Running it again on the same playlist only copies what's missing.

## Running it by hand

From `%USERPROFILE%\mfyn-process`:

```
python -m intake.create_show LINK                    # then Make Reels
python -m intake.create_show LINK --date 12_11_2026  # air date (default: today)
python -m intake.create_show LINK --name "Episode"   # instead of "Normal Show N"
python -m intake.create_show LINK --no-reels         # stop once the tracks are copied
python -m intake.create_show LINK --dry-run          # list the tracks and folder, change nothing
```

## The Chrome profile

The playlists are private, so only the signed-in `music_for_your_neighbors`
account can see them. Create Show therefore keeps its own Chrome profile in
`%APPDATA%\mfyn-intake\chrome-profile`, separate from your everyday Chrome and
from Acquire's, which starts blank every run.

- **First run, or whenever Bandcamp signs it out:** Bandcamp answers "Sorry,
  that something isn't here". Create Show then opens Bandcamp's sign-in page in
  its Chrome window and waits. Sign in as `music_for_your_neighbors` in that
  window, then press Enter in the black window. It reads the playlist again.
- **After that:** the profile stays signed in, and nothing is asked.
- **To sign it out,** close every Create Show window and delete the
  `chrome-profile` folder. The next run asks you to sign in again.

## Setup

Make a desktop shortcut to `scripts\create_show.cmd` named
**MFYN – Create Show**, like the Make Reels one. Nothing else: it uses the
Chrome and Python set up for step 1. Sign in to Bandcamp the first time it
asks.

## Troubleshooting

The log is `%APPDATA%\mfyn-intake\create_show.log`.

With Python from the Microsoft Store (as on the MFYN PC), Windows keeps that
folder somewhere else:
`%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\Roaming\mfyn-intake`.
To get the log and any saved page onto Drive for Claude to read, run this in
`%USERPROFILE%\mfyn-process`:

```
python -c "import shutil; from intake import config; [print(shutil.copy(p, config.SHOW_ARCHIVE_DIR)) for p in (config.CREATE_SHOW_LOG_FILE, config.APP_DIR / 'playlist-page.html') if p.exists()]"
```

- **"Bandcamp still won't show the playlist":** the Chrome window wasn't
  signed in as `music_for_your_neighbors`, the account that owns the
  playlist, when you pressed Enter. Run it again and sign in when asked.
- **"Chrome wouldn't start":** a Create Show Chrome window is still open,
  maybe from a run still waiting for Enter in its black window, or one that
  crashed. Its profile can only be used by one window at a time. Close it,
  and that black window, or end `chrome.exe` in Task Manager, and try again.
- **"Couldn't find any tracks on the playlist page":** Bandcamp's playlist
  pages are new and their layout may change. A copy of the page is saved as
  `%APPDATA%\mfyn-intake\playlist-page.html`. Send it to Claude to adjust
  [`intake/playlist.py`](../intake/playlist.py). Check the playlist is public too.
- **A track is "NOT IN THE LIBRARY":** check that `MFYN_Library` has its
  `Artist - Album` folder. A folder named differently is still searched if
  its name ends with the album or starts with the artist (a compilation filed
  under the label, say). Within it, the track's title on Bandcamp has to match
  its title tag or the end of its file name.
- **Chrome is blocked by a "Client Challenge":** see
  [step 1's troubleshooting](01-acquire-troubleshooting.md).
