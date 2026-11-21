# Research

What MFYN finds out about artists and their albums, kept so it's never redone
and builds up over time. It isn't a step in the pipeline: show notes
([step 2c](02c-show-notes.md)) use it now, and captions, album stories and an
artist database could later.

See also: [process overview](README.md) ·
[the skill](../.claude/skills/research/SKILL.md)

| | |
|---|---|
| **Trigger** | You, by hand, in Claude Code on the MFYN PC. `/research` on its own researches everything new in the sheet; `/research <artist, album or episode>` just that. `/show-prep` also runs it for any artist in the episode not researched yet |
| **Input** | The MFYN Artists sheet, the artist's Bandcamp page and links, and the web |
| **Output** | One file per artist, `H:\My Drive\MFYN_Research\<Artist>.md`, added to over time |
| **Runs on** | The MFYN PC, in Claude Code opened in `%USERPROFILE%\mfyn-process` |
| **Code** | The skill [`.claude/skills/research`](../.claude/skills/research/SKILL.md), and [`intake/research.py`](../intake/research.py) for what the sheet knows |

## What it does

1. **Start from what's known:** `python -m intake.research --artist NAME`
   prints the artist's rows from the MFYN Artists sheet (Artists, and all
   their Releases and Labels) and whether they have a research file yet.
   Claude reads the file if there is one, and only researches what's missing
   or more than 6 months old.
2. **Research,** in this order: the sheet, the artist's Bandcamp page and
   album page, their other links, then the web. For small bands, Bandcamp is
   often the only real source.
3. **Keep it** in the artist's file. Every finding has its source and the
   date it was found. What wasn't found, and look-alike bands that turned out
   to be someone else, are written down too, so they aren't searched for
   again.
4. **Found in passing:** anything found about another artist who already
   has a file is added to their file, with its source. If they have no
   file, none is made: it stays in the file of the artist being researched.
5. **Report** what was added, what's still missing, and any conflicts.

## The research files

```
MFYN_Research\
  Julia Set.md
  skimp.md
  ...
```

- **Every artist in the MFYN Artists sheet should have one.** Run
  `/research` on its own now and then (after a batch of purchases, say): it
  finds the artists with no file and the albums with no section yet, and
  researches those.
- **One per artist,** with a section per album. Albums stay in the file
  for good, whichever episode they were researched for.
- **Nothing is deleted.** New findings are added with their date. A source
  that contradicts an earlier one is noted under **Conflicts**, keeping both.
- **The sheet isn't changed.** Where research disagrees with it (a label,
  say), that's a conflict in the file, and in Claude's report, for you to fix
  in the sheet by hand. The sheet stays the place for the short structured
  facts; the research files are for the prose and the sources.
- The files are plain text, to read and edit in Drive like any other file.
