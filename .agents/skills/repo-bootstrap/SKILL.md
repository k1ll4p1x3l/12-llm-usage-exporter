---
name: repo-bootstrap
description: Use when a repo is new, sparse, or being re-founded and needs local policy, profile, and task-log scaffolding without taking ownership of consumer-local files forever.
---

# Repo bootstrap

## Trigger

- Use when the repository is new, mostly empty, or missing project policy and operating context.
- Use when a local consumer repo should receive starter templates and then own them independently.

## Inputs

- File tree and obvious project markers.
- Existing `README`, manifests, CI, Docker, build files, and repo policy.
- Consumer template source path after installation: `.agent-core/templates/`.

## Workflow

1. Read only the obvious project signals first.
2. Infer stack, commands, and risks conservatively.
3. Create or propose copy-once local files from `.agent-core/templates/` into:
   - `PROJECT_PROFILE.md`
   - `docs/REPO_POLICY.md`
   - `docs/TASK_LOG.md`
4. Use consumer templates as copy-once starters, not as permanently managed mirrors.
5. If private local context is needed, point to `private/references/private/README.md` as a placeholder only.
6. Merge with existing docs instead of overwriting them where practical.

## Stop / Approval Rules

- Stop before inventing commands, environments, or deployment facts without evidence.
- Stop before copying private source material into public-safe destinations.
- Do not force future synchronization of consumer-local files unless the user asked for managed generation.

## Checks

- Bootstrapped files are clearly editable and locally owned after creation.
- Unknown commands are marked as unknown, not guessed.
- Public/private boundaries are explicit.

## Output

```text
## Repo profile
...

## Bootstrapped files
- ...

## Inferred commands
- test:
- lint:
- build:

## Unknowns
- ...
```
