---
name: research
description: Research an MFYN artist and their albums, and keep what's found in the artist's file in MFYN_Research, with sources, so it's never redone and builds up over time. With no argument, researches everything new in the MFYN Artists sheet: artists with no file yet, and new albums of artists who have one. Or takes an artist, an album, or an episode (all its artists). Used by /show-prep; also use when asked to research or look up an artist or album.
---

# Research: artists and albums, kept

See `docs/research.md`. Research is kept so it's never wasted: one file per
artist in `MFYN_Research` (`H:\My Drive\MFYN_Research`), added to over time.
Show notes (`/show-prep`), and later captions and album stories, are written
from these files.

**Never write to the MFYN Artists sheet.** Disagreements with it are noted in
the research file for the user to settle.

**Every artist in the MFYN Artists sheet should have a research file.**

## 1. What to research

- **Nothing named (the usual run): everything new in the sheet.**
  `python -m intake.research --missing` lists `artists` with no research
  file, and `releases` (albums) that have no section in their artist's file
  yet. Research each new artist with all their releases in the sheet, and
  each new release on its own. If there are many, tell the user how many and
  ask before starting; offer to do them a few at a time.
- **An artist:** `python -m intake.research --artist "NAME"`
- **An album:** the same, for its artist; research only that album's section.
- **An episode:** `python -m intake.show_notes [--episode NAME]`, then each
  artist in it, and only the albums the episode plays.

Run these from the repo folder (`%USERPROFILE%\mfyn-process`). They print
JSON with what the sheet knows (`sheet`, each release's `sheet` and `label`),
the artist's `research_file`, and whether it exists yet (`research_exists`).

If the file exists, read it first. Then research only what's missing:

- an album that has no section yet;
- a section whose last research is more than 6 months old, or that the user
  asked to refresh;
- an item under "Not found" that's more than 6 months old.

If everything is covered and current, say so and stop.

## 2. Research, in this order

1. **The sheet:** location, bio, links, label, release date, tags and credits
   that step 1 read from Bandcamp. Don't copy these into the file; the sheet
   is where they live. Only note where research disagrees with them.
2. **The artist's Bandcamp page and the album page** (`Bandcamp page`,
   `Album link` in the sheet). For small bands this is often the only real
   source: the about text, credits, the album's notes, and the label.
3. **The artist's other links** (website, Instagram, `Other links`).
4. **The web:** interviews, reviews, the label's page, press, other releases,
   members and related bands, shows.

Look for:

- **Artist:** where they're from, members, when they started, earlier
  names, other releases, related projects, labels, press.
- **Album:** label and catalogue number, release date and formats, who
  recorded, mixed and mastered it, the story or theme the artist or label
  gives, singles and videos, reviews.
- **Tracks:** anything about a track itself: a single, a video, guests,
  covers, what it's about.

Rules:

- **Only what a source says.** No guessing. Your own reading (for example
  "the title suggests a cover") goes under "Not confirmed", marked as such.
- **Every finding has a source** (a number in Sources) and the date found.
- **Name clashes:** make sure a source is about this artist (match the
  album, label, location or Bandcamp page). Note rejected look-alikes under
  "Not this artist", so they aren't checked again.
- Paraphrase; don't paste long quotes. Short quotes from press are fine.

## 3. Keep it

Write `research_file` (`MFYN_Research\<Artist>.md`, UTF-8). Create the
folder if it isn't there.

**Never delete what's there.** Add to it:

- New findings are added under the right heading, with the date.
- If a new source contradicts an old finding, keep both and add the
  contradiction under "Conflicts".
- When something is found that was under "Not found", move it into the
  findings.

Layout:

```markdown
# <Artist>

Last researched: <YYYY-MM-DD>

## Artist

- <finding> [n] (<YYYY-MM-DD>)

**Not found** (searched <YYYY-MM-DD>): <members, location…>
**Not this artist:** <look-alike bands, with a link or where from>

## Album: <Title> (<year>)

Last researched: <YYYY-MM-DD>

- <finding> [n] (<YYYY-MM-DD>)

### Tracks

- **<Track>:** <finding> [n] (<YYYY-MM-DD>)

**Not found** (searched <YYYY-MM-DD>): <…>
**Not confirmed:** <your own reading, clearly marked>

## Conflicts

- <YYYY-MM-DD> <what disagrees, between which sources, or with the sheet's
  which column>. Unresolved.

## Sources

1. <link>: <what it gave> (read <YYYY-MM-DD>; or "search result only" if the
   page itself couldn't be opened)

## Log

- <YYYY-MM-DD>: <what was researched>, for <episode / on request>
```

- Album headings start exactly `## Album: <Title as in the sheet>`: that's
  how a new album is told apart from one already researched.
- Number sources once per file and keep the numbers; add new ones at the end.
- Sections for different albums stay in the file for good, including ones
  not played in the current episode.

## 4. Found in passing

While researching, you may find something about **another** artist, one
outside what you were asked to research (a split release, a shared member,
a tour together).

- **If that artist has a research file,** add it there, with its source like
  any finding, under a heading `## Found while researching <artist>
  (<YYYY-MM-DD>)`. Apply the same name-clash check, and add anything that
  contradicts their file to Conflicts. Don't change their "Last researched"
  dates, and don't research them any further.
- **If they have no file, don't create one.** Keep it in the current
  artist's file, where it was found (for example under related projects).
  If they're in the sheet, they're due a file anyway: mention them in the
  report.

## 5. Report

Tell the user which files were created or added to (including other
artists' files, from findings in passing), what's still not found,
and every new conflict, especially with the sheet, so they can fix the sheet
by hand.
