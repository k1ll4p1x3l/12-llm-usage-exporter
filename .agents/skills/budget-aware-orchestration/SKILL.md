---
name: budget-aware-orchestration
description: Use for large, expensive, or multi-agent tasks where token usage, fan-out, and checkpoint timing need explicit control.
---

# Budget-aware orchestration

## Trigger

- Use when the task is long-running, likely to touch many files, or may require several tools or agents.
- Use when usage limits, time limits, or model cost matter.

## Inputs

- User goal and urgency.
- `docs/TASK_LOG.md` or equivalent checkpoint, if present.
- Budget or usage hints from the user or environment.
- Scope size and risk level.

## Workflow

1. Classify the task into `normal`, `conserve`, `low`, or `critical` budget mode.
2. Choose the lightest viable exploration path first.
3. Reuse existing maps, logs, and checkpoints instead of rereading large context.
4. Scale concurrency only when the work truly splits cleanly.
5. Before fan-out, assign non-overlapping responsibility/path ownership and name
   a single primary integrator. Default maximum is four parallel subagents.
6. Do not allow recursive delegation unless the user explicitly requested it.
7. Rejoin through a factual ledger: result, evidence, changed paths, tests,
   unresolved risks, and accept/revise/discard decision.
8. Retry the same failed action at most twice. A retry must change hypothesis,
   input, or method; stop after two rejoin cycles without new evidence.
9. Checkpoint after each milestone with changed files, checks, risks, and next safe step.
10. In `critical`, stop after stabilizing state and writing a resume prompt.

## Stop / Approval Rules

- Do not spend heavy-model or parallel budget on avoidable broad scans.
- Do not start a new risky branch of work in `low` or `critical`.
- Stop if validation would require a large new branch of work with unclear payoff.
- Stop a loop that repeats the same action or review without new evidence.

## Checks

- Budget mode is explicit.
- Chosen fan-out matches the budget mode.
- There is a checkpoint plan before deep implementation.
- Resume information exists before stopping.
- Every delegated result has a rejoin decision owned by the primary agent.

## Output

```text
## Budget mode
...

## Routing plan
- ...

## Checkpoints
- ...

## Stop / resume condition
- ...
```
