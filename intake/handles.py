"""Confirming Instagram handles in the MFYN Artists sheet (step 3).

For each artist and label in an episode whose handle isn't settled yet, show
the suggestion and ask: Enter confirms it, a typed @handle replaces it, and
"-" records that they have no Instagram.
"""
import re

from . import catalog

SETTLED = {catalog.CONFIRMED.casefold(), catalog.NO_INSTAGRAM.casefold()}
VALID = re.compile(r"^@?[A-Za-z0-9._]{1,30}$")


def answer_to_change(answer, current):
    """The cells to write for an answer, or None to ask again."""
    answer = answer.strip()
    if answer == "":
        if not current:
            return None  # nothing to confirm; type a handle or "-"
        return {"Status": catalog.CONFIRMED}
    if answer == "-":
        return {"Instagram": "", "Status": catalog.NO_INSTAGRAM}
    if VALID.match(answer):
        return {"Instagram": "@" + answer.lstrip("@"), "Status": catalog.CONFIRMED}
    return None


def confirm(table, names, kind, ask=input, say=print):
    """Ask about every name in `names` whose row isn't settled. `table` is the
    Artists or Labels tab; `kind` is "artist" or "label"."""
    key = table.key[0]
    for name in names:
        index, row = table.find({key: name})
        if row is None:
            table.upsert({key: name})
            index, row = table.find({key: name})
        if row.get("Status", "").strip().casefold() in SETTLED:
            continue
        current = row.get("Instagram", "").strip()
        status = row.get("Status", "").strip() or "no status"
        say(f"\n{kind.capitalize()}: {name}")
        say(f"  Instagram: {current or '(none)'}  [{status}]")
        for link in (row.get("Website", ""), row.get("Other links", ""), row.get("Bandcamp page", "")):
            for line in filter(None, (link or "").splitlines()):
                say(f"  link: {line}")
        prompt = "  Enter = confirm, type @handle to change, - = no Instagram: " if current \
            else "  Type @handle, or - = no Instagram: "
        while True:
            change = answer_to_change(ask(prompt), current)
            if change is not None:
                break
            say("  Please type an Instagram handle like @name, or -.")
        table.set(index, change)
