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

- Branching:
- Commit style:
- Documentation update rule:
- Preferred task log path:
