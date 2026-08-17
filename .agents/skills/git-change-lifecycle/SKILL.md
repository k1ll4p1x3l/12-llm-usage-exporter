---
name: git-change-lifecycle
description: Use for any repository-writing task and for branch creation, milestone commits, pushes, pull requests, review fixes, merge readiness, merges, or branch/worktree cleanup so each change stays isolated, recoverable, reviewable, and bounded by the correct human gates.
---

# Git change lifecycle

## Classify the task

- Use no new branch for read-only analysis or advice.
- Use one linked worktree and one topic branch for each independent write task.
- Continue the same task or existing pull request on its existing branch.
- Move materially unrelated work to a new branch; use another linked worktree
  when work proceeds in parallel.

## Start the write task

1. Read the effective repository rules and inspect worktree topology, current
   branch, default branch, dirty state, upstream, and ahead/behind state.
2. Stop on unaccounted user changes or an unknown Git topology.
3. Never mutate a detached HEAD or a default/protected branch. A
   `MAIN_WORKTREE_OK` approval does not waive this branch boundary.
4. Reuse the existing task/PR branch when it matches the scope. Otherwise
   create `codex/<short-purpose>` from the intended base. Do not switch away
   from a dirty worktree.
5. Treat explicit authorization for repository implementation as including
   local task-branch creation and local milestone commits unless the user
   excludes either. It does not authorize remote writes or merge.

## Commit coherent milestones

1. Stage explicit paths in semantic groups; never use `git add .` or
   `git add -A` as a general shortcut.
2. Run the narrowest meaningful checks and then the repository-required gates.
3. Commit each coherent, reviewable milestone before a new human gate, push,
   pull request, task switch, handoff, interruption, or completion.
4. Use the repository's commit convention. Keep code, tests, and documentation
   together when separating them would create a knowingly broken commit.
5. Never create empty, secret-bearing, unrelated, or knowingly broken commits
   merely to satisfy cadence. If no repository diff exists, report that a
   commit is not applicable.

## Publish and review

- Push and pull-request creation/update are remote actions; obtain their exact
  human authorization early and bundled where safe. Announce ready-for-review,
  merge, and cleanup early, but request each separate gate only with current
  readback when it becomes actionable.
- Once an exact task branch and scope are authorized for push/PR updates, push
  later scope-valid milestone commits without repeated prompts and read back
  the remote SHA each time.
- Prefer a Draft PR for the first fully reviewable remote state. Read back its
  base, head SHA, diff, CI, security checks, reviews, and unresolved threads.
- Never force-push or directly push to the default branch unless a higher-level
  instruction explicitly establishes a different protected workflow.

## Merge and cleanup

1. Treat merge as a separate explicit human gate. Name PR, target branch,
   final head SHA, checks, reviews, unresolved threads, and merge method.
2. Re-read the same facts immediately before the approved merge and abort on
   drift.
3. Verify the resulting default-branch SHA and checks after merge.
4. Recommend remote-branch deletion and worktree cleanup, but perform them only
   after separate authorization and a clean-state readback.

## Stop rules

- Stop if branch/task ownership is ambiguous, the worktree contains unrelated
  changes, the base moved incompatibly, validation contradicts readiness, or
  the requested remote action exceeds current authorization.
- A local commit is recoverability, not proof of correctness or operational
  authority. A push is not merge approval; a PR is not merge approval.
- Project-local hooks are guardrails and may be absent or untrusted. Preserve
  these rules as the textual fallback and rely on remote rulesets for the
  default-branch boundary.

## Required handoff

```text
Git status
- Worktree / branch:
- Last local commit:
- Remote state:
- Pull request:
- CI / review:
- Merge readiness:
- Recommended next Git action:
- Required authorization:
```
