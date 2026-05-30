---
name: budget-aware-orchestration
description: Use for long or costly Codex tasks where model selection, subagent fan-out, checkpoints, and usage-limit conservation matter.
---

# Budget-aware orchestration

Use this skill when a task may run long, spawn subagents, touch many files, or consume noticeable usage.

## Inputs

- User goal.
- Current `.codex/state/budget_status.json`, if present.
- `docs/TASK_LOG.md`, if present.
- Any explicit usage/limit status from the user or Codex UI.

## Steps

1. Determine budget mode:
   - `normal`: >50% remaining or unknown.
   - `conserve`: 20–50% remaining.
   - `low`: 5–20% remaining.
   - `critical`: <5% remaining or explicit limit warning.
2. Select fan-out:
   - `normal`: up to 3–4 subagents.
   - `conserve`: up to 2 subagents.
   - `low`: no parallelism unless a blocker requires it.
   - `critical`: stop after checkpoint.
3. Prefer read-only mapping before implementation when scope is unclear.
4. Reuse summaries and maps. Do not make multiple agents read the same large files unless they need different perspectives.
5. At each milestone, record a checkpoint with goal, done items, changed files, checks, risks, and next safe step.

## Output

Return:

```text
## Budgetmodus
...

## Routingentscheidung
- Agent -> Aufgabe -> Warum dieses Modell

## Checkpoint-Plan
- ...

## Stop-/Resume-Bedingung
- ...
```
