---
name: decision-record
description: Use when the task is to choose between options, document trade-offs, or create an ADR/decision memo.
---

# Decision record

## Steps

1. State the decision question.
2. List options, including do-nothing if relevant.
3. Define constraints and weighted criteria.
4. Score coarsely and explain trade-offs.
5. Document reversibility, risks, triggers for review, and final recommendation.
6. Save as `docs/DECISIONS.md` or `docs/adr/YYYY-MM-DD-title.md` if requested.

## Minimum sections

```text
# Decision: ...

Date: YYYY-MM-DD
Status: proposed/accepted/rejected/superseded

## Context
## Options considered
## Criteria
## Decision
## Consequences
## Risks and mitigations
## Review trigger
```
