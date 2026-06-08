# Release Baseline

Current release baseline: `0.5.0-beta.1`

- Initial go implementation is prepared for local build and iteration.
- No public v1 semantics and no signed production release yet.
- Development and CI baseline: Go `1.26.4`.
- User-local maintainer tools:
  - GoReleaser `v2.16.0`
  - Syft `v1.44.0` for release SBOM generation
  - Gitleaks `v8.30.1`
  - actionlint `v1.7.12`
  - govulncheck `v1.1.4`
- Direct Go module baselines:
  - `github.com/pelletier/go-toml/v2` `v2.3.1`
  - `github.com/prometheus/client_golang` `v1.23.2`

## Planned milestones

- 0.1.0: Pre-alpha CLI exporter with real Codex App Server integration.
- 0.2.0: Integration tests with mocked JSON-RPC fixtures and release hardening.
- 0.3.0: Provider policy coverage with safe deferral where no read-only source exists.
- 0.4.0: Public project operations baseline (milestone process, release-note automation, contribution tooling).
- 0.5.0-beta.1: First beta with cross-platform CLI setup, diagnostics, current Codex App Server rate-limit mapping, and Linux/macOS/Windows release archives.

## GitHub milestone mapping

- `0.1` maps to the milestone in `docs/07_roadmap_milestones.md` covering MVP foundation work.
- `0.2` maps to hardening and operational quality work.
- `0.3` maps to provider policy coverage and safe provider-candidate deferral.
- `0.4` maps to public operations and release automation.
- `0.5-beta` maps to first beta release readiness across macOS, Linux, and Windows.
