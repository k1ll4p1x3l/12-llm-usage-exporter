---
name: decision-record
description: Use when the task is to choose between options, document trade-offs, and leave a reusable record of why a path was chosen.
---

# Decision record

## Trigger

- Use when the user asks what to do, which option is better, or how to structure an ADR or decision memo.
- Use when trade-offs, reversibility, and review triggers matter.

## Inputs

- Decision question.
- Constraints, criteria, stakeholders, and known risks.
- Available evidence and its confidence level.

## Workflow

1. State the decision clearly.
2. List realistic options, including do-nothing where relevant.
3. Define criteria and rough weighting without fake precision.
4. Score coarsely and explain why.
5. Document trade-offs, reversibility, and risks.
6. End with a recommendation plus triggers for re-evaluation.

## Stop / Approval Rules

- Stop if a recommendation would rest on missing critical evidence.
- Stop before presenting a coarse score as scientific certainty.
- Do not hide uncertainty behind long tables.

## Checks

- Criteria are explicit.
- Scoring is coarse and justified.
- Recommendation follows from stated trade-offs.
- Review triggers are concrete.

## Output

```text
## Decision question
...

## Options
- ...

## Criteria
- ...

## Matrix
| Option | Benefit | Cost | Risk | Reversibility | Overall |

## Recommendation
- ...

## Review trigger
- ...
```
