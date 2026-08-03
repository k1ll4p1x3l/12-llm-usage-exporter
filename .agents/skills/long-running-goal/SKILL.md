---
name: long-running-goal
description: Use when work should proceed in milestones with durable checkpoints, resumable state, and explicit done criteria.
---

# Long-running goal

## Trigger

- Use for multi-hour or multi-milestone work.
- Use when interruption is likely and resume quality matters.

## Inputs

- End goal and done criteria.
- Current task log or checkpoint file, if present.
- Validation commands and known risks.
- Optional `.agent-state/run-contract.json`, checkpoint, evidence ledger, and
  action envelope for an explicitly contracted run.

## Workflow

1. Freeze one objective and explicit non-goals before decomposition.
2. Break the goal into reviewable milestones with a single in-progress milestone.
3. Define validation, required evidence classes, retry limits, and stop conditions
   for each milestone.
4. For opt-in contracted runs, keep the state machine and run identifier stable.
5. Update the task log after each milestone with factual progress only.
6. Before compaction, update `.agent-state/checkpoint.json`; after compaction,
   re-read the contract, task log, checkpoint, scope, and next safe step before acting.
7. Record what changed, what was checked, what remains risky, and what to do next.
8. Produce a resume prompt that lets the next run continue without re-deriving context.

## Stop / Approval Rules

- Stop if the next milestone would require new approval, new scope, or unsafe assumptions.
- Stop if validation is unavailable and the result cannot be responsibly claimed complete.
- Do not leave the state between milestones undocumented.
- Do not weaken the scope, evidence requirements, or approval boundary just to
  pass a hook. If the contract is wrong, stop and repair it transparently.

## Checks

- Every milestone has a done signal or an explicit blocker.
- Task log and resume prompt are in sync.
- The next safe step is smaller than the remaining whole project.
- A checkpoint repeats the unchanged objective and distinguishes repo evidence,
  observed runtime evidence, user-provided evidence, and inference.

## Output

```text
## Milestone
...

## Done
- ...

## Checks
- ...

## Risks
- ...

## Resume prompt
...
```
