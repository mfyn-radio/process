# Show cards

Spoken intros for every artist on an episode's playlist, plus an events card
to close the show. Bryant reads them on air, so they're written to be said,
not read: a few natural sentences per artist, never a fact sheet.

| | |
|---|---|
| **Input** | The episode's Bandcamp playlist (e.g. `https://bandcamp.com/music_for_your_neighbors/playlist/mfyn-december-2026`), the artists' Bandcamp pages, the MFYN Catalog (Airtable: Artists, Events) |
| **Output** | `show_cards.md` in the episode folder (`MFYN_Workspace\2026_December\show_cards.md`), which Bryant edits before the show |
| **Done by** | [Build Show](02-create-show.md#build-show), as its last step (`intake.show_cards`). Claude Code on the PC (`claude -p`, on MFYN's Claude subscription) writes the cards from facts the code gathers. Asking Claude in the project still works too (the `mfyn-show-cards` skill, as a Claude Doc) |
| **When** | When Build Show runs, once the playlist is final |
| **Log** | Build Show's log. If the cards fail, the tracks and project are still made; the run says so |

## How it runs

1. Build Show reads each release's Bandcamp page in Chrome (album, label,
   date, tags, credits, the artist's location and bio), and the MFYN Catalog's
   Artists and Events (events from today to six weeks ahead).
2. It hands those facts, as JSON, to Claude Code with the card rules below
   and no tools, so the cards can't add facts from anywhere else.
3. The reply is saved as `show_cards.md`. Run Build Show with `--no-cards` to
   skip it.

## What a card holds

One card per artist, in playlist order. An artist with two tracks gets one
card that introduces both.

- **Heading:** the play number, the artist and the place (`3. Crowd Of Chairs (Ghent) · local`).
- **The spoken intro:** three to five sentences in a conversational radio
  voice. Who they are, where they're from, what it sounds like, one hook
  (a story behind the release, a guest, a cause), and the track's name.
  Each intro hands off from place to place, so the show travels.
- **A small line underneath, in italics,** that isn't read out: the Bandcamp
  link, and any care note (an explicit or sensitive title, which is kept out
  of the spoken text).

Facts come only from the artist's Bandcamp page and the MFYN Catalog. When
something isn't there (e.g. no location), the card says so in the small line
rather than guessing. Local BeNe artists are flagged in the heading.
Bryant adds his own stories (where he bought it, a show he saw) by editing
the doc. The cards are his to rewrite.

## The event calendar

Before writing, every artist is checked against upcoming events in the MFYN
Catalog's **Events** table (title, acts and linked artists). An artist with a
BeNe date soon gets it in their card ("they're at WORM on the 5th").

The last card, **Events: get out to a show**, is a spoken closing segment.
It covers events from the air date to about six weeks after, grouped by date,
with venue, city and start time where known. Rotterdam first, then the rest of
the BeNe region, then one or two to plan ahead for. It ends by pointing
listeners to the MFYN event calendar. Events without a city or that look
private are listed in the small line, not read out.

See [Event Calendar](event-calendar.md) for how the calendar is filled.
