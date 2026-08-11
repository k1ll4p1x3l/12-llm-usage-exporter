---
name: approved-change-execution
description: Use after real human approval to execute a tightly bounded live change with preflight, dry-run or check-mode validation, abort rules, readback, and rollback.
---

# Approved change execution

## Trigger

- Use only after a human has approved a specific live change.
- Use when planning is complete and the next step is controlled execution.
- Use for narrow live actions against exact approved targets, not broad maintenance.

## Inputs

- Human approval reference.
- Exact action, target, and scope boundary.
- Preflight assumptions and success criteria.
- Dry-run, check-mode, or diff-mode path if the tool supports it.
- Abort criteria, post-change readback, and reviewed rollback procedure.

## Workflow

1. Confirm the approved action, exact targets, and explicit non-goals.
2. Run preflight checks and compare them to the approved assumptions.
3. Use dry-run, check mode, diff mode, or equivalent preview when supported.
4. Limit execution to exact hosts, services, objects, or inventories. Use explicit limits, tags, selectors, or single-target addressing.
5. Stop immediately if preflight or preview differs from what was approved.
6. Execute the minimum approved live action.
7. Perform independent post-change readback against the intended state.
8. If readback fails or signals are ambiguous, stop and apply the reviewed rollback or hand back for human decision.
9. Record what was executed, what was verified, and what remains unverified.

## Stop / Approval Rules

- Never treat a template, action envelope, or assistant summary as approval. Approval must come from a real human decision.
- Never widen scope from one target to many because the first step looked safe.
- Never continue after a failed preflight, failed preview, ambiguous validation, or unexpected side effect.
- Never run live changes without a rollback path that matches the approved scope.
- Never perform credential, permission, network-boundary, or secret changes unless they were explicitly approved as part of the exact action.

## Checks

- Human approval is specific and current.
- Targets are exact, not inferred.
- Preflight and preview matched the approved assumptions.
- Post-change readback independently confirms the intended result.
- Rollback is ready before execution starts.

## Output

```text
## Approved action
...

## Targets and limits
- ...

## Preflight / preview
- ...

## Execution result
- ...

## Readback
- ...

## Rollback status
- ...
```
