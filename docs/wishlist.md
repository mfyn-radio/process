# Wishlist

Your Bandcamp wishlist in a Google Sheet, with each release's tags and
location, so you can filter it by tag or place, also on your phone.

| | |
|---|---|
| **Trigger** | Task Scheduler task `MFYN Wishlist`, daily at 20:00, via `scripts\run_wishlist.cmd`, or by hand |
| **Input** | The public wishlist on [bandcamp.com/music_for_your_neighbors](https://bandcamp.com/music_for_your_neighbors/wishlist) |
| **Output** | The **MFYN Wishlist** Google Sheet in mfyn@'s Drive, tab `Wishlist` |
| **Runs on** | The MFYN PC, in Chrome, like [Acquire](01-acquire.md) |
| **Code** | [`intake/wishlist.py`](../intake/wishlist.py) |
| **Log** | `wishlist.log`, next to the other logs (see [troubleshooting](01-acquire-troubleshooting.md)) |

It uses no Airtable records or API calls: the wishlist changes too often, and
grows too fast, for the free plan.

## What it does

1. Open the wishlist on the fan page in Chrome and ask Bandcamp for all of
   it, the way the page's own "view all" button does.
2. Open the album page of each item it hasn't read before, a few seconds
   apart, and keep its tags and location in `%APPDATA%\mfyn-intake\wishlist.json`.
   Each page is read only once. A run reads at most 100 new pages, so a long
   wishlist is filled in over a few days (or run it with `--pages 500`).
3. Rewrite the `Wishlist` tab, newest first. Releases you've removed from the
   wishlist drop off.

The location is the one on the album page, under the name in the sidebar. For
a label release that's the label's location, not the artist's.

## The sheet

| Column | |
|---|---|
| Artist, Release | As the wishlist names them |
| Tags | The album page's tags, comma-separated |
| City, Country, Location | Split from the album page's location, like the [Locations](airtable.md) in the catalog |
| Wishlisted | The date you added it |
| Bandcamp link | The album page; tap it to open it in Bandcamp |
| Notes | **Yours.** What you type here stays with the release. Every other column is rewritten on each run |

### Filtering on your phone

In the Google Sheets app, tap the column letter, then **Create a filter**.
Tap the filter icon on **Country** (for example only Netherlands and Belgium),
or on **Tags** and use **Filter by condition**, **Text contains**, `post-punk`.
On the PC, **Data > Create a filter view** saves a filter, like "BeNe", that you
can pick again later.

## Running it by hand

```
cd C:\Users\admin\mfyn-process
python -m intake.wishlist             # read new pages, rewrite the sheet
python -m intake.wishlist --dry-run   # read only, don't write the sheet
python -m intake.wishlist --pages 500 # read the whole backlog in one go
```

`MFYN_BANDCAMP_FAN` (or `--fan`) points it at another fan page.

## If it goes wrong

| In the log | What to do |
|---|---|
| `no fan data on ...` | Bandcamp showed something other than the fan page, such as its "Client Challenge". Try again later |
| `The wishlist ... is empty, or hidden from visitors` | Check that your wishlist shows on your fan page when you are signed out of Bandcamp (for example in a private window) |
| `couldn't read <link>` | That page is tried again on the next run |
