# Show calendar

Live shows from the posts MFYN saves on Instagram go on a Google calendar of
their own, **MFYN Shows**. Save a show's post to the **events** collection;
once a day the automation reads it and adds the event. This is
mfyn-radio/process#36, the Instagram half of mfyn-radio/process#15. Other sources come later.

See also: [process overview](README.md) · [Google Cloud setup](setup/google-cloud.md)

| | |
|---|---|
| **Trigger** | Task Scheduler task `MFYN Show Calendar`, daily |
| **Input** | New posts in one saved collection on MFYN's Instagram |
| **Output** | Events on the **MFYN Shows** calendar, owned by mfyn@ |
| **Runs on** | The MFYN PC, while signed in (Chrome, Instagram signed in as MFYN) |
| **Code** | [`intake/events.py`](../intake/events.py), with [`instagram.py`](../intake/instagram.py), [`flyer.py`](../intake/flyer.py) and [`show_calendar.py`](../intake/show_calendar.py), started by [`scripts/run_events.cmd`](../scripts/run_events.cmd) |
| **Log** | `%APPDATA%\mfyn-intake\events.log` |

## What it does

1. **Finds new posts.** Chrome opens the collection and lists posts it hasn't
   read before, newest first, at most 15 a run. Pages open a few seconds
   apart, so Instagram doesn't take it for a bot.
2. **Reads each post:** its caption, who posted it and when, and its image.
   For a carousel that's the first image only. For a Reel it's the cover.
3. **Finds the events.** Claude Code on the PC (`claude -p`, on the Claude
   subscription, so no extra bill) reads the flyer and the caption and returns
   each event: title, acts, date, times, venue, city and tickets. A tour
   poster can give several. Flyers often leave out the year, so it's worked
   out from the posting date. A post that isn't an event gives none.
4. **Adds them to MFYN Shows**, laid out like this:
   ```
   Calls From The Hull IV
   V11, Rotterdam
   Sat 28 Nov 2026

   alternative, kraut, krautpop, nowave

   (the post's caption)

   Save & Share on Instagram                 <- a link to the post
   ```
   - **The first line** is the tags: genres the post names or hashtags,
     plus the tags in the MFYN Artists sheet for acts already in the library
     (leaving out their town and country). No tags, no line.
   - **The event's link** (Calendar's "source") is a tickets or event address
     written in the post, else the Instagram post. "Link in bio" doesn't
     count.
   - Without a start time it's an all-day event; without an end time it's
     3 hours long. Shows that are already over are skipped.
5. **Remembers the post** in `%APPDATA%\mfyn-intake\events.json`, so it's
   never read again. A post that fails is retried next run.

**Your edits are safe.** Once an event is on the calendar the automation never
changes it. Fix an event by hand and it stays fixed. Delete one and
it stays deleted.

**What it can only touch:** the calendars it creates itself (the
`calendar.app.created` permission). It can't see mfyn@'s other calendars.

## Setting it up on the PC

Needs: everything from [step 1's setup](01-acquire.md#setting-it-up-on-the-pc)
(Python, Chrome, the repo, the Google sign-in), plus Claude Code signed in
to your Claude subscription. Nothing new to buy.

1. **Update the code** and its packages, from `%USERPROFILE%\mfyn-process`:
   ```
   git pull
   pip install -r requirements.txt
   ```
2. **Enable the Google Calendar API** in the `mfyn-library-agent` project
   ([setup](setup/google-cloud.md)).
3. **Sign in to Google again**, so the sign-in includes the calendar:
   ```
   python -m intake.acquire --setup "%APPDATA%\mfyn-intake\client_secret.json"
   ```
   Until you do, Acquire and the rest carry on as before. Only this
   automation needs the new permission.
4. **Install Claude Code** and sign in. In PowerShell:
   ```
   irm https://claude.ai/install.ps1 | iex
   ```
   Then open a new Command Prompt, run `claude`, choose to sign in with your
   Claude account (the subscription), and type `/exit` once it's ready.
   Check it with `claude --version`. Each post read counts toward the
   subscription's usage limits, like a short chat.
5. **Make the collection.** On Instagram, signed in as MFYN, make a saved
   collection (MFYN's is called **events**) and save a show's post to it. Open it in
   Chrome and copy the address, e.g.
   `https://www.instagram.com/<account>/saved/shows/17900000000000000/`.
6. **Set the collection**, in Command Prompt (it takes effect in new windows):
   ```
   setx MFYN_INSTAGRAM_COLLECTION "https://www.instagram.com/<account>/saved/shows/<id>/"
   ```
   Times on flyers are read as Rotterdam time (`Europe/Amsterdam`). To change
   that, set `MFYN_TIMEZONE` the same way. `MFYN_CLAUDE_MODEL` (e.g. `opus`)
   picks the model; by default it's Claude Code's own.
7. **Sign in to Instagram**, once, in the automation's own Chrome profile
   (kept in `%USERPROFILE%\mfyn-chrome-instagram`):
   ```
   python -m intake.events --setup-instagram
   ```
   Sign in as MFYN in the window that opens, then press Enter.
8. **Try it** without adding anything:
   ```
   python -m intake.events --dry-run
   ```
   Then run it for real. The first real run creates the **MFYN Shows**
   calendar and logs its ID (`c_…@group.calendar.google.com`; it's also
   `calendar_id` in `%APPDATA%\mfyn-intake\events.json`).
   It appears in mfyn@'s Google Calendar under **My calendars**. If it
   doesn't, subscribe to it with the ID from the log: **Other calendars → +
   → Subscribe to calendar**. Share it from there if you like.
9. **Schedule it daily:**
   ```
   schtasks /Create /TN "MFYN Show Calendar" /SC DAILY /ST 10:17 /TR "\"%USERPROFILE%\mfyn-process\scripts\run_events.cmd\""
   ```

## Running it by hand

```
python -m intake.events [--dry-run] [--post SHORTCODE]
```

- `--dry-run` reads the new posts and logs each event it would add, with its
  description, so you can check the layout. It adds nothing and doesn't
  remember the posts, so they're read again next time.
- `--post` reads one post, even one read before: the code after `/p/` in
  its link. It rewrites that post's events with the current layout,
  putting back any you deleted and replacing any edits you made to them.
  Use it to test, or to redo an event.

## If it misbehaves

- **"Instagram isn't signed in":** run `--setup-instagram` again.
- **Instagram asks Chrome to confirm it's you**, or the account is
  challenged: sign in by hand with `--setup-instagram`, and leave the task
  off for a day or two. Instagram doesn't offer an API for saved posts, so
  Chrome reading it the way a person would is the only automatic way. That's
  why it opens few pages, slowly.
- **Nothing found in a post that has a show:** the details may be on a later
  carousel slide, which isn't read. Add the event by hand.
- **"Claude Code isn't installed"** or **"Claude Code failed"**: run `claude`
  in Command Prompt to check it's signed in. If the subscription's usage
  limit was reached, the posts are retried on the next run.
- **"The flyer for '…' wasn't clear"** in the log: Claude wasn't sure of
  the date, venue or acts. Check that event against the post.
- **Wrong year or time:** fix the event by hand. It won't be changed back.
- **Page layout changes:** if Instagram changes its pages, finding posts
  (`instagram.py`) is the part likely to break. The log says which post
  failed.
