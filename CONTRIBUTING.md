# Contributing

## Development Rules

- No provider credential handling.
- No UI scraping.
- No MITM or proxy collection.
- Tests required for every collector mapping.
- Every new provider needs a `docs/provider-policy/<provider>.md` security review.

## Pull Request Checklist

- [ ] No secrets in logs, snapshots, metrics, fixtures.
- [ ] Prometheus labels reviewed for cardinality and privacy.
- [ ] New external facts documented in `docs/99_sources.md`.
- [ ] `go test ./...`, `govulncheck ./...`, lint and CodeQL pass.
- [ ] `CHANGELOG.md` updated.
- [ ] `README.md` reflects functional and operational changes.
- [ ] Pull request has a milestone assigned.
- [ ] Issue/feature is filed with the appropriate issue template.
- [ ] `CHANGELOG.md` is updated unless PR carries `no-changelog-required`.
