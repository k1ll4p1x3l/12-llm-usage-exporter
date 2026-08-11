---
name: observability-and-runbooks
description: Use for monitoring, logging, alerts, ownership, retention, privacy boundaries, and runbook linkage around a service or homelab system.
---

# Observability and runbooks

## Trigger

- Use when a service needs monitoring, alerting, logging, or operator runbooks.
- Use when an existing setup generates noise, lacks ownership, or cannot distinguish good state from failure.

## Inputs

- Services, dependencies, and critical user journeys.
- Signals already available or easy to collect.
- Alerting channels, owners, privacy constraints, and retention needs.

## Workflow

1. Define the service or system boundary.
2. List the signals that matter: availability, latency, errors, capacity, freshness, backup success, security events, or config drift.
3. For each signal, define source, retention, alert condition, owner, runbook, and privacy considerations.
4. Describe the expected good state in plain language.
5. Separate operational signals from forensic evidence and from sensitive personal data.
6. Remove or de-prioritize alerts that have no owner or no actionable runbook.
7. Revisit observability after incidents and major architecture changes.

## Stop / Approval Rules

- Never create alerts with no owner, no threshold logic, or no response path.
- Never collect more personal or secret data than the operational goal requires.
- Never call a metric useful if no one can explain what good state or bad state means.

## Checks

- Every important signal has source, retention, alert, owner, and runbook.
- Good state is explicit.
- Privacy and data minimization are documented.
- No critical system is left without actionable signals.

## Output

```text
## System scope
...

## Signal catalog
- ...

## Alerts and owners
- ...

## Runbook links
- ...

## Privacy / retention notes
- ...
```
