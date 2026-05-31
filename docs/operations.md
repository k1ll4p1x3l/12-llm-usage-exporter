# Repository Operations

Recommended GitHub settings for this repository:

- Branch protection on `main`
  - require pull request reviews before merge
  - dismiss stale reviews
  - require status checks: `ci`, `analyze`, `vulncheck`, `check-milestone`, `ensure-changelog`
  - require pull request milestone assignment before merge
  - require linear history (optional)
- Rulesets for fork security and secret scanning
- Security:
  - enable Dependabot alerts
  - enable secret scanning and push protection
  - require private security advisories for vulnerabilities
- Workflow enforcement:
  - `.github/workflows/milestone-check.yml` enforces milestone assignment on pull requests.
  - `.github/workflows/milestone-release-notes.yml` exports closed milestone items and can create/update a draft release.
  - `.github/workflows/changelog-check.yml` requires changelog updates unless explicitly labeled `no-changelog-required`.
- Release:
  - publish via tag push (`v*`) and GoReleaser workflow
  - keep release notes auto-generated or curated manually

## Repository bootstrap helper

Run once for a new repository clone to provision milestones and labels used by the workflow checks:

```bash
./scripts/bootstrap-github-org.sh
```

Use dry-run mode to inspect intended operations:

```bash
DRY_RUN=1 ./scripts/bootstrap-github-org.sh
```

You can also run this as an offline preview without GH authentication. For a
full run, authenticate first (`gh auth login`) or execute the GitHub Action version.

You can also run this from GitHub Actions:

```bash
gh workflow run bootstrap-github-org.yml
```

Admin-level repository settings are intentionally applied from an authenticated
maintainer shell, not from the default `GITHUB_TOKEN` workflow token:

```bash
DRY_RUN=1 ./scripts/bootstrap-github-settings.sh
./scripts/bootstrap-github-settings.sh
```

Run in dry-run mode from GitHub Actions:

```bash
gh workflow run bootstrap-github-org.yml -f dry_run=true
```

If you need direct command execution, keep the check names aligned with this workflow:

- `ci` (from `.github/workflows/ci.yml`)
- `vulncheck` (from `.github/workflows/security.yml`)
- `analyze` (from `.github/workflows/codeql.yml`)
- `check-milestone` (from `.github/workflows/milestone-check.yml`)
- `ensure-changelog` (from `.github/workflows/changelog-check.yml`)

## Maintainer toolchain

Validate the local development environment:

```bash
./scripts/dev-env-check.sh
```

Run the full local check gate:

```bash
./scripts/check.sh
```

The project expects Go `1.26.3`, GoReleaser `v2.16.0`, Gitleaks `v8.30.1`,
actionlint `v1.7.12`, and govulncheck `v1.1.4`.

## Milestone practice

- Create milestones for every release cycle before merging related changes.
- Track milestone planning and closing in [`docs/milestones.md`](docs/milestones.md).
- Keep issue and pull request assignment consistent with the target milestone.
- Only close milestones after all planned pull requests are merged and documented in the changelog.
