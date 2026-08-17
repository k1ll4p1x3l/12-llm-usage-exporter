# REPO_POLICY

Status: local working copy
Managed-by-source: no

This file is copied once into a consumer repo and then maintained there. It is
intended to capture local policy that should not be silently overwritten by
future template updates.

## Scope

- Repos, folders, and systems this policy applies to.

## Worktree safety

- Preferred location for normal work: linked worktree
- Primary worktree blocks all local tools until explicit confirmation: yes / no
- Exact standalone user line required for approval: `MAIN_WORKTREE_OK`
- Hook stores only a session approval marker outside the repo after that exact line: yes / no
- If worktree detection fails, fail closed: yes / no

## Git task lifecycle

- Default/protected branches:
- Standard task-branch prefix: `codex/`
- One independent write task per topic branch: yes / no
- Parallel write tasks use separate linked worktrees: yes / no
- Repo implementation approval includes local task-branch creation: yes / no
- Repo implementation approval includes coherent milestone commits: yes / no
- Commit required before human gate, push, PR, task switch, handoff and completion: yes / no
- Push/PR may be authorized together at intake: yes / no
- Ready-for-review requires its own approval: yes / no
- Merge requires a separate explicit approval with fresh PR/SHA/CI readback: yes / no
- Force-push and direct default-branch push forbidden: yes / no
- Branch/worktree cleanup requires explicit approval: yes / no

## Approval gates

- Live production changes require explicit approval: yes / no
- External service changes require explicit approval: yes / no
- Destructive cleanup requires explicit approval: yes / no
- New dependencies require explicit approval: yes / no

## Public / private boundary

- Public-safe paths:
- Private-only paths:
- Sensitive examples that must stay out of mirrors:

## Validation expectations

- Minimum checks before handoff:
- Additional checks before release:
- Cases where a checkpoint is acceptable instead of full completion:

## Local conventions

- Branching exceptions:
- Commit style:
- Documentation update rule:
- Preferred task log path:
