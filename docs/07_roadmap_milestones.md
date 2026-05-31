# Roadmap

## Release Milestones

## Milestone 0.1 (MVP Foundation)

- Goal: runnable core with config, collect pipeline, JSON snapshot export, and Prometheus metrics.
- Owners: core maintainers
- Tracking:
  - open issues and PRs should be assigned to milestone `0.1`.
  - PRs must pass all checks in `CI`, `CodeQL`, and `Security`.

## Milestone 0.2 (Readiness and Hardening)

- Goal: robust integration posture and operational resilience.
- Planned outcomes:
  - expanded scheduler, validation, and error path coverage,
  - documented production-safe release workflow,
  - expanded issue and PR templates plus milestone enforcement.
- Tracking:
  - open issues and PRs should be assigned to milestone `0.2`.

## Milestone 0.3 (Provider Policy Coverage)

- Goal: evaluate a second provider candidate without weakening the read-only
  security model.
- Planned outcomes:
  - new provider policy document for at least one provider candidate,
  - explicit allow/deny decision for default collection,
  - collector contract tests for schema drift when a safe collector is enabled,
  - integration or deferral documentation in `docs/provider-policy`.
- Tracking:
  - open issues and PRs should be assigned to milestone `0.3`.

## Milestone 0.4 (Public Operations Baseline)

- Goal: repository operations, release automation, and public maintenance
  guardrails are ready for pre-alpha collaboration.
- Planned outcomes:
  - branch protection and required status checks,
  - milestone and changelog enforcement,
  - release-note and release workflow documentation,
  - maintainer environment and full-check scripts.
- Tracking:
  - open issues and PRs should be assigned to milestone `0.4`.

## Milestone process

- Milestones are planning containers in GitHub and should reflect release intent, not just issue buckets.
- Always include representative changes in changelog entries before closing a milestone.
- Keep risk flags, dependency updates, and docs adjustments in the same milestone.
- See [`docs/milestones.md`](docs/milestones.md) for maintainer-level milestone workflows.

## Current milestone

- In progress: PR #8 combines the 0.1-0.4 implementation baseline for review.
