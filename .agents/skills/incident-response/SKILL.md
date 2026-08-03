---
name: incident-response
description: Use for an incident lifecycle from preparation and detection through triage, containment, evidence handling, recovery, and lessons learned.
---

# Incident response

## Trigger

- Use when there is a suspected outage, compromise, misconfiguration with live impact, data loss event, or unclear production fault.
- Use when evidence handling and recovery discipline matter more than speed alone.

## Inputs

- Incident signal or symptom.
- Affected systems, users, and business impact.
- Available logs, alerts, timelines, and prior changes.
- Known containment options, recovery paths, and contact points.

## Workflow

1. Preparation: identify severity, owners, communication path, and known recovery options.
2. Detection: state what triggered the incident and what is currently known.
3. Triage: separate confirmed facts, plausible hypotheses, and unknowns.
4. Containment: define the narrowest safe action to stop further damage or spread.
5. Evidence: preserve logs, commands, timestamps, artifacts, and relevant state before destructive cleanup.
6. Eradication: remove the confirmed cause only after containment and evidence capture.
7. Recovery: restore service in controlled order and verify the intended good state.
8. Lessons learned: capture timeline, root cause, safeguards, and follow-up actions.

## Stop / Approval Rules

- Never destroy evidence before capturing what is needed for diagnosis and accountability.
- Never claim compromise, recovery, or root cause without evidence.
- Never perform broad containment that creates larger outage risk unless the human owner explicitly approves it.
- Never mix speculation and fact in the incident record.

## Checks

- Incident stage is explicit.
- Impact and scope are stated.
- Evidence is preserved or the reason it could not be preserved is recorded.
- Recovery includes independent verification and follow-up actions.

## Output

```text
## Incident stage
...

## Impact and scope
...

## Confirmed facts
- ...

## Containment / evidence / recovery
- ...

## Follow-up and lessons learned
- ...
```
