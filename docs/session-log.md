# Session log

Where the MFYN intake project stands, and where to pick up. The newest
session is first.

## 2026-10-23: first session

### Where we got to

A purchase on Bandcamp now flows all the way to finished Reels, with an
artist directory built along the way:

| # | Step | State |
|---|---|---|
| 1 | [Acquire](01-acquire.md): Bandcamp purchase → `MFYN_Library` + the MFYN Artists sheet | **Live**, hourly on the MFYN PC |
| 2 | [Create the show](02-create-show.md) → `MFYN_Show_Archive\D_M_YYYY- Episode Name\Tracks` | Manual |
| 3 | [Make Reels](03-make-reels.md): episode tracks → 30-second Reels + `.json` details in `MFYN_Reels` | **Built**, runs on the PC; sketch layout being tuned |
| — | Instagram copy (captions) | **Not built.** Next up. |
| 4 | Schedule posts | **Not built** |

### What was built

**Step 1, Acquire** (`intake/acquire.py`, Task Scheduler task `MFYN Acquire`)
- **Trigger:** Bandcamp "Thank you!" receipts in the mfyn@ inbox.
- **Download:** Chrome opens each receipt's link, picks FLAC and downloads
  it. It's then unzipped to `H:\My Drive\MFYN_Library\Artist - Album`, and
  the email is labelled `MFYN/Downloaded`.
- **Skipped:** pre-orders wait for their release date. *Music for Your
  Neighbors - Archive* purchases are labelled `MFYN/Excluded`.
- **Records:** fills in the **MFYN Artists** Google Sheet:
  - **Artists**, the artist library: Instagram, status, location, tags,
    website, other links (no Spotify), Bandcamp page, bio.
  - **Releases:** album, artist, label or `Self-released`, release date,
    tags, album link, credits, purchased, library folder.
  - **Labels:** each label's Instagram, suggested.
  - **Tags:** one row per tag per release, for sorting and filtering.
- **Rules for the sheet:**
  - Rows are created automatically, with no review. Handles are `Suggested`
    or `Not found`.
  - The automation only fills empty cells and adds tags; it never overwrites
    typed values.
  - On a label release, the Bandcamp page's Instagram goes to the label, not
    the artist.
- **First album:** *applied communications – bites the big one*.

**Step 3, Make Reels** (`intake/reels.py`, double-click
`scripts\make_reels.cmd` / "MFYN – Make Reels")
1. Picks the newest episode by air date.
2. Confirms the Instagram handles of its artists and labels:
   - Enter keeps the suggestion;
   - typing a handle changes it;
   - `-` means no Instagram.

   This sets `Confirmed` or `No Instagram` in the sheet.
3. Runs the `processing\MFYN_Reel` sketch (30 seconds, loudest stretch).
4. Writes `MFYN_Reels\<episode>\Artist - Title.mp4` plus `.json`.
- The sketches now live in the repo (`processing\`), the master copy.
  `MFYN_Album`, the Album Story, is in the repo but **not automated, and not
  to be changed for now**.
- The Reel sketch got `input=` / `output=` / `seconds=` options (keep
  `readArgs()`), a 30-second default, and two-line artist names.
- **From here, the sketches are edited locally on the PC**, then committed
  and pushed from there (see the end of this log).

### Decisions worth remembering

- Bandcamp blocks plain scripts with a "Client Challenge", so downloading
  runs in a real Chrome window on the PC. GitHub Actions only runs the tests.
  The fallback, if Chrome gets blocked too, is a semi-manual inbox folder.
  See [decisions](01-acquire-decisions.md).
- **Google access:** the `mfyn-library-agent` Cloud project (Internal). The
  sign-in token lives on the PC in `%APPDATA%\mfyn-intake\`. Permissions:
  `gmail.modify` and `drive.file` (only the sheet the automation created).
  The Sheets API is enabled.
- **Instagram can only tag Instagram accounts.** Artists without one are
  credited by name, with their other links as a "find them on…".
- **Making Reels and scheduling posts are separate automations**, with
  `MFYN_Reels` between them.

### Later the same day: live test with new purchases

Four purchases came through step 1 by themselves, in the hourly runs at
14:07 and 15:07:

- **Fellatio:** *Ezekiel Is Unwell!* (an album) and *Plasticine Paul Live In
  The Hague* (a single track).
- **Daufødt:** *Glitter*.

All three are in `MFYN_Library`, their receipts are labelled, and their
artists and releases are in the sheet with location, tags, bio and links. For
example, Daufødt's Facebook was picked up, so link reading works.

Make Reels was re-run for the episode after deleting the old Reels. It skips
tracks that already have one.

Found along the way, still to do:

- [ ] **Labels aren't detected when a label sells through the artist's own
      Bandcamp page.** Daufødt's receipt says "purchasing from
      **FysiskFormat**", and Fellatio's says "**AT EASE**", but both were
      recorded as Self-released, because the album page belongs to the
      artist.
      - **Proposed fix:** take the label from the receipt's seller when it
        isn't the artist, let the automation replace its own
        "Self-released", then re-run `--artists`.
      - **Waiting on:** confirmation that AT EASE is a label.
- [ ] **The Reel's pixel font only has the 95 basic characters,** so ø, ù, é
      and non-Latin text come out as `?` (Daufødt, FOSCØ, Put Pùrana,
      *Nisemono 偽者*).
      - **Proposed fix, in Make Reels, without touching the sketch:**
        1. check names against the sketch's `data/fonts.json`;
        2. write plain-letter versions (ø→O, é→E…) into the *temporary
           copies'* tags before rendering;
        3. ask for a display name when a name can't be converted.
      - The `.json` details and captions keep the real spelling.
- [ ] **Selected backlog:** only chosen older purchases get downloaded, using
      `--message-id`.
      - Claude listed the 23 older receipts with their IDs.
      - The first pick, *My Wife's An Angel – Keep Honking I'm About To
        Fucking Kill Myself* (`1a0fd5b82a311729`, label Knife Hits), **didn't
        arrive**: no folder, no label. The cause isn't known yet. Next time,
        check `%APPDATA%\mfyn-intake\acquire.log` for the lines after
        `1a0fd5b82a311729: failed`.
      - Old receipts' download pages may behave differently from new ones.

### Open items

- [x] Merge mfyn-radio/process#12 (Album Story restored, this log added).
- [ ] **Finish tuning the Reel sketch** locally: long titles and artists,
      the smaller text size. Commit and push it from the PC.
- [ ] **Test Make Reels end to end** on a real episode, and check the
      `.json` files.
- [ ] **Backlog:** handled selectively. See "Selected backlog" above.
- [ ] **Clean up:** delete `H:\My Drive\MFYN_Processing` (replaced by the
      repo) and the `add-processing-sketches` branch on GitHub.
- [ ] **Untested:** receipts with several albums on them.

### Next session

1. **Instagram copy, then test it.** A generator that turns each Reel's
   `.json`, plus fresh handles from the MFYN Artists sheet, into a caption
   with:
   - `@artist` and `@label` tags, or the artist's name and other links when
     they have no Instagram;
   - album and label credit;
   - Bandcamp link wording;
   - hashtags from the Bandcamp tags;
   - the episode name and air date.

   To decide: tone and template, hashtag rules, a fixed sign-off, where the
   caption is saved (e.g. `Artist - Title.txt` next to the Reel, or in a
   sheet for review), and whether you review or edit captions before
   scheduling.
2. **Step 4, schedule posts.** To decide:
   - **Which tool:** Instagram's own API (needs a Business or Creator
     account linked to a Facebook Page) or a scheduler such as Buffer or
     Later.
   - **Timing:** around the air date, and how many per day.
   - **Tagging:** whether a proper "tag people" or Collab works for Reels
     through that tool, or whether `@mentions` in the caption have to do.

### Handy references

| What | Where |
|---|---|
| Code on the PC | `%USERPROFILE%\mfyn-process` (`git pull` to update) |
| Logs | `%APPDATA%\mfyn-intake\acquire.log`, `reels.log` |
| MFYN Artists sheet | <https://docs.google.com/spreadsheets/d/1m95uKxvyNK2EfRtT1r6fZsaTapwVbyFqbc0AOxjnpHE/edit> |
| Library | `H:\My Drive\MFYN_Library` (Drive folder `1Anmx1Om4RZdmwujyu8fEb-lUJnEULKG5`) |
| Show archive | `H:\My Drive\MFYN_Show_Archive` |
| Reels | `H:\My Drive\MFYN_Reels` |
| Google Cloud project | `mfyn-library-agent`, client `mfyn-intake-cli` |
| Troubleshooting | [step 1](01-acquire-troubleshooting.md), [step 3](03-make-reels.md#troubleshooting) |

**Saving sketch changes from the PC:**
```
cd %USERPROFILE%\mfyn-process
git add processing
git -c user.name="MFYN" -c user.email="mfyn@nothingflatdigital.com" commit -m "Describe the change"
git push
```

**Working with Claude:** changes come as pull requests on GitHub. Merge them
only once Claude says it has finished pushing. Several today were merged a
moment too early, and follow-up pull requests were needed.
