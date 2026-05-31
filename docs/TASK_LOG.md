# Task Log

## Checkpoint 2026-05-31 Europe/Berlin

### Goal

Bring the repository to the current GitHub state and complete the 0.1-0.4 implementation path:
MVP hardening, automation, GitHub operations, release readiness, and documentation.

### Completed

- Fast-forwarded local `main` to `origin/main` at `a219196`.
- Created implementation branch `codex/complete-0.1-0.4`.
- Installed user-local tools under `~/.local/bin`:
  - GoReleaser `v2.16.0`
  - Gitleaks `v8.30.1`
  - actionlint `v1.7.12`
  - govulncheck `v1.1.4`
- Moved Go build/module caches for heavyweight tool installs from `/tmp` to
  `~/.cache/llm-usage-exporter` after `/tmp` filled during the first attempt.
- Updated GitHub Actions to current major versions and Go `1.26.3`.
- Added environment, full-check, and GitHub settings bootstrap scripts.
- Applied live GitHub repository metadata and settings:
  - labels and milestones `0.1` through `0.4`
  - topics, Discussions enabled, Wiki disabled, delete branch on merge enabled
  - Dependabot alerts/security updates enabled
  - secret scanning and push protection enabled
  - branch protection on `main` with required PR review and status checks
  - existing Dependabot PRs labeled and assigned to milestone `0.2`
- Hardened Codex collector and service behavior:
  - provider timeout config
  - JSON-RPC framed response parsing and max frame size
  - strict malformed `Content-Length` rejection and unframed response size checks
  - regression test for the long-lived appserver process lifecycle
  - mockable Codex RPC client
  - stricter rate-limit schema handling
  - schema-compatible provider error snapshots
  - redacted provider error messages
  - persisted `last_successful_at`
- Fixed `snapshot` so all-provider failure exits non-zero after printing the error snapshot.
- Added tests for Codex, config, JSON export, Prometheus export, redaction, and scheduler failure paths.
- Added JSON schema and deferred Claude Code provider policy.

### Changed Files

- `.github/workflows/*`
- `.github/CODEOWNERS`
- `scripts/bootstrap-github-org.sh`
- `scripts/bootstrap-github-settings.sh`
- `scripts/check.sh`
- `scripts/dev-env-check.sh`
- `cmd/llm-usage-exporter/*`
- `internal/*`
- `schemas/usage.snapshot.v1alpha1.json`
- `docs/provider-policy/claude-code.md`
- `docs/TASK_LOG.md`

### Tests / Checks

- `./scripts/dev-env-check.sh`: pass
- `actionlint`: pass
- `go test ./...`: pass
- `go vet ./...`: pass
- `go test -race ./...`: pass
- `./scripts/check.sh`: pass
- Final `./scripts/check.sh`: pass

### Risks / Open Points

- Required checks in branch protection reference workflow job names and should be verified once this branch opens a PR.
- GoReleaser source builds are large; keep caches outside `/tmp`.
- Claude Code provider remains deferred until a safe read-only quota source is verified.

### Next Safe Step

Review the diff, commit, push, and open a PR.

### Resume Prompt

Continue on branch `codex/complete-0.1-0.4`. Read `docs/TASK_LOG.md`, run
`git status --short --branch`, then continue with Codex collector/service hardening and
automation validation.
