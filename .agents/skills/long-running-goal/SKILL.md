---
name: long-running-goal
description: Use for goal-mode or multi-hour work: split into reviewable milestones, maintain TASK_LOG checkpoints, and produce resume prompts.
---

# Long-running goal protocol

## Rules

- Work in small, reviewable increments.
- Keep `docs/TASK_LOG.md` current.
- Never start a new risky branch of work when budget mode is `low` or `critical`.
- Each milestone must have a validation result or a clear reason why validation was impossible.

## Checkpoint format

```text
## Checkpoint YYYY-MM-DD HH:MM Europe/Berlin

### Ziel
...

### Erledigt
- ...

### Geänderte Dateien
- ...

### Tests / Checks
- ...

### Risiken / offene Punkte
- ...

### Nächster sicherer Schritt
- ...

### Resume-Prompt
...
```
