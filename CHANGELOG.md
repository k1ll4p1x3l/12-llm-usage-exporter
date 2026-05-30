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

## 0.0.1

- Repository bootstrap and research/plan documentation.
