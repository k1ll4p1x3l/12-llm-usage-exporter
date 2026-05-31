# Release Baseline

Current pre-release baseline: `0.0.0-dev`

- Initial go implementation is prepared for local build and iteration.
- No public v1 semantics and no signed production release yet.
- Development and CI baseline: Go `1.26.3`.
- User-local maintainer tools:
  - GoReleaser `v2.16.0`
  - Gitleaks `v8.30.1`
  - actionlint `v1.7.12`
  - govulncheck `v1.1.4`

## Planned milestones

- 0.1.0: Pre-alpha CLI exporter with real Codex App Server integration.
- 0.2.0: Integration tests with mocked JSON-RPC fixtures and release hardening.
- 0.3.0: Release candidate with optional attestations and distribution artifacts.
- 0.4.0: Public project operations baseline (milestone process, release-note automation, contribution tooling).

## GitHub milestone mapping

- `0.1` maps to the milestone in `docs/07_roadmap_milestones.md` covering MVP foundation work.
- `0.2` maps to hardening and operational quality work.
- `0.3` maps to provider expansion and policy coverage.
