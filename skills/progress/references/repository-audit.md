# Repository audit and evidence

## Build a baseline

1. Locate the requested project root and look for an existing tracker. Start with the user's scope, accepted specifications, issue or milestone plans, and README. Use manifests, entry points, tests, and project configuration to map where the features live and how they run. Prefer requirements backed by project sources. Label assumptions and open questions in the draft.
2. If Git is available, inspect `git status --short`, relevant `git diff -- <paths>` and `git diff --cached -- <paths>`, and `git log -n 10 --oneline -- <paths>`. Use changes and history to locate implementation and tests. Read the code and normal entry point before making a completion claim. Projects without Git can be audited through files and runnable checks.
3. Draft small tasks that each deliver a behavior the user can recognize. Assign stable IDs and positive integer weights based on relative effort, such as `1`, `2`, `3`, `5`, `8`. Keep the order useful for the next-action suggestion and record dependencies that affect sequencing. Phrase acceptance criteria as observable outcomes with stable criterion IDs. Include important error cases or integration paths where the requirement calls for them.
4. Initialize only when the user asks to create a tracker. If the request includes an evidence-backed baseline, inspect the existing behavior against each task's criteria before recording its status. Where the audit cannot establish a stronger state, leave the task at `todo` or record observed partial work as `in_progress`.

## Record what you observed

| State | When to use it |
| --- | --- |
| `todo` | Work awaits action or there is insufficient evidence to assess it. |
| `in_progress` | The work is underway or only part of the planned behavior is present. |
| `implemented` | The behavior is present through the normal entry point. Cite the relevant paths, symbols or commit and what you observed. A check can still be pending or failing. |
| `verified` | The implementation is present and a current check passed for each acceptance criterion. |
| `blocked` | A specific dependency, permission, environment, or decision prevents work. Include the next step needed to remove the blocker. |

- For implementation, trace the relevant behavior from the entry point through its dependencies. A filename, a passing unrelated test, a commit message, or a checked box alone is insufficient. A test failure that shows a required implementation is missing warrants `in_progress` or `blocked` according to the actual situation.
- For an automated check, use the repository's documented command and record the actual relevant result. For a manual check, record the steps, environment if material, and observed result. Record the commit or worktree context when it affects reproducibility. Use the check kinds in [checks.json](../assets/checks.json). Read [tracker format](tracker-format.md) for the input rules.
- If a criterion needs several observations, report `passed` only once all required observations succeed. Use the check kind that best describes the recorded validation and describe any supplementary checks in `detail`. Leave an unrun criterion absent. Base the result on a current run or reproducible observation.
- When relevant code or configuration changes, reassess affected tasks. Replace stale evidence with current observations. If verification fails while implementation is still present, record `implemented` with the failed check. If the implementation has regressed, revise that state too. Revisit dependent tasks when their evidence relies on the changed behavior.
- Record only the paths, commands, and results needed for the claim. Omit secrets and unnecessary log dumps.
