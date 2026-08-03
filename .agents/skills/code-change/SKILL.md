---
name: code-change
description: Use for bounded code or config changes that should stay minimal, reviewable, tested, and free of unauthorized side effects.
---

# Code change

## Trigger

- Use for bugfixes, small features, refactors, config changes, or tests in a known repository.
- Use when a task should end in a minimal diff plus validation.

## Inputs

- Goal, scope, and acceptance criteria.
- Relevant files, tests, and conventions.
- Allowed write surface and forbidden side effects.

## Workflow

1. Map the smallest relevant code path before editing.
2. Change only what is required to meet the goal.
3. Preserve existing style, patterns, and ownership boundaries.
4. Update tests or docs when behavior or operator guidance changes.
5. Run the narrowest meaningful checks first, then broader checks if warranted.
6. Summarize behavior changes, validation, and residual risks.

## Stop / Approval Rules

- Stop before new dependencies, schema/data migrations, auth changes, secret handling, or live deployments unless explicitly approved.
- Stop if the fix grows beyond the promised scope or crosses another owner's area.
- Do not "clean up" unrelated code opportunistically.

## Checks

- Diff is minimal and attributable to the goal.
- Behavior change is explicit.
- Relevant tests, lint, or syntax checks ran or a concrete reason is given.
- Rollback path is obvious from the diff.

## Output

```text
## Goal
...

## Changed files
- ...

## Behavior changed
- ...

## Checks
- command: result

## Risks / follow-up
- ...
```
