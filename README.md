# llm-usage-exporter

`llm-usage-exporter` is a local telemetry adapter that reads usage and quota data from coding agents and exports normalized snapshots to JSON and Prometheus.

## Current status

- Development stage: first beta release published (`v0.5.0-beta.1`)
- Primary platforms: macOS, Linux, Windows
- Primary language: Go
- Primary provider: OpenAI Codex (read-only)

Environment-specific follow-up validation is deferred until the operator
completes an external lab audit. The published beta remains the current usable
baseline.

## Architecture

```text
Provider source (e.g. Codex App Server)
  -> collector
  -> neutral model
  -> exporters (JSON file, Prometheus)
  -> local monitoring
```

The project is intentionally a data translator, not a credential manager, dashboard, or authentication service.

## Key guarantees

- No credential persistence.
- No token refresh/login/logout flows.
- No web UI scraping.
- No proxy/MITM collection.
- Unknown provider schema results in explicit error status snapshots.

## Agent configuration

This repository consumes the centrally maintained Agent Core with the public
profile pinned in `.agent-core.lock.json`. Its managed paths include
`AGENTS.md`, `.codex/`, `.agents/skills/`, and `.agent-core/templates/`.
Project-specific purpose, commands, and immutable boundaries remain locally
owned in `PROJECT_PROFILE.md`, `docs/REPO_POLICY.md`, and the existing project
documentation.

Do not edit managed files directly. Agent Core updates arrive as reviewable
sync pull requests and must pass lock/hash verification, this repository's CI,
and public-safety checks. Optional templates under `.agent-core/templates/`
become consumer-owned only after they are copied to an ignored local working
path such as `.agent-state/`.

## Quick start

Create a starter config in the OS default location:

```bash
llm-usage-exporter init
llm-usage-exporter doctor
```

Default config and snapshot paths:

- Linux: `~/.config/llm-usage-exporter/config.yaml` and `~/.local/state/llm-usage-exporter/usage.snapshot.json`
- macOS: `~/Library/Application Support/llm-usage-exporter/config.yaml` and `~/Library/Application Support/llm-usage-exporter/usage.snapshot.json`
- Windows: `%AppData%\llm-usage-exporter\config.yaml` and `%LocalAppData%\llm-usage-exporter\usage.snapshot.json`

Build from source:

```bash
go build ./cmd/llm-usage-exporter
./llm-usage-exporter serve --config config.yaml
```

Run a one-shot snapshot:

```bash
./llm-usage-exporter snapshot --config examples/llm-usage-exporter.yaml
```

## Configuration

`llm-usage-exporter` accepts JSON, YAML, or TOML configuration. Environment variables are allowed for common overrides.

Example:

```yaml
poll_interval: 60s
json_output:
  enabled: true
  path: /var/lib/llm-usage-exporter/usage.snapshot.json
prometheus:
  enabled: true
  listen_address: 127.0.0.1:9738
providers:
  - name: codex
    type: codex
    enabled: true
    command: codex
    timeout: 10s
    args: ["app-server"]
```

## CLI

- `init` writes a starter YAML config. It will not overwrite existing files unless `--force` is set.
- `doctor` validates config, checks Codex command resolution, verifies output settings, and runs a read-only Codex collection probe.
- `serve` runs periodic polling and exports to configured outputs.
- `snapshot` runs one poll and prints snapshot to stdout. If every provider fails, it still
  prints the error snapshot but exits non-zero.
- `validate-config` validates and prints the effective configuration.
- `version` prints the built version.

Useful docs:

- `docs/deployment.md`
- `docs/operations.md`
- `docs/release.md`
- `docs/provider-policy/codex.md`
- `schemas/usage.snapshot.v1alpha1.json`

## Development

- Maintainer security baseline: Go `1.26.6` with govulncheck `v1.1.4`.
- `scripts/dev-env-check.sh`
- `scripts/check.sh`
- `go test ./...`
- `go test -race ./...`
- `go vet ./...`
- `gofmt` or IDE formatting before commits
- release build can use `goreleaser` and requires a semver git tag (`v*`) for `Release` workflow
- release SBOM generation requires `syft` on the release runner
- beta release archives target Linux, macOS, and Windows on `amd64` and `arm64`
- PRs are expected to carry an assigned GitHub milestone.
- Maintainers can generate release-note drafts with the Milestone Notes workflow and
  [`docs/milestones.md`](docs/milestones.md).
- GitHub metadata and settings helpers are contact-free, preview-only tools.
  They never authenticate or apply changes; `DRY_RUN=0` fails closed. The
  matching workflow also emits only a reviewable preview with read-only
  permissions.
- `scripts/check.sh` includes the race detector, redacting public-safety tests,
  and an unpublished GoReleaser snapshot whose six archives, checksums, and six
  Syft SBOMs are verified before any tag workflow may publish.
- New provider support requires a provider policy under `docs/provider-policy/`.
- Long-running implementation checkpoints are tracked in `docs/TASK_LOG.md`.
- Agent-specific project context and approval boundaries are documented in
  `PROJECT_PROFILE.md` and `docs/REPO_POLICY.md`.

## Repository policy

- Public documentation and interfaces are in English.
- Private operational notes (if present) live outside tracked repository content.
- For release planning and milestone operations, follow
  [`docs/operations.md`](docs/operations.md) and [`docs/milestones.md`](docs/milestones.md).
- Contact-free governance previews are `./scripts/bootstrap-github-org.sh`
  and `./scripts/bootstrap-github-settings.sh`; applying settings remains a
  separate, explicitly approved operation outside these scripts.
- Full local validation is `./scripts/check.sh`.

## License

Apache-2.0
