---
name: infrastructure-change-control
description: Use for Virtualisierung, Storage, Container, DNS, firewall, IAM, backup, monitoring, reverse proxy, VPN, or other infrastructure work.
---

# Infrastruktur change control

## Critical rule

No unapproved live changes. Repository patches, plans, dry-run scripts, and documentation are allowed. Productive changes require explicit approval, rollback, validation, and final main-thread review.

## Steps

1. Inventory first: topology, affected hosts, services, data, ports, credentials, backups.
2. Classify risk:
   - Low: docs, templates, local validation scripts.
   - Medium: Compose/Ansible/monitoring patches not applied live.
   - Critical: DNS, firewall, routing, storage, backup, IAM, secrets, TLS, VPN, productive deploy.
3. For critical changes, call `infra_critical_planner` before any patch authoring.
4. Prepare rollback and validation before commands.
5. Redact secrets and avoid publishing private topology.

## Required output for critical work

```text
## Impact
...

## Pre-checks
...

## Plan
...

## Rollback
...

## Validation
...

## Freigabepunkte
...
```
