# MFYN Intake and Production Process

Code and docs for Music for Your Neighbors (MFYN). Start at
[`docs/README.md`](docs/README.md) for the pipeline, and
[`docs/session-log.md`](docs/session-log.md) for where the project stands.

- Tests: `python -m pytest`.
- Changes go through pull requests. Don't merge one unless asked.
- The code runs on the MFYN Windows PC. Docs use Windows paths.

## Issues are the single list of open work

Open work, deferred decisions and open questions live in GitHub Issues, not in
the docs. Don't add new to-do lists or "open questions" sections to the docs.
Link to the issue instead.

### Suggest issues as we work

While working, watch for things that should be tracked, such as:

- a follow-up or problem outside the current task;
- a decision or open question we put off;
- something the docs call "not built yet" that has no issue;
- a bug you notice.

When you spot one:

1. **Search the open issues first.** If one already covers it, suggest a
   comment on it instead of a new issue.
2. **Suggest it, don't create it.** Show the proposed title and a short body,
   and say whether it is a new issue or a **sub-issue** of an existing one.
   Use a sub-issue when it is a piece of a bigger issue (for example, a child
   automation of Create the show). Ask the user to confirm or deny.
3. **Only after they confirm**, create it (and link it as a sub-issue if that
   was the suggestion). If they deny, drop it and don't raise it again in
   that session.

Never create, edit, comment on or close an issue without the user's
confirmation. Don't write a bare `@name` in an issue or comment, since it
notifies that person.

When work finishes an issue, say so and suggest closing it. Don't close it
yourself.
