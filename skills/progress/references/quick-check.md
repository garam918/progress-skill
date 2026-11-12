# Read-only implementation estimate

## Choose a denominator

- Use an explicitly requested milestone or subproject when available. If a valid tracker covers that scope, keep its task IDs and weights. Review current behavior against its criteria, including previously completed entries. Use the tracker for the plan, and the current checkout for implementation claims.
- Without a usable tracker, look for a current release plan, spec, README requirements, acceptance tests, and interfaces, in roughly that order. Use tests, explicit stubs, or TODOs attached to required behavior to identify gaps. Keep the estimate bounded to the closest defensible scope and describe that scope in the answer. When the project has several phases, use the current one if there is evidence identifying it.
- Create a short list of independently observable outcomes that covers the chosen scope. Use equal weights for similarly sized outcomes. Use relative weights such as `1`, `2`, and `3` only when complexity is materially different and visible in the requirements. Choose weights before classifying completion. Include intended, unfinished work so the current file inventory does not define completion by itself.
- If only working features are visible and no intended scope can be inferred, report that the implementation percentage cannot be determined from the available scope. An absent tracker on its own is no obstacle to an estimate.

## Assess current behavior

- Trace each counted outcome from its normal entry point through the relevant code, configuration, and dependencies. A stub, partial path, isolated helper, or unchecked claim contributes zero until the full required behavior is supported. An existing test file may help identify intended behavior. Read available test results when relevant and use them only for the corresponding code state.
- Keep incomplete and unconfirmed work in the denominator. Say when unconfirmed work makes the number a conservative estimate. A source inspection can support implementation even when the tests have yet to be run.
- Inspect relevant files and existing artifacts without modifying the workspace. Use Git changes only to locate relevant code and identify stale tracker evidence.

## Calculate

Supply one UTF-8 JSON object on stdin. Each outcome has a unique lowercase hyphenated ID, a positive integer weight, a boolean `implemented`, and a short `evidence` string for that judgment. The command returns the scope, implemented weight, total weight, and percentage as JSON.

```bash
python3 -B "$skill_dir/scripts/progress.py" estimate <<'JSON'
{
  "scope": "README MVP",
  "tasks": [
    {"id": "save-note", "weight": 3, "implemented": true, "evidence": "The editor save action calls the configured persistent store."},
    {"id": "list-notes", "weight": 2, "implemented": false, "evidence": "The README requires saved notes on the home screen, which renders a placeholder."}
  ]
}
JSON
```

In this example the result is `60.0%`. The calculation is `floor(1000 × implemented weight / total weight) / 10`. An empty scope has no percentage. Use the same calculation if Python is unavailable. Omit a trailing `.0` in the brief user-facing reply if appropriate.
