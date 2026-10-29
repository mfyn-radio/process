"""The issue forms, the Labels workflow and CLAUDE.md all name the same labels.

If one changes without the others, the Claude task form would apply a label
that doesn't exist, or CLAUDE.md would tell Claude to look for one nothing
creates.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FORMS = ROOT / ".github" / "ISSUE_TEMPLATE"


def workflow_labels():
    """Labels the Labels workflow creates (`gh label create NAME ...`)."""
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "labels.yml").read_text(encoding="utf-8"))
    script = "\n".join(step.get("run", "") for step in workflow["jobs"]["labels"]["steps"])
    return set(re.findall(r"gh label create (\S+)", script))


def test_claude_task_form_is_well_formed():
    form = yaml.safe_load((FORMS / "claude-task.yml").read_text(encoding="utf-8"))
    assert form["name"] == "Claude task"
    assert form["labels"] == ["claude-task"]
    fields = {item["id"]: item for item in form["body"] if "id" in item}
    assert {"goal", "done", "where", "constraints", "verify"} <= set(fields)
    # Without these Claude can't tell what "finished" means.
    assert fields["goal"]["validations"]["required"]
    assert fields["done"]["validations"]["required"]


def test_every_label_the_forms_apply_is_created_by_the_labels_workflow():
    applied = set()
    for path in FORMS.glob("*.yml"):
        applied |= set(yaml.safe_load(path.read_text(encoding="utf-8")).get("labels") or [])
    assert applied, "no form applies a label"
    assert applied <= workflow_labels()


def test_blank_issues_stay_on_so_general_issues_are_the_default():
    config = yaml.safe_load((FORMS / "config.yml").read_text(encoding="utf-8"))
    assert config["blank_issues_enabled"] is True


def test_claude_md_names_every_label_the_workflow_creates():
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    labels = workflow_labels()
    assert labels == {"claude-task", "needs-human"}
    for label in labels:
        assert f"`{label}`" in text
