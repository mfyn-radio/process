# Working on the MFYN PC

Some work can only happen on the MFYN PC: rendering the Processing sketches,
running the automations, reading their logs and checking the scheduled task.
Claude does this itself through a **Remote Control** session on the PC, so
you don't copy commands into a terminal.

## Where things live

| What | Where | Master? |
|---|---|---|
| Code, docs and sketches | GitHub, `mfyn-radio/process` | **Yes.** Every change goes through a pull request |
| The repo on the PC | `C:\Users\admin\mfyn-process`, a git clone on `main` | No: updated with `git pull` |
| Always-available sketches | `H:\My Drive\MFYN_Processing` | No: a copy of the repo's `processing\`, made by `scripts\sync_sketches.cmd` |
| Processing 4 | `C:\Program Files\Processing\Processing.exe` (4.5.6) | |
| Finished output | the `MFYN_` folders in `H:\My Drive` (`MFYN_Posts`, `MFYN_Stories`, `MFYN_Show_Archive`…) | **Yes.** These are the final files |
| Logs | `%APPDATA%\mfyn-intake\` | |

The git clone stays on `C:`, outside Google Drive, because Drive sync can
break a `.git` folder. Claude may use any `MFYN_` folder in `H:\My Drive`.

## How a change flows

1. **Edit in the repo.** A cloud session or a PC session changes the code,
   docs or a sketch on a branch, then opens a pull request.
2. **Try it on the PC.** A PC session checks out that branch in
   `C:\Users\admin\mfyn-process`, renders or runs it, looks at the result,
   and pushes any fixes to the same branch.
3. **You merge** the pull request on GitHub.
4. **Update the PC.** In `C:\Users\admin\mfyn-process`: `git checkout main`,
   `git pull --ff-only`, then `scripts\sync_sketches.cmd` if a sketch changed.

A PC session starts with `git status`. If there are local changes that aren't
on GitHub, it stops and asks before doing anything else, so nothing on the PC
is lost or kept only there.

Never edit the sketches in `MFYN_Processing`: the next sync overwrites them.

## Rendering a sketch by hand

Processing isn't on `PATH`, so use the full path. This renders without opening
a window, in about 15 seconds:

```
"C:\Program Files\Processing\Processing.exe" cli --sketch="C:\Users\admin\mfyn-process\processing\MFYN_Archive" --run number=3 "date=5 November 2026"
```

Warnings that the display isn't available (AWT) are harmless. Each sketch's
README lists its options, including `input=` and `output=`. Point `output=`
at an `MFYN_` folder on H: for a final file. Without it, the sketch writes to
its own `output\` folder in the repo, which git ignores.

## Starting a Remote Control session

`H:\My Drive` is shared for Remote Control on the PC. A Claude thread that
needs the PC asks to start a session there, and you approve it once on the
card. The session can then work in `C:\Users\admin\mfyn-process` too.
If the PC isn't listed, open the Claude desktop app and check that Remote
Control is on for `H:\My Drive`.
