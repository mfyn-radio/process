# Airtable

The catalog the automations keep, **MFYN Catalog**, is an Airtable base on
the free plan, in mfyn@'s Airtable account. What's in it:
[the MFYN Catalog](01-acquire.md#the-mfyn-catalog). Background:
[#58](https://github.com/mfyn-radio/process/issues/58).

The **MFYN Run Log** stays a Google Sheet ([run log](run-log.md)): the status
page reads it there, and it grows every day.

## How the code reaches it

- `intake/airtable.py` gives each table the same `find`, `upsert`, `set` and
  `rows` as a Google Sheet tab (`intake/table.py`), so Acquire, the Event
  Calendar, Make Episode Content and the YouTube playlist read and write it
  as they did the sheet.
- Rows read as plain text, as in the sheet. A multi-select such as Tags reads
  as `a, b, c`.
- Linked-record fields (`Linked artists`, `Linked label`, `Linked episode`,
  `Linked artist`, `Linked release`, `Linked venue`, `Linked location`) are
  filled by name. A name is matched
  ignoring case and accents. Links only ever gain records, like tags, so
  links you make by hand stay. An event or playlist entry only links to an
  artist or release already in the base; it never makes one up. Venues and
  Locations are the exception: a new venue or place is added, so every
  event and artist can link to one ([Locations and Venues](01-acquire.md#locations-and-venues)).
- The same rule as the sheet: only empty fields are filled.
- **Renaming fields is safe.** Each run first reads the base's field list
  (1 call) and follows your renames: a field you turn into a link keeps its
  text in `<name>- text` (Venue became the link to Venues, with the text in
  "Venue- text"), and a link the code fills is found by the table it links
  to, whatever it's called. A date field with the old name (Added, Purchased,
  Release date, Date) takes the dates, written `2026-11-21`. A field that's
  gone, with no `- text` copy, is skipped and the run says so in its log.

## Free plan limits

| Limit | Free plan | What the code does |
|---|---|---|
| Records per base, all tables together | 1,000 | About 100 today. See [when the base fills up](#when-the-base-fills-up) |
| API calls per workspace per month | 1,000 | Reads only the tables a run uses (Artists, Releases and Labels when opened; the rest, such as Events, Venues and Locations, when first used), 100 records a call, and writes 10 records a call. Each run also reads the field list once. Expected use: about 350 a month |
| Calls in one run | (ours) 150, `MFYN_AIRTABLE_MAX_CALLS` | A run that reaches it stops using the base and carries on without it, as when the sheet couldn't be reached |
| Requests per second | 5 per base | The code waits a quarter of a second between calls, and 30 seconds if Airtable says it's too many |
| Revision history | 2 weeks | Export a table to CSV now and then if you want older history |

Source: [Airtable plans overview](https://support.airtable.com/articles/2277136852-airtable-plans-overview).
The paid Team plan lifts these but costs extra, so it's not used (`CLAUDE.md`).

## Setup on the MFYN PC

1. **Token.** In Airtable, Builder hub → Personal access tokens → create a
   token with the scopes `data.records:read`, `data.records:write`,
   `schema.bases:read` and `schema.bases:write`, with access to the workspace.
   Save it in `C:\Users\admin\mfyn-process\airtable_token.txt`. It's in
   `.gitignore`, so it's never committed. (`AIRTABLE_TOKEN` or
   `MFYN_AIRTABLE_TOKEN_FILE` can point elsewhere.)
2. **Base and tables.**

   ```
   python -m intake.airtable_setup --copy
   ```

   It finds the base named **MFYN Catalog**, adds any missing tables and
   fields (links last), saves the base's id in `%APPDATA%\mfyn-intake\airtable.json`,
   then copies the MFYN Artists sheet across. The token can't look up a
   workspace, so if there's no base yet, either make an empty one with that
   name in Airtable first, or pass `--workspace wsp…` (the id in the
   workspace's address). `--copy --dry-run` only counts the sheet's rows.
   Running it again is safe: it adds only what's missing.
3. A base made by hand comes with an empty **Table 1**. Delete it once the
   setup has run.

### What the copy does

- Artists, Labels, Releases, Events and (once there are some) Playlists rows
  are copied. The Tags tab isn't: the same tags are already on each release
  and artist, as multi-select fields.
- A release links to the artist its credit names, or, for a split or a
  collaboration (`A / B`, `A & B`, `A + B`…), to each part that's an artist
  in the base. A label release links to its label, and the label to those
  artists.
- Columns you added to the sheet by hand come along as text fields.
- The sheet is only read. It stays in mfyn@'s Drive as a backup.

## When the base fills up

At 1,000 records the free plan stops new records being added. The plan, not
built yet, is an **archive** base beside the active one:

- **Archive:** events whose date has passed, and episodes older than about
  six months with their playlist entries.
- **Keep active:** Artists, Labels, Releases, Venues and Locations. The automations look these
  up on every run, and they grow slowly.
- Links can't cross bases, so archived records keep their names as text.
  Both bases share the 1,000 API calls a month.

Details: [#58](https://github.com/mfyn-radio/process/issues/58#issuecomment-7061036843).

## Troubleshooting

| Message | What to do |
|---|---|
| `No Airtable token` | Save the token as in setup step 1. |
| `Airtable isn't set up on this PC yet` | Run `python -m intake.airtable_setup`. |
| `HTTP 401` or `HTTP 403` | The token is wrong, has expired, or lacks a scope or the workspace. Make a new one. |
| `HTTP 422 … UNKNOWN_FIELD_NAME` | A field was renamed while a run was going, or the token can't read the schema (`schema.bases:read`). Run again, or check the token's scopes. |
| `stopped after … Airtable calls` | The run used its budget. It carries on without the base; the next run fills in what was missed (`--artists`, `--fill-sheet`). |
| `HTTP 429` again and again | Over the monthly 1,000 calls. It resets on the 1st. |
