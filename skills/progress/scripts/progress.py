#!/usr/bin/env python3
"""Manage a project's task plan, evidence, and progress snapshots."""

import argparse
from pathlib import Path
import sys

from progress_model import STATES, ProgressError, apply_plan, estimate, parse_plan, require, summarize, update_task
from progress_report import render
from progress_store import Store, json_text, parse_json, read_json


def positive_version(argument):
    value = int(argument)
    if value < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return value


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--root", type=Path, default=Path.cwd(), help="project directory (default: current directory)")
    commands = cli.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="initialize an untracked project from a plan")
    init.add_argument("--plan", type=Path, required=True, help="path to a plan JSON file")

    replan = commands.add_parser("replan", help="apply a replacement plan, retaining unchanged task evidence")
    replan.add_argument("--plan", type=Path, required=True, help="path to the full replacement plan JSON file")
    replan.add_argument("--expect-revision", type=positive_version, required=True)

    set_status = commands.add_parser("set", help="replace one task's status and evidence snapshot")
    set_status.add_argument("task_id")
    set_status.add_argument("state", choices=STATES)
    set_status.add_argument("--expect-version", type=positive_version, required=True, help="current task version from status --json")
    set_status.add_argument("--implementation", action="append", default=[], help="implementation evidence (repeatable)")
    set_status.add_argument("--checks", type=Path, help="JSON file containing current acceptance checks")
    set_status.add_argument("--note", help="status note or concrete blocker")

    status = commands.add_parser("status", help="read a current progress snapshot without writing")
    status.add_argument("--json", action="store_true", help="include tracker data and metrics as JSON")
    commands.add_parser("estimate", help="calculate implementation progress from a JSON assessment on stdin")
    commands.add_parser("report", help="save the current snapshot to .progress/report.md")
    commands.add_parser("validate", help="validate the existing tracker")
    return cli


def show_status(store, json_output):
    tracker = store.read(required=False)
    metrics, next_action = summarize(tracker)
    if json_output:
        return json_text({"tracker": tracker, "metrics": metrics, "next_action": next_action})
    return render(tracker, metrics, next_action)


def run(args):
    if args.command == "estimate":
        return json_text(estimate(parse_json(sys.stdin.buffer.read().decode("utf-8"), "assessment from stdin")))
    store = Store(args.root)
    if args.command == "status":
        return show_status(store, args.json)
    if args.command == "validate":
        tracker = store.read()
        return f"Valid tracker at revision {tracker['revision']}.\n"
    if args.command == "init":
        plan = parse_plan(read_json(args.plan))
        with store.locked(create=True):
            require(not store.path("tasks.json").exists(), "tracker already exists. Use replan to change scope.")
            path = store.write(apply_plan(plan))
        return f"Initialized {path} at revision 1.\n"
    if args.command == "report":
        with store.locked():
            tracker = store.read()
            metrics, next_action = summarize(tracker)
            path = store.write_report(render(tracker, metrics, next_action))
        return f"Wrote {path} at revision {tracker['revision']}.\n"

    if args.command == "replan":
        plan = parse_plan(read_json(args.plan))
        with store.locked():
            tracker = store.read()
            require(tracker["revision"] == args.expect_revision,
                    f"tracker revision is {tracker['revision']}, expected {args.expect_revision}. Reread status before retrying.")
            result = apply_plan(plan, tracker)
            if result is not tracker:
                store.write(result)
        return f"Plan at revision {result['revision']}.\n"

    checks = read_json(args.checks) if args.checks is not None else []
    with store.locked():
        tracker = store.read()
        result = update_task(tracker, args.task_id, args.expect_version, args.state, args.implementation, checks, args.note)
        if result is not tracker:
            store.write(result)
    return f"{args.task_id} recorded as {args.state} at revision {result['revision']}.\n"


def main():
    args = parser().parse_args()
    try:
        sys.stdout.write(run(args))
    except (ProgressError, OSError, RuntimeError, UnicodeError) as error:
        print(f"progress: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
