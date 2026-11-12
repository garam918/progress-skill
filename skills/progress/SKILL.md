---
name: progress
description: Use when the entire user message is `progress` or when asked for the current project's implementation percentage. Inspect current code and intended scope, then return a brief weighted estimate. Works without a tracker.
---

# Progress

When the user types `progress` on its own or invokes this skill without arguments, give the current project's implementation percentage in one or two lines. Use the user's language. Resolve the project from the current workspace, preferring the Git root unless the user is working on a specific subproject.

## Quick check

1. Read [quick-check.md](references/quick-check.md) and inspect the project read-only. Use a valid `.progress/tasks.json` for scope and weights if available. Review the current code even when a tracker exists. Otherwise use project requirements, README, tests, and entry points to infer the intended scope.
2. Feed the evidence-backed assessment to `python3 -B <skill-dir>/scripts/progress.py estimate` as JSON on stdin. Resolve `<skill-dir>` from this file. If Python is unavailable, apply the formula in the reference. Only count work that you can trace through its normal entry point.
3. Reply with the implementation percentage, scope, and completed/total weight. Label inferred scope or weights as an estimate. If useful, name one important remaining item. If a credible scope cannot be established, say the percentage is unknown and give the short reason.

Example in Korean:

> **구현률 약 60%** · README의 MVP 기준, 3/5 가중치.
>
> 남은 핵심 작업은 저장한 메모 목록 표시입니다.

Quick checks are read-only. Inspect source and existing test artifacts. Save a report, change the tracker, or run project tests when the user specifically asks for those actions.

## Explicit tracker requests

Use [tracker-format.md](references/tracker-format.md) for initialization, status changes, replan, verification, and saving a detailed report. Derive acceptance criteria and check evidence using [repository-audit.md](references/repository-audit.md). Make tracker changes through the bundled CLI. On a version conflict, reread the tracker and reassess before retrying.
