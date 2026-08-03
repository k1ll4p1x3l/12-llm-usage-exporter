---
name: automation-hardening
description: Use for CI, scripts, cron, agent workflows, and other automation that needs guardrails, idempotency, and safe failure behavior.
---

# Automation hardening

## Trigger

- Use for GitHub Actions, local scripts, cron jobs, setup flows, installers, or agentic automation.
- Use when repeated execution must be safe and observable.

## Inputs

- Trigger, inputs, outputs, and operator expectations.
- Permissions, tokens, secrets, and environment assumptions.
- Failure modes and rollback expectations.

## Workflow

1. Define trigger, inputs, outputs, and side effects.
2. Make re-runs safe: idempotent by default, or clearly refuse duplicate execution.
3. Add dry-run, validate-only, or preview behavior where feasible.
4. Minimize privileges, secrets, and file write scope.
5. Log what happened without leaking sensitive values.
6. Add timeout, retry, and loop guards for unattended execution.
7. Document rollback or manual recovery for non-trivial flows.

## Stop / Approval Rules

- Stop before enabling production deployment, destructive cleanup, or external integrations without approval.
- Stop if the automation cannot explain its own state transitions or recovery path.
- Do not hardcode secrets or assume network availability silently.

## Checks

- Trigger and side effects are explicit.
- Re-run behavior is safe.
- Permissions are least-privilege.
- Failure handling and rollback are documented.

## Output

```text
## Workflow
...

## Guardrails
- ...

## Validation
- ...

## Rollback / recovery
- ...
```
