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

## Milestone 0.3 (Provider Expansion)

- Goal: second-provider onboarding with policy and collection coverage.
- Planned outcomes:
  - new provider policy document,
  - collector contract tests for schema drift,
  - integration documentation in `docs/provider-policy`.
- Tracking:
  - open issues and PRs should be assigned to milestone `0.3`.

## Milestone process

- Milestones are planning containers in GitHub and should reflect release intent, not just issue buckets.
- Always include representative changes in changelog entries before closing a milestone.
- Keep risk flags, dependency updates, and docs adjustments in the same milestone.
- See [`docs/milestones.md`](docs/milestones.md) for maintainer-level milestone workflows.

## Current milestone

- In progress: MVP runnable scaffold with configuration, Codex collector pipeline, JSON and Prometheus exports.
