# MFYN Processing sketches

Three sketches, set up and run the same way (Processing 4; the video post and Story sketches also need ffmpeg):

- `MFYN_VideoPost_OnAir/`: one track in, one white dot-matrix radio video post out, 1080×1920 with the player centred (discovery, automated).
- `MFYN_Story_Album/`: one album folder in, one media-player Story out (featured album, posted with the Bandcamp link; automated by Make Album Story).

- `MFYN_Archive/`: one episode number and date in, one archive cover out (2160×2160 PNG, a paper colour per episode). The brand anchor: kept independent of the other two so its look stays fixed.

Each folder has its own README with setup, inputs and settings.
Open a sketch by double-clicking its main `.pde` file (MFYN_VideoPost_OnAir.pde / MFYN_Story_Album.pde / MFYN_Archive.pde).

## Naming

Sketches are named `MFYN_ComponentType_ContentName`, for example
`MFYN_VideoPost_OnAir`. Stories leave out "Post": `MFYN_Story_Album`.

## Where to edit

This folder in the repo is the master copy. `H:\My Drive\MFYN_Processing` is
a copy that `scripts\sync_sketches.cmd` refreshes after each `git pull`, so
the sketches are always available in Drive. Don't edit that copy: the next
sync overwrites it. See [working on the PC](../docs/working-on-the-pc.md).
