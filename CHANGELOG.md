# Changelog

## Unreleased

- Added initial public implementation scaffold for `llm-usage-exporter`.
- Added:
  - `go.mod` and Go project layout.
  - Configuration loading with JSON/YAML/TOML + environment overrides.
  - Internal neutral data model and collector/exporter abstractions.
  - Codex collector with App Server JSON-RPC client and policy guards.
  - JSON and Prometheus exporters.
  - Basic CLI (`serve`, `snapshot`, `validate-config`, `version`).
  - CI, CodeQL, Dependabot, and release workflow scaffold.
- Added deployment readiness artifacts:
  - `docs/deployment.md`, sample config and systemd unit.
  - `.github/workflows/*` for CI, security checks, and release.
  - `.goreleaser.yaml` for release archive and SBOM generation.
- Hardened configuration handling:
  - Environment overrides now fail fast on invalid values.
  - Duration parsing supports `d` and `w` units for convenience.
- Added focused tests for service and configuration validation paths.
- Added `go vet` into CI.
- Changed linker-injected version variable from `const` to `var` to support release pipelines.
- Added repository organization hardening for public operations:
  - Milestone enforcement workflow for pull requests.
  - Issue templates for bug reports and feature requests.
  - Milestone-first roadmap and operations guidance.
- Added milestone release-note automation:
  - New workflow `.github/workflows/milestone-release-notes.yml` to export all milestone items and optionally create or update a draft release.
  - New maintainer runbook `docs/milestones.md`.
- Enhanced milestone notes workflow to accept milestone dispatch by title as an alternative to number.
- Added release runbook `docs/release.md` covering milestone freeze, notes generation,
  and release sequencing.
- Cross-linked release process from `docs/deployment.md`.
- Added changelog enforcement workflow `.github/workflows/changelog-check.yml` requiring `CHANGELOG.md` updates for PRs unless labeled `no-changelog-required`.
- Added `scripts/bootstrap-github-org.sh` to provision milestones (`0.1`–`0.4`) and control labels for the repository workflows.
- Added `.github/workflows/bootstrap-github-org.yml` to run the bootstrap script from GitHub Actions.
- Extended bootstrap automation to optionally apply branch protection for the target branch, including required check contexts aligned to existing workflows.
- Updated bootstrap helper to support `DRY_RUN=1` without GitHub authentication by deferring repository resolution until runtime.
- Hardened local development and repository automation:
  - Updated GitHub Actions to current major versions and Go `1.26.3`.
  - Added `scripts/dev-env-check.sh`, `scripts/check.sh`, and `scripts/bootstrap-github-settings.sh`.
  - Split GitHub metadata bootstrap from admin-level repository settings.
  - Made milestone enforcement fetch the current pull request state before failing.
  - Added additional repository labels for dependencies, automation, security, provider, core, docs, and release work.
  - Added repository CODEOWNERS.
- Hardened the MVP runtime:
  - Added provider-level timeout parsing and validation.
  - Fixed Codex JSON-RPC framed response parsing.
  - Added JSON-RPC response version validation and frame size limits.
  - Made Codex collector RPC dependencies mockable.
  - Treat more Codex rate-limit schema drift as hard errors.
  - Normalized provider error snapshots so degraded and unavailable output still follows the public schema.
  - Redacted sensitive-looking provider error text, including bearer headers and JSON-like secret fields, before snapshot export.
  - Preserved `last_successful_at` across later provider failures.
  - Made `snapshot` exit non-zero when all providers fail after printing the error snapshot.
- Expanded tests for Codex collector/client behavior, config validation, JSON export, Prometheus export, redaction, and scheduler failure state.
- Added a versioned JSON schema for `usage.snapshot.v1alpha1`.
- Added a deferred Claude Code provider policy documenting why it is not safe to collect by default yet.
- Updated the long-running task log with the live PR, branch-protection, and milestone completion audit status.
- Updated Go module dependencies for TOML parsing and Prometheus export to the current Dependabot targets.
- Clarified the 0.3 provider-policy milestone, added an explicit 0.4 operations milestone, and documented Codex `initialize` as JSON-RPC session setup.
- Moved generated manual environment remediation steps to the ignored `.codex/state` area by default.
- Logged closure of superseded Dependabot pull requests after their updates were consolidated into PR #8.
- Recorded explicit admin merge approval for PR #8 in the task log.
- Recorded the final merged-main verification checkpoint for the 0.1-0.4 implementation baseline.
- Adjusted branch-protection bootstrap defaults for single-maintainer operation by setting required approving reviews to `0` while keeping required status checks.

## 0.0.1

- Repository bootstrap and research/plan documentation.
