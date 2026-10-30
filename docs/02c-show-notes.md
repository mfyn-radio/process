# Step 2c: Show notes

Notes on each artist, album and track in an episode, to read from during the
show or to make a show sheet from. A sub-automation of
[step 2, Create the show](02-create-show.md), independent of the others: it
needs only the episode's `Tracks` folder.

See also: [process overview](README.md) ·
[the skill](../.claude/skills/show-prep/SKILL.md)

| | |
|---|---|
| **Trigger** | You, in Claude Code on the MFYN PC: `/show-prep`, or `/show-prep <episode>` |
| **Input** | The episode's `Tracks` folder in `MFYN_Show_Archive` (FLAC tags), the MFYN Artists sheet, and the web |
| **Output** | `Show Notes.md` in the episode folder, next to `Tracks` |
| **Runs on** | The MFYN PC, in Claude Code opened in `%USERPROFILE%\mfyn-process` |
| **Code** | The skill [`.claude/skills/show-prep`](../.claude/skills/show-prep/SKILL.md), and [`intake/show_notes.py`](../intake/show_notes.py) for the facts |

## What it does

1. **Gather the facts:** `python -m intake.show_notes` finds the newest
   episode (or the one named) and prints, as JSON, its running order and,
   for each artist and album, their rows from the MFYN Artists sheet: the
   Artists, Releases and Labels tabs. It only reads. Without the sheet
   (`--no-sheet`, or if it can't be opened) it goes on with the tags alone.
2. **Research:** Claude looks up each artist and album on the web, starting
   from the links in the sheet, and cites every fact it uses. If nothing
   turns up, it says so rather than filling in.
3. **Write** `MFYN_Show_Archive\<episode folder>\Show Notes.md`:
   ```
   5_11_2026- Normal Show\
     Show Notes.md
     Tracks\
   ```
   The notes have the running order, then a section per artist (where
   they're from, links, a few lines on who they are), per album (label,
   release date, tags, what it is), a line on each track played, talking
   points, and the sources. If the file already exists, Claude asks before
   replacing it.
4. **Report:** where the file is, and what it couldn't find or wasn't sure
   of, for you to check before the show.

## Why a skill

Research and writing are judgement work, so a skill does them. The facts
come from a script so they're the same each time and can be tested. Each
part can be improved on its own.
