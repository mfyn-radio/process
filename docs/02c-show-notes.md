# Step 2c: Show notes

Notes on each artist, album and track in an episode, to read from during the
show or to make a show sheet from. A sub-automation of
[step 2, Create the show](02-create-show.md), independent of the others: it
needs only the episode's `Tracks` folder.

See also: [process overview](README.md) · [research](research.md) ·
[the skill](../.claude/skills/show-prep/SKILL.md)

| | |
|---|---|
| **Trigger** | You, in Claude Code on the MFYN PC: `/show-prep`, or `/show-prep <episode>` |
| **Input** | The episode's `Tracks` folder in `MFYN_Show_Archive` (the tags), the MFYN Artists sheet, and the [research files](research.md) |
| **Output** | `Show Notes.md` in the episode folder, next to `Tracks`. New research goes into `MFYN_Research` |
| **Runs on** | The MFYN PC, in Claude Code opened in `%USERPROFILE%\mfyn-process` |
| **Code** | The skill [`.claude/skills/show-prep`](../.claude/skills/show-prep/SKILL.md), and [`intake/show_notes.py`](../intake/show_notes.py) for the facts |

## What it does

1. **Gather the facts:** `python -m intake.show_notes` finds the newest
   episode (or the one named) and prints, as JSON, its running order and,
   for each artist and album, their rows from the MFYN Artists sheet and
   whether the artist has a research file. It only reads. Without the sheet
   (`--no-sheet`, or if it can't be opened) it goes on with the tags alone.
2. **Make sure the research is there:** for any artist not researched yet,
   or an album of theirs that isn't, Claude runs [research](research.md)
   first. That's kept in `MFYN_Research`, so the next episode with the same
   artist starts from it.
3. **Write** `MFYN_Show_Archive\<episode folder>\Show Notes.md`, from the
   sheet and the research files:
   ```
   5_11_2026- Normal Show\
     Show Notes.md
     Tracks\
   ```
   The notes have the running order, then a section per artist (where
   they're from, links, a few lines on who they are), per album (label,
   release date, tags, what it is), a line on each track played, talking
   points, what to check before the show, and the sources. If the file
   already exists, Claude asks before replacing it.
4. **Report:** where the notes are, which research files changed, and what
   to check before the show.

The running order is the order of the files in `Tracks`, by name.

## Why two skills

Research is the slow part, and worth keeping, so the research skill does it
once and keeps it. Show prep only lays it out for the show. The facts come
from scripts, so they're the same each time and can be tested. Each part can
be improved on its own.
