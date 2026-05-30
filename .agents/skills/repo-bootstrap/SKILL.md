---
name: repo-bootstrap
description: Use when a repository is new, poorly documented, or should receive a generic AI-ready project profile, runbook, task log, and safe automation baseline.
---

# Repo bootstrap

Use this skill before major work in an unknown repository.

## Steps

1. Read file tree and obvious project files only: `README`, package manifests, CI files, Docker/Compose, Makefile/Taskfile, pyproject, go.mod, Cargo.toml, AGENTS.md.
2. Infer stack and commands conservatively.
3. Create or propose `PROJECT_PROFILE.md` using `templates/project/PROJECT_PROFILE.template.md`.
4. Create `docs/TASK_LOG.md` if absent.
5. Create `docs/RUNBOOK.md` only if repo has service/deploy/ops characteristics.
6. Do not overwrite existing docs. Merge or create `.draft.md`.

## Output

```text
## Repo-Profil
...

## Angelegte Dateien
- ...

## Vermutete Befehle
- test:
- lint:
- build:

## Unsicherheiten
- ...
```
