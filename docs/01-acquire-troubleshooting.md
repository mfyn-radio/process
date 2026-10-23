# Step 1: troubleshooting

Problems with the [Acquire step](01-acquire.md), and what to do about them.
Run every command in Command Prompt **from the repo folder**:

```
cd %USERPROFILE%\mfyn-process
```

## First, look at the log

```
type %APPDATA%\mfyn-intake\acquire.log
```

- Each run starts with `N purchase email(s) to check`.
- Each album ends with `added '…'`, or an `ERROR … failed; will retry next run`
  followed by the details.
- Chrome's own messages (`DevTools listening…`, `PHONE_REGISTRATION_ERROR`,
  `update_service_dialer`…) are harmless noise.

Selenium errors can include the album's download link. The log stays on the
PC. The link only gets that album and expires.

## Common problems

### `No module named 'intake'`

The command was run outside the repo folder. `cd %USERPROFILE%\mfyn-process`
first. The scheduled task does this by itself.

### `'py' is not recognized`

On the MFYN PC, Python is `python`, not `py`.

### `unrecognized arguments: --setup` (or another new option)

The code on the PC is older than the docs. Update it:

```
git pull
python -m pip install -r requirements.txt
```

If it's still missing, the change isn't on `main` yet: check that its pull
request is merged.

### `Not signed in to Gmail yet` or `invalid_grant`

The Gmail token is missing or no longer valid. This happens if:

- the mfyn@ password changed,
- access was removed at <https://myaccount.google.com/permissions>
  (the app is listed as **mfyn-library-agent**),
- it went unused for 6 months.

Sign in again:

```
python -m intake.acquire --setup <client JSON>
```

The client JSON is
`client_secret_648160844206-jhea8g49optdpf94bqet5grgbf64915g.apps.googleusercontent.com.json`.
A copy is kept in `%APPDATA%\mfyn-intake\client_secret.json`. Sign in as
**mfyn@**.

### `Library folder … not found`

`H:\My Drive\MFYN_Library` isn't there. Is Google Drive for desktop running and
signed in as mfyn@? Is it still mapped to `H:`?

### Chrome opens but nothing downloads

- **Don't click in the Chrome window** while the job runs.
- `ElementClickInterceptedException` means something on the page covered the
  download link. The job clicks through JavaScript to avoid this, so if it
  comes back, Bandcamp has changed its page.
- `the download link never appeared` is followed by a list of the page's
  buttons. Paste it to Claude to adjust the code.
- `no format menu on the download page` usually means a pre-order or an
  unavailable item. It's retried next run.

### "Client Challenge" in an error

Bandcamp's bot protection blocked the request. Chrome normally gets through.
If it's blocked consistently, see the fallback in
[decisions](01-acquire-decisions.md#run-on-the-mfyn-pc-in-a-real-chrome-window-chosen).

### An album didn't arrive

1. Check the receipt email's labels in Gmail:
   - `MFYN/Downloaded`: it was added. Check Drive sync.
   - `MFYN/Excluded`: it was skipped on purpose.
   - neither: it hasn't been handled yet, or failed. Check the log.
2. Was it bought before 2026-10-23? Those need a backlog run.
3. Is it a pre-order? It waits for the release date.
4. Re-run just that email:
   `python -m intake.acquire --message-id <id>`. Ask Claude for the ID.

### A `.partial - …` folder in the library

A run was interrupted. The next run for that album replaces it. It's safe to
delete by hand.

## The scheduled task

| To | Run |
|---|---|
| Run it now | `schtasks /Run /TN "MFYN Acquire"` |
| See its status and last run | `schtasks /Query /TN "MFYN Acquire" /V /FO LIST` |
| Pause it | `schtasks /Change /TN "MFYN Acquire" /DISABLE` |
| Resume it | `schtasks /Change /TN "MFYN Acquire" /ENABLE` |
| Remove it | `schtasks /Delete /TN "MFYN Acquire"` |

It only runs while you're signed in to Windows, because Chrome needs your
desktop.
