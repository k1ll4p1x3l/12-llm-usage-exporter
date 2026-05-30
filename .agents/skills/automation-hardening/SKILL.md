---
name: automation-hardening
description: Use for CI/CD, GitHub Actions, scheduled scripts, idempotent workflows, safety gates, secrets, logging, and failure handling.
---

# Automation hardening

## Steps

1. Define trigger, inputs, outputs, permissions, secrets, and failure modes.
2. Ensure idempotency: running twice should not corrupt state.
3. Add dry-run or validation mode where possible.
4. Use least privilege for tokens and CI permissions.
5. Avoid unbounded loops, broad file globs, and destructive defaults.
6. Add logs that explain what happened without leaking secrets.
7. Include rollback or manual recovery instructions for non-trivial automation.

## Output

```text
## Workflow
...

## Guardrails
...

## Validation
...

## Rollback / Recovery
...
```
