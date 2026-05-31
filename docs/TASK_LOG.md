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

## Checkpoint 2026-05-31 03:26 Europe/Berlin

### Goal

Continue the long-running 0.1-0.4 implementation goal with the current branch and
GitHub state as authoritative evidence.

### Completed

- Re-read repository rules, conventions, source policy, security policy, and the
  `$long-running-goal` skill.
- Verified PR [#8](https://github.com/k1ll4p1x3l/12-llm-usage-exporter/pull/8):
  - branch `codex/complete-0.1-0.4` targets `main`,
  - all required checks pass (`ci`, `analyze`, `vulncheck`, `check-milestone`,
    `ensure-changelog`),
  - milestone `0.4` and labels are assigned,
  - mergeability is `MERGEABLE`,
  - review state is `REVIEW_REQUIRED`.
- Verified live GitHub repository settings:
  - default branch `main`,
  - Discussions enabled, Wiki disabled, delete-branch-on-merge enabled,
  - topics: `codex`, `go`, `llm-tools`, `prometheus`, `telemetry`,
  - branch protection requires PR review and the expected required checks.
- Started a read-only milestone completion audit for the 0.1-0.4 scope.
- Integrated the still-open Dependabot Go module targets into this branch:
  - `github.com/pelletier/go-toml/v2` `v2.3.1`,
  - `github.com/prometheus/client_golang` `v1.23.2`.
- Resolved read-only audit findings:
  - documented Codex `initialize` as allowed JSON-RPC session setup only,
  - clarified milestone `0.3` as provider policy coverage with safe deferral,
  - added an explicit milestone `0.4` operations baseline section,
  - completed checked-date source logging and removed duplicated tooling source entries,
  - moved generated manual remediation scripts to ignored `.codex/state` by default.

### Changed Files

- `CHANGELOG.md`
- `README.md`
- `VERSIONS.md`
- `docs/04_provider_abstraction.md`
- `docs/07_roadmap_milestones.md`
- `docs/08_codex_implementation_brief.md`
- `docs/99_sources.md`
- `docs/TASK_LOG.md`
- `docs/operations.md`
- `docs/provider-policy/codex.md`
- `go.mod`
- `go.sum`
- `scripts/dev-env-check.sh`

### Tests / Checks

- `git status --short --branch`: clean branch before this checkpoint update.
- `gh pr view 8 --json ...`: pass; PR is open, mergeable, checks green,
  review required.
- `gh repo view --json ...`: pass; repository settings match operations doc.
- `gh api repos/k1ll4p1x3l/12-llm-usage-exporter/branches/main/protection`:
  pass; branch protection matches the required check list.
- `gh api repos/k1ll4p1x3l/12-llm-usage-exporter/milestones --paginate`:
  pass; milestones `0.1` through `0.4` exist.
- `gh pr list --state open --json ...`: pass; Dependabot PRs are labeled and
  assigned to `0.2`, and PR #8 is assigned to `0.4`.
- `go get github.com/prometheus/client_golang@v1.23.2 github.com/pelletier/go-toml/v2@v2.3.1`:
  pass.
- `go mod tidy`: pass.
- `bash -n scripts/dev-env-check.sh scripts/check.sh scripts/bootstrap-github-settings.sh scripts/bootstrap-github-org.sh`:
  pass.
- `GOCACHE=/tmp/go-build GOMODCACHE=/tmp/go-mod-cache go test -race ./...`:
  pass with network permission after the first sandboxed run could not download
  updated modules.
- `./scripts/check.sh`: pass after dependency, source, policy, and checkpoint
  updates.

### Risks / Open Points

- The goal is not complete on `main` yet because branch protection requires an
  approving review for PR #8 and the latest follow-up changes still need to be
  committed, pushed, and rechecked by GitHub.
- Milestone 0.3 provider expansion remains intentionally constrained by provider
  safety policy: Claude Code is documented as deferred until a safe local
  read-only quota source exists. This should not be represented as a working
  second provider collector.
- Dependabot PRs #1 through #7 are superseded by PR #8 after the action and Go
  module updates are incorporated; they should be closed with a supersession
  note after the follow-up commit is pushed.

### Next Safe Step

- Commit and push this follow-up update, close superseded Dependabot PRs #1
  through #7 with a note pointing to PR #8, then verify PR #8 checks again and
  wait for or request the required PR review.

### Resume Prompt

Continue on branch `codex/complete-0.1-0.4`. Read `AGENTS.md`,
`.agents/skills/long-running-goal/SKILL.md`, and `docs/TASK_LOG.md`. Verify
`git status --short --branch` and PR #8. Do not bypass branch protection or
merge without the required review. Continue from the latest checkpoint, close
superseded Dependabot PRs only after PR #8 includes the replacement updates, and
keep `docs/TASK_LOG.md` current after each milestone.

## Checkpoint 2026-05-31 03:38 Europe/Berlin

### Goal

Record the completion of the dependency-consolidation milestone and the current
PR gate status.

### Completed

- Committed and pushed audit fixes as `8a23fa5` on
  `codex/complete-0.1-0.4`.
- Closed superseded Dependabot PRs #1 through #7 with comments pointing to PR
  #8 as the consolidated replacement.
- Verified only PR #8 remains open.
- Verified milestones `0.1` through `0.4` have no open milestone items except
  PR #8 assigned to `0.4`.
- Verified PR #8 checks are green after the follow-up push:
  `ci`, `analyze`, `vulncheck`, `check-milestone`, `ensure-changelog`, and
  GitGuardian all pass.

### Changed Files

- `docs/TASK_LOG.md`

### Tests / Checks

- `gh pr list --state open --json ...`: pass; only PR #8 is open.
- `gh api repos/k1ll4p1x3l/12-llm-usage-exporter/milestones --paginate`:
  pass; milestones `0.1` through `0.4` have no open items outside PR #8.
- `gh pr checks 8 --watch --interval 10`: pass; all required checks pass.

### Risks / Open Points

- PR #8 remains `REVIEW_REQUIRED` because branch protection requires one
  approving review. Do not bypass this requirement.
- Milestone `0.3` is satisfied as provider policy coverage and safe deferral,
  not as a live second-provider collector.

### Next Safe Step

- Request or wait for an approving review on PR #8. After approval, merge via
  the protected PR path and verify `main`.

### Resume Prompt

Continue on branch `codex/complete-0.1-0.4`. Verify PR #8 review state and
checks. If an approving review exists, merge through GitHub's protected PR path,
pull `main`, run `./scripts/check.sh`, and update `docs/TASK_LOG.md`. If review
is still missing, do not merge or bypass branch protection.
