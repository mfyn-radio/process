---
name: show-prep
description: Write the show notes for an MFYN episode (step 2c) - artist, album and track notes to use as reference during the show. Makes sure each artist has been researched (the research skill, kept in MFYN_Research), then writes "Show Notes.md" in the episode folder in MFYN_Show_Archive. Use when asked for show notes, show prep or a show sheet for an episode.
---

# Show prep: the show notes for an episode

Step 2c of the MFYN process. See `docs/02c-show-notes.md`.

The notes are a reference to read from on air: who the artist is, what the
album is, and something worth saying about each track. They are not post
copy. Keep them short enough to glance at mid-show.

The research itself is done and kept by the **research** skill
(`.claude/skills/research/SKILL.md`), one file per artist in
`MFYN_Research`. Show prep only writes from those files, so nothing it finds
is lost.

## 1. Gather the facts

From the repo folder (`%USERPROFILE%\mfyn-process` on the MFYN PC), run:

```
python -m intake.show_notes
```

It picks the newest episode in `MFYN_Show_Archive` by air date. If the user
named an episode, pass `--episode NAME` (part of the folder name). It prints
JSON:

- `episode`: name, air date and folder.
- `running_order`: the tracks in the order of the `Tracks` folder (file-name
  order). Say so if it doesn't look like a chosen order.
- `artists`: each artist with their **Artists** row (`sheet`), their
  `research_file` and whether it exists (`research_exists`), and their
  albums in the episode, each with its **Releases** row (`sheet`), its
  **Labels** row (`label`) and the tracks played from it.
- `notes_file`: where to write the notes. `notes_exist`: whether a file is
  already there.
- `sheet_read`: false if the sheet couldn't be opened. Say so to the user and
  go on.

Tell the user the episode and track count before going further. If
`notes_exist` is true, ask whether to replace the file or stop. Never
overwrite it without a yes.

Don't write to the MFYN Artists sheet.

## 2. Make sure the research is there

For each artist, read their research file. Follow the research skill for
any artist with no file, or whose file is missing an album the episode
plays, or is out of date by that skill's rules. Research only the albums in
this episode.

## 3. Write the notes

Write `notes_file` (`<episode folder>\Show Notes.md`) in UTF-8, from the
sheet and the research files only. Use this layout:

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

**Check before the show:** <conflicts or doubts from the research file>

## Sources

- <link>: <what it was used for>
```

- Artists appear in the order they first come up in the running order.
- Use the sheet's confirmed Instagram handle (`Status` = `Confirmed`) as
  `@handle`. If it's only `Suggested`, mark it "(unconfirmed)".
- Carry over the sources the notes use from the research files.
- Leave out a line rather than writing an empty field.

## 4. Report

Tell the user where the notes are, which research files were created or
added to, and anything to check before the show: conflicts (especially with
the sheet), name clashes, and what couldn't be found.
