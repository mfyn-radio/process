# Run log

The automations write what they did to a Google Sheet, **MFYN Run Log**, in
mfyn@'s Drive. It is made on first use, like the MFYN Artists sheet. The status
page reads it, so you can see what ran without opening the logs on the MFYN PC.
Background: [#44](https://github.com/mfyn-radio/process/issues/44).

## Tabs

**Runs:** one row each time an automation finishes something, or fails at it.

| Column | What it holds |
|---|---|
| Time | When, on the MFYN PC's clock (`2026-11-21 08:05`) |
| Automation | Acquire, Make Reels, Album Story, Archive cover |
| About | The album folder, episode folder, or `(the run)` when the run stopped before it got to one |
| Result | `ok`, `failed` or `excluded` |
| Details | What it made, or the error |

**Last run:** one row per automation, overwritten every run: when it last ran,
whether it worked, and a short summary. Acquire runs hourly, so a time more
than an hour or two old here means the Task Scheduler task isn't running.

## What each automation logs

| Automation | A row in Runs when | Last run summary |
|---|---|---|
| Acquire | An album is added, was already in the library, a purchase is from an excluded seller, or a purchase fails | How many purchase emails it checked, and how many are waiting (pre-orders, not downloadable yet). Waiting purchases get no row, since they'd add one every hour |
| Make Reels | It finishes an episode: posts made, failed, captions written, and whether the archive cover was made | The same |
| Album Story | A Story is made, or Processing made no video | What it made |
| Archive cover (run on its own) | A cover is made | What it made |

Any run that ends with an error and hasn't logged a failed row gets one, with
the errors it logged, so "Drive for desktop isn't running" shows up too.

## When the sheet can't be reached

Logging never stops an automation. If the sheet can't be opened or written, a
warning goes to the automation's own log file and the run carries on. Dry runs
(`--dry-run`) and `--setup` aren't logged.

The log only starts from the day this was added. Older runs are only in the
log files on the PC.
