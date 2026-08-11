---
name: worktree-safety
description: Use when work must distinguish a linked worktree from the primary worktree and enforce explicit confirmation before writing in the primary checkout.
---

# Worktree safety

## Trigger

- Use at the start of repo work when the current checkout may be a primary repo or a linked worktree.
- Use before any write, commit, branch move, generator run, or cleanup command.
- Use whenever a repo policy requires special handling for the main checkout.

## Inputs

- Current working directory.
- `git rev-parse --show-toplevel`, `--absolute-git-dir` and `--git-common-dir` output, if available.
- Repo policy and any session-start gate state available outside the repo.
- Explicit user approval if work in the primary checkout is allowed.

## Definitions

- **Primary worktree:** the main checkout listed by Git, usually the path without `.git/worktrees/...` backing.
- **Linked worktree:** an additional checkout listed by Git whose `.git` file points into `.git/worktrees/...`.
- **`MAIN_WORKTREE_OK`:** the exact standalone user prompt line that grants primary-worktree use for the current session. It is not an environment variable and must not be synthesized, paraphrased, or set by a launcher or hook.
- **Session gate marker:** a session-scoped approval record stored outside the repo after the user has provided the exact `MAIN_WORKTREE_OK` prompt line.

## Workflow

1. Resolve repository root, absolute Git directory and common Git directory with read-only `git rev-parse` calls.
2. Classify `git dir == common dir` as primary and different directories as linked. Do not infer this from branch names.
3. Classify the session as:
   - `linked`: normal guarded work may proceed.
   - `primary-approved`: primary worktree, and a session gate marker exists because the user already answered with the exact `MAIN_WORKTREE_OK` line.
   - `primary-blocked`: primary worktree, no valid session gate marker.
   - `unknown`: detection failed; use the same explicit-confirmation gate as primary.
4. In `linked`, local tools may proceed normally.
5. In `primary-blocked`, ask at session start and block all local tools until the user responds.
6. Treat the primary worktree as approved only after the user sends the exact standalone line `MAIN_WORKTREE_OK`; then let the hook store the session gate marker outside the repo.
7. In `unknown`, fail closed. Explain that topology could not be proven and require the same exact standalone `MAIN_WORKTREE_OK` line before local tools may run for this session.
8. If no hook exists, fall back to repo policy or AGENTS guidance, but still require the exact standalone `MAIN_WORKTREE_OK` line before local tools run in the primary worktree.

## Stop / Approval Rules

- Never infer approval from branch name, detached HEAD state, or "probably safe" context.
- Never treat `MAIN_WORKTREE_OK` as an environment variable, config value, or hook-generated token.
- Never set `MAIN_WORKTREE_OK` implicitly inside task logic.
- In `unknown`, fail closed until topology is resolved or the user explicitly accepts the risk for this session with the exact standalone line.
- Stop all local tool use, not just writes, in `primary-blocked` or `unknown`.

## Checks

- Current path and primary path are known or explicitly unknown.
- The session mode is classified before any local tool use.
- Approval source is recorded when primary work is allowed.
- Fallback behavior is safe if Git or hooks are unavailable.

## Output

```text
## Worktree status
- current path:
- primary path:
- mode: linked / primary-approved / primary-blocked / unknown

## Gate decision
- local tools allowed:
- approval source: exact prompt line / session gate marker / none

## Next safe step
- ...
```
