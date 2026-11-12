"""Validation and calculations for the project-progress file format."""

from datetime import datetime, timezone
from graphlib import CycleError, TopologicalSorter
import re


SCHEMA_VERSION = 1
STATES = ("todo", "in_progress", "implemented", "verified", "blocked")
COMPLETE = ("implemented", "verified")
PLAN_FIELDS = {"project", "scope", "tasks"}
TASK_FIELDS = {"id", "title", "weight", "criteria"}
STATUS_FIELDS = {"state", "version", "implementation", "checks", "note"}
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class ProgressError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ProgressError(message)


def text_value(value, label):
    require(isinstance(value, str) and value.strip(), f"{label} must be non-empty text")
    require(not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff]", value),
            f"{label} contains invalid text characters")


def positive_integer(value, label):
    require(type(value) is int and value > 0, f"{label} must be a positive integer")


def fields(value, required, label, optional=()):
    require(isinstance(value, dict), f"{label} must be an object")
    missing = required - value.keys()
    extra = value.keys() - required - set(optional)
    if missing or extra:
        raise ProgressError(f"{label} fields are invalid (missing: {sorted(missing)}, extra: {sorted(extra)})")


def identifier(value, label):
    require(isinstance(value, str) and ID.fullmatch(value),
            f"{label} must use lowercase letters, digits, and single hyphens")


def validate_definition(task, label):
    identifier(task["id"], f"{label}.id")
    text_value(task["title"], f"{label}.title")
    positive_integer(task["weight"], f"{label}.weight")
    criteria = task["criteria"]
    require(isinstance(criteria, dict) and criteria, f"{label}.criteria must be a non-empty object")
    for key, description in criteria.items():
        identifier(key, f"{label} criterion ID")
        text_value(description, f"{label}.criteria.{key}")
    dependencies = task["depends_on"]
    require(isinstance(dependencies, list), f"{label}.depends_on must be a list")
    for dependency in dependencies:
        identifier(dependency, f"{label} dependency ID")
    require(len(set(dependencies)) == len(dependencies), f"{label} has duplicate dependencies")


def validate_graph(tasks):
    graph = {task["id"]: task["depends_on"] for task in tasks}
    require(len(graph) == len(tasks), "task IDs must be unique")
    for task_id, dependencies in graph.items():
        missing = set(dependencies) - graph.keys()
        require(not missing, f"task {task_id} references unknown dependencies: {', '.join(sorted(missing))}")
    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as error:
        raise ProgressError(f"dependency cycle: {' -> '.join(error.args[1])}") from error


def parse_plan(plan):
    fields(plan, PLAN_FIELDS, "plan")
    text_value(plan["project"], "plan.project")
    text_value(plan["scope"], "plan.scope")
    require(isinstance(plan["tasks"], list), "plan.tasks must be a list")
    for index, task in enumerate(plan["tasks"], 1):
        label = f"plan task #{index}"
        fields(task, TASK_FIELDS, label, optional={"depends_on"})
        task.setdefault("depends_on", [])
        validate_definition(task, label)
    validate_graph(plan["tasks"])
    return plan


def validate_status(task):
    label = f"task {task['id']}"
    state = task["state"]
    require(state in STATES, f"{label} has an invalid state")
    if task["note"] is not None:
        text_value(task["note"], f"{label}.note")
    require(state != "blocked" or task["note"], f"{label} needs a blocker note")

    implementation = task["implementation"]
    require(isinstance(implementation, list), f"{label}.implementation must be a list")
    for item in implementation:
        text_value(item, f"{label} implementation evidence")
    require(state not in COMPLETE or implementation, f"{label} needs implementation evidence")

    checks = task["checks"]
    require(isinstance(checks, list), f"{label}.checks must be a list")
    results = {}
    for check in checks:
        fields(check, {"criterion", "kind", "result", "detail"}, f"{label} check")
        criterion = check["criterion"]
        identifier(criterion, f"{label} check criterion ID")
        require(criterion in task["criteria"], f"{label} has an unknown criterion: {criterion}")
        require(criterion not in results, f"{label} has duplicate checks for {criterion}")
        require(check["kind"] in ("automated", "manual"), f"{label} check kind must be automated or manual")
        require(check["result"] in ("passed", "failed"), f"{label} check result must be passed or failed")
        text_value(check["detail"], f"{label} check detail")
        results[criterion] = check["result"]
    require(state != "todo" or not (implementation or checks), f"{label} todo state cannot carry evidence")
    if state == "verified":
        outstanding = [key for key in task["criteria"] if results.get(key) != "passed"]
        require(not outstanding, f"{label} needs passing checks for: {', '.join(outstanding)}")


def validate_tracker(tracker):
    require(isinstance(tracker, dict), "tracker must be an object")
    version = tracker.get("schema_version")
    require(type(version) is int and version == SCHEMA_VERSION, f"unsupported tracker schema_version: {version!r}")
    fields(tracker, PLAN_FIELDS | {"schema_version", "revision", "updated_at"}, "tracker")
    positive_integer(tracker["revision"], "tracker.revision")
    text_value(tracker["project"], "tracker.project")
    text_value(tracker["scope"], "tracker.scope")
    text_value(tracker["updated_at"], "tracker.updated_at")
    try:
        datetime.strptime(tracker["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise ProgressError("tracker.updated_at must be a UTC timestamp") from error
    require(isinstance(tracker["tasks"], list), "tracker.tasks must be a list")
    for index, task in enumerate(tracker["tasks"], 1):
        label = f"tracker task #{index}"
        fields(task, TASK_FIELDS | STATUS_FIELDS | {"depends_on"}, label)
        validate_definition(task, label)
        positive_integer(task["version"], f"{label}.version")
        require(task["version"] <= tracker["revision"], f"{label}.version exceeds the tracker revision")
        validate_status(task)
    validate_graph(tracker["tasks"])
    return tracker


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply_plan(plan, previous=None):
    revision = 1 if previous is None else previous["revision"] + 1
    old_tasks = {} if previous is None else {task["id"]: task for task in previous["tasks"]}
    tasks = []
    for definition in plan["tasks"]:
        prior = old_tasks.get(definition["id"])
        same_requirements = (prior is not None
                             and prior["criteria"] == definition["criteria"]
                             and set(prior["depends_on"]) == set(definition["depends_on"]))
        if same_requirements:
            task = {**prior, **definition}
            if task != prior:
                task["version"] = revision
        else:
            task = {**definition, "state": "todo", "version": revision,
                    "implementation": [], "checks": [], "note": None}
        tasks.append(task)
    revised_plan = {**plan, "tasks": tasks}
    if previous and all(revised_plan[key] == previous[key] for key in PLAN_FIELDS):
        return previous
    return {**revised_plan, "schema_version": SCHEMA_VERSION, "revision": revision, "updated_at": now()}


def update_task(tracker, task_id, expected, state, implementation, checks, note):
    for index, task in enumerate(tracker["tasks"]):
        if task["id"] == task_id:
            break
    else:
        raise ProgressError(f"unknown task ID: {task_id}")
    require(task["version"] == expected,
            f"task {task_id} version is {task['version']}, expected {expected}. Reread status before retrying.")
    changed = {**task, "state": state, "implementation": implementation, "checks": checks, "note": note}
    validate_status(changed)
    if changed == task:
        return tracker
    revision = tracker["revision"] + 1
    changed["version"] = revision
    tracker["tasks"][index] = changed
    return {**tracker, "revision": revision, "updated_at": now()}


def weighted_percent(weight, total):
    return (weight * 1000 // total) / 10 if total else None


def estimate(assessment):
    fields(assessment, {"scope", "tasks"}, "assessment")
    text_value(assessment["scope"], "assessment.scope")
    tasks = assessment["tasks"]
    require(isinstance(tasks, list), "assessment.tasks must be a list")
    seen = set()
    total = implemented = 0
    for index, task in enumerate(tasks, 1):
        label = f"assessment task #{index}"
        fields(task, {"id", "weight", "implemented", "evidence"}, label)
        task_id = task["id"]
        identifier(task_id, f"{label}.id")
        require(task_id not in seen, f"duplicate assessment task ID: {task_id}")
        seen.add(task_id)
        positive_integer(task["weight"], f"{label}.weight")
        require(type(task["implemented"]) is bool, f"{label}.implemented must be a boolean")
        text_value(task["evidence"], f"{label}.evidence")
        total += task["weight"]
        if task["implemented"]:
            implemented += task["weight"]
    return {
        "scope": assessment["scope"],
        "implemented_weight": implemented,
        "total_weight": total,
        "implementation_percent": weighted_percent(implemented, total),
    }


def summarize(tracker):
    tasks = tracker["tasks"] if tracker else []
    total = sum(task["weight"] for task in tasks)
    implemented = sum(task["weight"] for task in tasks if task["state"] in COMPLETE)
    verified = sum(task["weight"] for task in tasks if task["state"] == "verified")

    metrics = {
        "total_weight": total,
        "implemented_weight": implemented,
        "verified_weight": verified,
        "implementation_percent": weighted_percent(implemented, total),
        "verification_percent": weighted_percent(verified, total),
    }
    states = {task["id"]: task["state"] for task in tasks}
    for state, action in (("in_progress", "Continue"), ("implemented", "Verify"), ("todo", "Start"), ("blocked", "Unblock")):
        for task in tasks:
            if task["state"] != state:
                continue
            if state == "todo" and any(states[key] not in COMPLETE for key in task["depends_on"]):
                continue
            return metrics, f"{action} {task['id']}"
    return metrics, None
