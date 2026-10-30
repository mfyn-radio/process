---
name: show-prep
description: Write the show notes for an MFYN episode (step 2c) - artist, album and track notes to use as reference during the show. Reads the episode's tracks and the MFYN Artists sheet, researches each artist and album on the web, and writes "Show Notes.md" in the episode folder in MFYN_Show_Archive. Use when asked for show notes, show prep or a show sheet for an episode.
---

# Show prep: the show notes for an episode

Step 2c of the MFYN process. See `docs/02c-show-notes.md`.

The notes are a reference to read from on air: who the artist is, what the
album is, and something worth saying about each track. They are not post
copy. Keep them short enough to glance at mid-show.

## 1. Gather the facts

From the repo folder (`%USERPROFILE%\mfyn-process` on the MFYN PC), run:

```
python -m intake.show_notes
```

It picks the newest episode in `MFYN_Show_Archive` by air date. If the user
named an episode, pass `--episode NAME` (part of the folder name). It prints
JSON:

- `episode`: name, air date and folder.
- `running_order`: the tracks in the order of the `Tracks` folder.
- `artists`: each artist with their **Artists** row (`sheet`), and their
  albums in the episode, each with its **Releases** row (`sheet`), its
  **Labels** row (`label`) and the tracks played from it.
- `notes_file`: where to write the notes. `notes_exist`: whether a file is
  already there.
- `sheet_read`: false if the sheet couldn't be opened. Say so to the user and
  go on with the tags and research.

Tell the user the episode and track count before going further. If
`notes_exist` is true, ask whether to replace the file or stop. Never
overwrite it without a yes.

The script only reads. Don't write to the MFYN Artists sheet: it belongs to
steps 1 and 2a.

## 2. Research

For each artist, then each album, look on the web to fill in what the sheet
doesn't have. Start from the links the sheet gives (`Bandcamp page`,
`Album link`, `Website`, `Other links`), then search. Look for:

- **Artist:** where they're from, who's in it, how long they've been going,
  earlier releases, related projects.
- **Album:** label, release date, format, who recorded or produced it, the
  story or theme the artist or label tells about it, notable press.
- **Tracks played:** anything said about that track specifically (a single,
  a video, guests, lyrics' subject).
- **Live:** upcoming shows, if easy to find, with the date checked against
  the air date.

Rules:

- **Only what a source says.** No guessing and no filler. If nothing turns up,
  write "Nothing found" rather than padding.
- **Cite every researched fact** with its link. Facts from the sheet or the
  tags don't need one.
- **Watch for name clashes:** check the source is about this artist (match
  the album, label or location) before using it.
- Paraphrase; don't paste long quotes.

## 3. Write the notes

Write `notes_file` (`<episode folder>\Show Notes.md`) in UTF-8, using this
layout:

```markdown
# Show Notes: <Episode Name>

Air date: <Weekday D Month YYYY> · Made <YYYY-MM-DD> by /show-prep

## Running order

| # | Artist | Track | Album |
|---|---|---|---|
| 1 | ... | ... | ... |

## <Artist>

**From** <location> · **Links** <Bandcamp>, <Instagram>, <website>

- <2-4 short bullets: who they are>

### <Album> (<Label>, <release date>)

- <2-4 short bullets: what the album is>
- Tags: <tags>

**Played:**
- **#<position> <Track>:** <one line worth saying, or nothing if nothing found>

**Talking points:** <1-2 lines in plain speech that could be said on air>

## Sources

- <link>: <what it was used for>
```

- Artists appear in the order they first come up in the running order.
- Use the sheet's confirmed Instagram handle (`Status` = `Confirmed`) as
  `@handle`. If it's only `Suggested`, mark it "(unconfirmed)".
- Leave out a line rather than writing an empty field.

## 4. Report

Tell the user where the file is, and list anything you couldn't find or
weren't sure about (for example a possible name clash), so they can check it
before the show.
