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
  human authorization early and bundled where safe. If the user wants one
  longer autonomous run, prepare the bounded lifecycle envelope below before
  asking for one approval that names every intended stage.
- Once an exact task branch and scope are authorized for push/PR updates, push
  later scope-valid milestone commits without repeated prompts and read back
  the remote SHA each time.
- Prefer a Draft PR for the first fully reviewable remote state. Read back its
  base, head SHA, diff, CI, security checks, reviews, and unresolved threads.
- Never force-push or directly push to the default branch unless a higher-level
  instruction explicitly establishes a different protected workflow.

## Merge and cleanup

1. Treat merge as a separate technical stage. It needs a current explicit
   human gate unless that exact stage is already included in a still-valid
   lifecycle approval envelope.
2. Immediately before merge, re-read PR identity, target branch and approved
   base SHA, the run-produced final head SHA, complete diff, checks, reviews,
   unresolved threads, mergeability, and merge method. Abort on drift.
3. Verify the resulting default-branch SHA and checks after merge.
4. Remote-branch deletion, linked-worktree removal, and local-branch deletion
   are distinct cleanup stages. Perform only the exact approved subset after a
   successful merge readback and a clean-state preflight.

## Bounded lifecycle approval envelope

Use this opt-in path only for one repository task and one pull request:

1. Activate or reuse a matching run contract. Copy
   `.agent-core/templates/GIT_LIFECYCLE_APPROVAL_ENVELOPE.json` to the sole
   active path `.agent-state/action-envelope.json`; do not invent a parallel
   approval file.
2. Before asking for approval, fill the exact repository slug, absolute linked
   worktree, Git remote, base branch and current full remote base SHA, topic
   branch, repo-relative path allowlist, allowed stages, PR title/body policy and exact label,
   milestone and reviewer values, merge method, cleanup mode, abort conditions,
   and finite expiry. Maximum validity is 168 hours; shorter is preferable.
3. Ask the human once to approve that exact envelope. Record an exact quote or
   stable conversation reference and timestamp only after the real approval.
   The file cannot create or widen authority.
4. Execute listed stages in order. Each stage keeps its own preflight and
   readback. Normal Codex permission prompts and repository rules still apply.
5. Bind the final, initially unknown head only as `run-produced-tip`: every
   commit must have been produced in this run, remain inside the path allowlist,
   and have passed the declared validation. Stage only explicit in-scope paths,
   require that the named remote URL resolves to the approved repo slug, push
   only the exact topic branch there, and stop on any unexpected commit or
   remote base drift.
6. Before ready and again immediately before merge, require exact PR/base/head,
   complete diff, all required and reported checks green, the declared approval
   count, no changes-requested review, no unresolved thread, and clean
   mergeability. Create the PR as Draft with explicit matching `--repo`,
   `--base`, `--head`, exact title and explicit body input; metadata must stay
   inside the exact label/milestone/reviewer sets. Use the exact `--repo` on
   every PR mutation and merge only with the declared method plus
   `--match-head-commit <run-produced-tip>`. After merge, prove the resulting
   default-branch SHA before any cleanup.
7. Expiry; repository, branch, base, head, path, or PR drift; a negative check
   or review; ambiguous readback; or an out-of-envelope action invalidates all
   remaining stages. Diagnose first and obtain a new bounded approval rather
   than editing the old envelope.

The envelope never covers secrets or credentials, permissions or repository
settings, release/tag/workflow dispatch, destructive data work, live or
production effects, Homelab infrastructure, force-push, direct default-branch
push, or any target/scope expansion. Those actions retain their own exact
human gates.

## Stop rules

- Stop if branch/task ownership is ambiguous, the worktree contains unrelated
  changes, the base moved incompatibly, validation contradicts readiness, or
  the requested remote action exceeds current authorization.
- A local commit is recoverability, not proof of correctness or operational
  authority. A push or PR is not merge approval unless a current explicit
  approval or valid envelope independently includes the merge stage.
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
