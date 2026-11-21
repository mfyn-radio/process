# Step 2b: Instagram copy

A caption for each video post. A sub-automation of [step 2, Create the show](02-create-show.md),
run during [step 2a, Make Episode Content](02a-make-episode-content.md), straight after the video posts.

| | |
|---|---|
| **Trigger** | Every **MFYN – Make Episode Content** run that makes ON AIR posts, after the posts. No double-click of its own |
| **Input** | Each video post's `.json` in `MFYN_Posts\<episode>`, plus fresh handles from the [MFYN Artists sheet](01-acquire.md#the-mfyn-artists-sheet) |
| **Output** | `Artist - Title.txt` next to each video post, ready to paste into Instagram |
| **Runs on** | The MFYN PC |
| **Code** | [`intake/captions.py`](../intake/captions.py) |
| **Next** | You review the video posts and captions, before the Publishing Process starts |

## The caption

```
Music worth paying for, follow to find and support an artist

Artist: @applied.communications
Song Title: donna deegan
Album: bites the big one

Label: @knifehits
Release Date: 12 September 2026

Air Date: 5 November 2026
```

- **Handles:** looked up again in the MFYN Artists sheet when the caption is
  made, in case one was corrected after the video post was made. Only `Confirmed` handles are
  tagged. Artists and labels marked `No Instagram`, or not confirmed yet, are
  credited by name.
- **Label:** a self-released album shows `Label: Self-released`.
- **Missing details:** a line with nothing to fill it (no album, no release
  date, no label known) is left out.
- **Without the sheet:** if it can't be opened, the handles saved in the
  `.json` are used.

The opening line is `OPENING` at the top of `intake/captions.py`; the rest of
the template is in `caption()` there.

## Editing and remaking

The `.txt` files are yours to edit before posting. A video post that already has a
caption is left alone, so your edits survive later runs.

To remake a caption, for example after correcting a handle in the sheet,
delete its `.txt` and double-click **MFYN – Make Episode Content** again. It skips the
video posts that already exist and writes the missing captions.

From Command Prompt, in the repo folder, captions can also be made on their own:

```
python -m intake.captions                  # the newest episode in MFYN_Posts
python -m intake.captions --episode NAME   # the episode whose folder name contains NAME
```
