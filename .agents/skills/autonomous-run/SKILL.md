---
name: autonomous-run
description: Use when a task should gather required inputs and approvals early, then run end-to-end autonomously until a result or checkpoint.
---

# Autonomous run

## Trigger

- Use when the task is multi-step and would otherwise require repeated user ping-pong.
- Use when you can bundle missing questions, approvals, files, or credentials up front.
- Use when the desired behavior is "keep going until done or safely blocked."

## Inputs

- User goal and acceptance criteria.
- Scope boundaries: allowed paths, systems, repos, and environments.
- Required approvals for risky, live, external, destructive, or irreversible actions.
- Existing repo policy, task log, and relevant local conventions.

## Workflow

1. Restate the goal, scope, non-goals, done criteria, evidence classes, and stop conditions in one short check.
2. Separate four things that must never be conflated:
   - worktree write permission,
   - repository task scope,
   - human authorization for live/external/risky actions,
   - technical capability or credentials.
3. Identify all missing must-have inputs and approvals before starting implementation.
4. Ask for them in one bundled request whenever feasible. Do not drip-feed questions.
5. For a long or interruption-prone run, copy the managed templates to the ignored
   `.agent-state/` directory and activate an opt-in `run-contract.json`.
6. During `intake` and `planned`, keep `action_envelope_required` false so the
   local contract and envelope can be prepared. Only after the actual human
   approval is present and the envelope is valid, set it true and move to
   `authorized`. This order stages enforcement; it does not weaken it.
7. After the bundle is resolved, execute independently within scope. Update the
   contract only to describe state; never use it to invent or widen approval.
8. Prefer the smallest safe next action that preserves momentum.
9. Before context compaction, write a matching `checkpoint.json` whose objective
   is unchanged and whose last result is evidence-backed.
10. Finish at one of three end states:
   - completed result,
   - safe checkpoint with resume prompt,
   - explicit blocker that cannot be resolved without new user input or approval.

## Contracted state machine

`intake -> planned -> authorized -> executing -> verifying -> completed`

- `blocked` may be entered from any state when a hard stop is reached.
- `authorized` means an actual human approval exists in the conversation where
  required; editing the JSON file cannot create that approval.
- Do not skip from `planned` to `completed` merely because files were changed.
- A completed state requires current evidence for every declared evidence class.

## Stop / Approval Rules

- Stop before live changes, external side effects, destructive actions, new secrets, or permission changes that were not already approved.
- Stop if the same missing input or approval blocks progress after one bundled request.
- Stop if evidence contradicts the original assumption set and scope must change.
- Stop if an action envelope is absent, expired, mismatched, or broader than the
  actual human authorization for a live/external/risky action.
- Do not claim completion when validation is missing. A passing status written by
  the agent is metadata, not independent proof of the underlying result.

## Checks

- Goal and acceptance criteria are explicit.
- Required approvals were requested as early as possible.
- The remaining work can proceed without new user turns.
- Final state is completed or checkpointed, not silently abandoned.
- Evidence records name the observation time, command/readback, result, and
  repo-local artifact where applicable.

## Output

```text
## Goal
...

## Bundled inputs / approvals
- ...

## Progress
- ...

## Validation or checkpoint
- ...

## Next safe step
- ...
```
