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
| 2a | [Make Reels](02a-make-reels.md): episode tracks → 30-second Reels + `.json` details in `MFYN_Reels` | **Built**, runs on the PC; sketch layout being tuned |
| 2b | Instagram copy (captions) | **Not built.** Next up. |
| — | Manual stop: you review all the content | **Not built** (the hand-off) |
| → | Publishing Process (schedule posts, …) | Separate process, **not built** |

Steps 2a and 2b are sub-automations of step 2, the parent that runs when a show
is ready. Together they produce all the content for a post, so they belong to
this intake and production process. After your review, the Publishing Process
takes over.

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

**Step 2a, Make Reels** (`intake/reels.py`, double-click
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
- **Production and Publishing are separate processes**, with your review
  between them. `MFYN_Reels` holds what you review.

### Open items

- [x] **Merge mfyn-radio/process#12.** It restores the Album Story sketch,
      which mfyn-radio/process#11 changed by mistake. Merged; `git pull` on the
      PC if it hasn't been done.
- [ ] **Finish tuning the Reel sketch** locally: long titles and artists,
      the smaller text size. Commit and push it from the PC.
- [ ] **Test Make Reels end to end** on a real episode, and check the
      `.json` files.
- [ ] **Backlog:** the ~30 purchases from before 2026-10-23 aren't
      downloaded. Run `python -m intake.acquire --dry-run --backlog`, then
      `--backlog`, then `--artists`.
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
2. **The Publishing Process** (starts after your review; not part of this
   repo's steps yet). First piece, scheduling posts. To decide:
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
| Troubleshooting | [step 1](01-acquire-troubleshooting.md), [step 2a](02a-make-reels.md#troubleshooting) |

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
