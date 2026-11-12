import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "progress.py"


def task(task_id, weight=1, **changes):
    return {
        "id": task_id,
        "title": f"Deliver {task_id}",
        "weight": weight,
        "criteria": {"works": "The feature works through its normal entry point."},
        **changes,
    }


class ProgressTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="progress-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.state = self.root / ".progress" / "tasks.json"
        self.report = self.state.with_name("report.md")

    def command(self, *args):
        return [sys.executable, "-B", str(SCRIPT), "--root", str(self.root), *map(str, args)]

    def run_cli(self, *args, success=True, input_text=None):
        result = subprocess.run(self.command(*args), input=input_text, capture_output=True, text=True, timeout=10)
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue(result.stderr)
            self.assertNotIn("Traceback", result.stderr)
        return result.stdout

    def input_file(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def plan(self, *tasks):
        return self.input_file("plan.json", {"project": "메모 프로젝트", "scope": "MVP", "tasks": tasks})

    def init(self, *tasks):
        self.run_cli("init", "--plan", self.plan(*tasks))

    def status(self):
        return json.loads(self.run_cli("status", "--json"))

    def set_task(self, task_id, state, *args, version=1, success=True):
        return self.run_cli("set", task_id, state, "--expect-version", version, *args, success=success)

    def checks(self, *checks):
        return self.input_file("checks.json", [
            {"criterion": criterion, "kind": kind, "result": result, "detail": detail}
            for criterion, kind, result, detail in checks
        ])

    def estimate(self, *tasks, success=True):
        payload = json.dumps({"scope": "현재 CLI MVP", "tasks": tasks}, ensure_ascii=False)
        return self.run_cli("estimate", input_text=payload, success=success)

    def test_estimate_calculates_progress_without_creating_project_files(self):
        result = json.loads(self.estimate(
            {"id": "save", "weight": 3, "implemented": True, "evidence": "cli.py routes save to storage"},
            {"id": "list", "weight": 2, "implemented": False, "evidence": "README requires listing; route is a stub"},
        ))
        self.assertEqual(result, {"scope": "현재 CLI MVP", "implemented_weight": 3,
                                  "total_weight": 5, "implementation_percent": 60.0})
        self.assertEqual(list(self.root.iterdir()), [])

    def test_estimate_uses_current_evidence_instead_of_a_stale_tracker_state(self):
        self.init(task("save"))
        self.set_task("save", "implemented", "--implementation", "Old save handler")
        before = self.state.read_bytes()
        result = json.loads(self.estimate(
            {"id": "save", "weight": 1, "implemented": False, "evidence": "Current save handler is a stub"},
        ))
        self.assertEqual(result["implementation_percent"], 0.0)
        self.assertEqual(self.state.read_bytes(), before)
        self.assertFalse(self.report.exists())

    def test_empty_estimate_returns_unknown_instead_of_zero(self):
        self.assertIsNone(json.loads(self.estimate())["implementation_percent"])

    def test_estimate_rejects_unsupported_status_claims(self):
        item = {"id": "save", "weight": 1, "implemented": True, "evidence": "cli.py has a save handler"}
        for changes in ({"evidence": "  "}, {"weight": 0}, {"implemented": "true"}):
            with self.subTest(changes=changes):
                self.estimate({**item, **changes}, success=False)
        self.estimate(item, item, success=False)
        self.assertFalse(self.state.parent.exists())

    def test_status_without_a_plan_is_unknown_and_read_only(self):
        status = self.status()
        self.assertIsNone(status["tracker"])
        self.assertIsNone(status["metrics"]["implementation_percent"])
        self.assertIsNone(status["metrics"]["verification_percent"])
        self.assertFalse(self.state.parent.exists())

    def test_empty_plan_is_unknown_and_existing_plan_cannot_be_overwritten_by_init(self):
        self.init()
        self.assertIsNone(self.status()["metrics"]["implementation_percent"])
        before = self.state.read_bytes()
        self.run_cli("init", "--plan", self.plan(task("new")), success=False)
        self.assertEqual(self.state.read_bytes(), before)

    def test_init_starts_existing_code_at_todo_without_agent_evidence(self):
        (self.root / "app.py").write_text("print('implemented')\n", encoding="utf-8")
        self.init(task("feature"))
        tracker = self.status()["tracker"]
        self.assertEqual(tracker["revision"], 1)
        self.assertEqual(tracker["tasks"][0]["state"], "todo")
        self.assertEqual(tracker["tasks"][0]["implementation"], [])

    def test_weighted_rates_distinguish_implemented_verified_and_blocked(self):
        self.init(task("a", 3), task("b", 2), task("c", 5))
        self.set_task("a", "verified", "--implementation", "app.py handles feature A",
                      "--checks", self.checks(("works", "automated", "passed", "python -m unittest: 1 passed")))
        self.set_task("b", "implemented", "--implementation", "worker.py runs feature B")
        self.set_task("c", "blocked", "--note", "Waiting for the test account")
        self.assertEqual(self.status()["metrics"], {
            "total_weight": 10, "implemented_weight": 5, "verified_weight": 3,
            "implementation_percent": 50.0, "verification_percent": 30.0,
        })

    def test_a_weighted_rate_below_completion_never_displays_100(self):
        self.init(task("large", 10000), task("small"))
        self.set_task("large", "implemented", "--implementation", "app.py contains the feature")
        self.assertEqual(self.status()["metrics"]["implementation_percent"], 99.9)

    def test_completion_rejects_missing_evidence_or_a_failing_acceptance_criterion(self):
        self.init(task("a", criteria={"works": "Runs", "handles-error": "Handles errors"}))
        before = self.state.read_bytes()
        self.set_task("a", "implemented", success=False)
        self.set_task("a", "verified", "--implementation", "app.py handles inputs", "--checks",
                      self.checks(("works", "manual", "passed", "Opened and ran")), success=False)
        self.set_task("a", "verified", "--implementation", "app.py handles inputs", "--checks",
                      self.checks(("works", "manual", "passed", "Opened and ran"),
                                  ("handles-error", "automated", "failed", "Expected 400, got 500")), success=False)
        self.assertEqual(self.state.read_bytes(), before)

    def test_regression_replaces_stale_pass_and_preserves_implementation_rate(self):
        self.init(task("a"))
        self.set_task("a", "verified", "--implementation", "app.py handles inputs", "--checks",
                      self.checks(("works", "manual", "passed", "Opened and ran")))
        self.set_task("a", "implemented", "--implementation", "app.py still handles normal inputs", "--checks",
                      self.checks(("works", "automated", "failed", "Empty input test fails")), version=2)
        status = self.status()
        self.assertEqual(status["metrics"]["implementation_percent"], 100.0)
        self.assertEqual(status["metrics"]["verification_percent"], 0.0)
        self.assertEqual(status["tracker"]["tasks"][0]["checks"][0]["result"], "failed")

    def test_retry_with_stale_task_version_cannot_overwrite_newer_status(self):
        self.init(task("a"))
        self.set_task("a", "in_progress")
        self.set_task("a", "todo", success=False)
        self.assertEqual(self.status()["tracker"]["tasks"][0]["state"], "in_progress")

    def test_independent_processes_keep_all_concurrent_task_updates(self):
        ids = [f"job-{index}" for index in range(8)]
        self.init(*(task(task_id) for task_id in ids))
        processes = [subprocess.Popen(self.command("set", task_id, "in_progress", "--expect-version", 1),
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                     for task_id in ids]
        for process in processes:
            _, errors = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, errors)
        tracker = self.status()["tracker"]
        self.assertEqual(tracker["revision"], 9)
        self.assertEqual([item["state"] for item in tracker["tasks"]], ["in_progress"] * 8)

    def test_replan_keeps_evidence_for_weight_change_and_resets_changed_criteria(self):
        self.init(task("a"), task("b"))
        for task_id in ("a", "b"):
            self.set_task(task_id, "implemented", "--implementation", f"{task_id}.py behavior inspected")
        self.run_cli("replan", "--plan", self.plan(task("a", 5), task("b", criteria={"works": "New behavior"}),
                                                   task("c")), "--expect-revision", 3)
        tracker = self.status()["tracker"]
        a, b, c = tracker["tasks"]
        self.assertEqual((a["id"], a["weight"], a["state"]), ("a", 5, "implemented"))
        self.assertEqual((b["state"], b["implementation"], b["checks"]), ("todo", [], []))
        self.assertEqual(c["state"], "todo")
        self.assertEqual(tracker["revision"], 4)

    def test_replan_cannot_lose_a_concurrent_change(self):
        self.init(task("a"))
        self.set_task("a", "in_progress")
        before = self.state.read_bytes()
        self.run_cli("replan", "--plan", self.plan(task("b")), "--expect-revision", 1, success=False)
        self.assertEqual(self.state.read_bytes(), before)

    def test_init_rejects_bad_scope_before_writing(self):
        plans = [
            (task("a", 0),),
            (task("a", True),),
            (task("a"), task("a")),
            (task("a", depends_on=["unknown"]),),
            (task("a", depends_on=["b"]), task("b", depends_on=["a"])),
            (task("a", state="verified"),),
        ]
        for tasks in plans:
            with self.subTest(tasks=tasks):
                self.run_cli("init", "--plan", self.plan(*tasks), success=False)
                self.assertFalse(self.state.exists())

    def test_invalid_or_unsupported_tracker_is_never_overwritten(self):
        self.init(task("a"))
        originals = ['{"schema_version":1,"schema_version":1}', '{"schema_version":99}', '{broken']
        for content in originals:
            with self.subTest(content=content):
                self.state.write_text(content, encoding="utf-8")
                self.run_cli("validate", success=False)
                self.set_task("a", "in_progress", success=False)
                self.assertEqual(self.state.read_text(encoding="utf-8"), content)

    def test_report_is_a_snapshot_with_evidence_blockers_and_next_action(self):
        self.init(task("a"), task("blocked"), task("downstream", depends_on=["blocked"]), task("ready"))
        self.set_task("a", "verified", "--implementation", "app.py exposes the operation", "--checks",
                      self.checks(("works", "manual", "passed", "Opened the real screen")))
        self.set_task("blocked", "blocked", "--note", "Sandbox account expired")
        stdout = self.run_cli("status")
        self.assertFalse(self.report.exists())
        self.run_cli("report")
        report = self.report.read_text(encoding="utf-8")
        self.assertEqual(report, stdout)
        for fragment in ("메모 프로젝트", "25.0%", "Sandbox account expired", "Opened the real screen", "manual",
                         "app.py exposes the operation", "Start ready", "Revision 3"):
            self.assertIn(fragment, report)
        self.run_cli("validate")

    def test_progress_dir_symlink_cannot_redirect_writes(self):
        target = self.root / "other"
        target.mkdir()
        os.symlink(target, self.state.parent)
        self.run_cli("init", "--plan", self.plan(task("a")), success=False)
        self.assertEqual(list(target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
