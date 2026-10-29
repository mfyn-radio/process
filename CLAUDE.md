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
confirmation. Creating an issue or sub-issue always needs a yes first, with
no exceptions. (The one thing the `claude-task` label authorizes is working
that issue, below.) Don't write a bare `@name` in an issue or comment, since it
notifies that person.

When work finishes an issue, say so and suggest closing it. Don't close it
yourself.

When you suggest an issue, say which kind it is: a general issue (the
default, a free-form note for work or ideas) or a **Claude task** (below).

## Two kinds of issue

- **General issues** are the default: a work and ideas tracker. They are the
  user's. Don't work on one unless asked.
- **Claude tasks** are issues labelled `claude-task`, made from the "Claude
  task" issue form. They are yours to work on independently.

### Working Claude tasks

At the start of a session, list the open issues labelled `claude-task` that
aren't labelled `needs-human`. Tell the user which are ready. If the user
gave you something else to do, ask which comes first. Otherwise work them.

The `claude-task` label is the user's confirmation for that issue. For it,
and only it, you may comment on the issue, create a branch and open a pull
request without asking again.

1. Read the issue's Goal, Done when, Where it touches and Constraints.
2. Work on a branch from the latest `main`, one issue per branch.
3. Open a pull request that says `Closes #N`. Never merge it, and don't close
   the issue: the user reviews, merges and closes.
4. Say in the PR what you could not check. Anything that needs the MFYN PC
   (Bandcamp, Chrome, Processing, Google Drive) can't be run here.
5. If the issue is unclear, or a choice is the user's to make, don't guess.
   Comment on the issue with the question and add `needs-human`. The user
   removes `needs-human` when they've answered.

Staying inside the issue: don't widen it. If you find something else that
should be tracked, suggest it as above.

### When the user steps away

Always ask before creating an issue or sub-issue. Stepping away is no
exception.

- **If they say they're about to step away**, offer to hand the rest of the
  work to a Claude task: show the proposed title, body and parent (a
  sub-issue of the issue it belongs to, if any), and wait for their yes. Fill
  in the whole form from what we decided, so it makes sense without this
  conversation.
- **If they've already gone**, don't create anything. Carry on with the work
  already agreed on its branch, or work an existing `claude-task` issue as
  above. Keep a short list of any issues you'd suggest, and put it in your
  last message for them to confirm when they're back.
- Don't invent new scope while they're away.
