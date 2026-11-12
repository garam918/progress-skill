"""Render a status snapshot using the bundled Markdown template."""

from html import escape
from pathlib import Path
import re
from string import Template


TEMPLATE = Path(__file__).resolve().parents[1] / "assets" / "report.md"


def markdown(value):
    line = escape(" ".join(value.split()), quote=False)
    return re.sub(r"([\\`*_[\]|~])", r"\\\1", line)


def task_lines(tasks, states):
    lines = []
    for task in tasks:
        if task["state"] not in states:
            continue
        line = f"- `{task['id']}` {markdown(task['title'])} ({task['weight']})"
        if task["state"] in ("implemented", "verified"):
            line += f" · `{task['state']}`"
        if task["depends_on"]:
            line += " · Depends on " + ", ".join(f"`{key}`" for key in task["depends_on"])
        if task["note"]:
            line += f" · {markdown(task['note'])}"
        lines.append(line)
    return "\n".join(lines) or "None."


def evidence_lines(tasks):
    lines = []
    for task in tasks:
        if not (task["implementation"] or task["checks"]):
            continue
        lines.append(f"- `{task['id']}`")
        lines.extend(f"  - Implementation evidence — {markdown(item)}" for item in task["implementation"])
        for check in task["checks"]:
            key = check["criterion"]
            lines.append(f"  - `{key}` · {check['kind']} · {check['result']} — {markdown(check['detail'])}")
    return "\n".join(lines) or "None recorded."


def render(tracker, metrics, next_action):
    def progress(metric):
        value = metrics[f"{metric}_percent"]
        return "Unknown" if value is None else f"{value:.1f}%"

    tasks = tracker["tasks"] if tracker else []
    snapshot = f"Revision {tracker['revision']} · Updated {tracker['updated_at']}" if tracker else "Tracker uninitialized."
    next_action = next_action or ("All tracked work is verified." if tasks else "Define the task scope.")
    total = metrics["total_weight"]
    return Template(TEMPLATE.read_text(encoding="utf-8")).substitute(
        project=markdown(tracker["project"]) if tracker else "Project",
        scope=markdown(tracker["scope"]) if tracker else "Unknown",
        snapshot=snapshot,
        implementation=progress("implementation"),
        verification=progress("verification"),
        implemented_weight=f"{metrics['implemented_weight']} / {total}" if total else "—",
        verified_weight=f"{metrics['verified_weight']} / {total}" if total else "—",
        current=task_lines(tasks, ("in_progress",)),
        completed=task_lines(tasks, ("implemented", "verified")),
        blocked=task_lines(tasks, ("blocked",)),
        remaining=task_lines(tasks, ("todo",)),
        evidence=evidence_lines(tasks),
        next_action=markdown(next_action),
    )
