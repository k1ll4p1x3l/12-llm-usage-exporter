# Project profile

Status: consumer-owned working copy
Managed-by-source: no

## Purpose

- Read usage and quota information through explicitly allowed, read-only local
  provider interfaces and normalize it into JSON and Prometheus snapshots.
- Support local operator diagnostics without becoming a credential manager,
  authentication broker, web scraper, proxy, dashboard, or provider-control
  plane.

## Primary work modes

- Primary: `code`, `automation`
- Secondary: `data`, `security-review`, `ops-docs`, `research`

## Important paths

| Path | Why it matters |
|---|---|
| `cmd/llm-usage-exporter/` | CLI entry point and command behavior |
| `internal/collectors/` | Provider-specific read-only collection |
| `internal/model/` | Provider-neutral snapshot model |
| `internal/exporters/` | JSON and Prometheus output paths |
| `docs/provider-policy/` | Allowed and forbidden provider operations |
| `schemas/` | Versioned public snapshot schema |
| `.agent-core.lock.json` | Pinned central Agent Core profile and managed-file hashes |
| `.agent-core/templates/` | Centrally managed copy-once operating templates |

## Commands

| Goal | Command | Confidence | Notes |
|---|---|---|---|
| Build | `go build ./cmd/llm-usage-exporter` | verified | Produces the local CLI binary |
| Unit tests | `go test ./...` | verified | Runs the Go test suite |
| Static checks | `go vet ./...` | verified | Run with formatting checks before handoff |
| Automation contracts | `python3 -m unittest discover -s tests -p 'test_*.py' -v` | verified locally | Preview-only helpers, redacting public scan, malicious archives, checksums, and SBOM matrix |
| Full validation | `./scripts/check.sh` | Hosted validation pending | Requires the documented Go/security/release toolchain; includes race and unpublished release snapshot |
| GitHub settings preview | `./scripts/bootstrap-github-settings.sh` | verified locally | Contact-free preview only; `DRY_RUN=0` is rejected |
| Local snapshot | `go run ./cmd/llm-usage-exporter snapshot --config examples/llm-usage-exporter.yaml` | verified from repo docs | May contact only configured local provider transports |

## Risks and boundaries

- This is a public repository. All tracked content must be public-safe.
- Never persist, decode, forward, refresh, or proxy provider credentials.
- Never read `~/.codex/auth.json`, scrape provider UIs, sniff headers, or use
  MITM collection.
- Usage metadata can still be operationally sensitive; generated snapshots and
  local configuration stay outside tracked content unless explicitly sanitized.
- Repository changes do not authorize live Homelab, monitoring, provider, or
  GitHub-setting changes.
- Repository automation may describe GitHub mutations but cannot execute them;
  metadata and settings helpers remain preview-only in both shell and Actions.

## Done criteria

- Relevant Go tests and static checks pass.
- Provider-policy and security boundaries remain covered by tests and docs.
- Public-safety and secret scans pass before publication.
- Race detection and the six-platform archive/checksum/SBOM contract pass in
  Hosted CI before release publication.
- Agent Core changes pass central `verify-consumer`, an idempotent second sync,
  Consumer CI, and an independent worktree-gate readback.
- User-visible or operational changes update README/CHANGELOG and relevant
  runbooks.

## Known deferred validation

- Environment-specific Homelab integration remains deferred until the separate
  external lab audit is complete and explicitly approved.
