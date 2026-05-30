# llm-usage-exporter

`llm-usage-exporter` is a local telemetry adapter that reads usage and quota data from coding agents and exports normalized snapshots to JSON and Prometheus.

## Current status

- Development stage: pre-alpha
- Primary platform: Linux
- Primary language: Go
- Primary provider: OpenAI Codex (read-only)

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

## Quick start

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
    args: ["appserver"]
```

## CLI

- `serve` runs periodic polling and exports to configured outputs.
- `snapshot` runs one poll and prints snapshot to stdout.
- `validate-config` validates and prints the effective configuration.
- `version` prints the built version.

Useful docs:

- `docs/deployment.md`
- `docs/operations.md`
- `docs/release.md`
- `docs/provider-policy/codex.md`

## Development

- `go test ./...`
- `go vet ./...`
- `gofmt` or IDE formatting before commits
- release build can use `goreleaser` and requires a semver git tag (`v*`) for `Release` workflow
- PRs are expected to carry an assigned GitHub milestone.
- Maintainers can generate release-note drafts with the Milestone Notes workflow and
  [`docs/milestones.md`](docs/milestones.md).
- Repository governance bootstrap supports preview mode via `DRY_RUN=1` and also runs in GitHub Actions through `.github/workflows/bootstrap-github-org.yml` (including optional branch protection bootstrap).

## Repository policy

- Public documentation and interfaces are in English.
- Private operational notes (if present) live outside tracked repository content.
- For release planning and milestone operations, follow
  [`docs/operations.md`](docs/operations.md) and [`docs/milestones.md`](docs/milestones.md).
- Quick bootstrap for repo governance is `./scripts/bootstrap-github-org.sh`.

## License

Apache-2.0
