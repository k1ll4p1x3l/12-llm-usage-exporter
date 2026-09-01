# Repository Operations

Recommended GitHub settings for this repository:

- Branch protection on `main`
  - keep pull request and required-check workflow for normal changes
  - single-maintainer default: set required approving reviews to `0`, because
    GitHub does not count a pull request author's own approval toward required
    reviews
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
  - `.github/workflows/milestone-check.yml` enforces milestone assignment on
    human pull requests.
  - `.github/workflows/milestone-release-notes.yml` exports closed milestone items and can create/update a draft release.
  - `.github/workflows/changelog-check.yml` requires changelog updates unless
    explicitly labeled `no-changelog-required`.
  - Dependabot-authored PRs carrying the repository-owned `dependencies` label
    bypass the milestone and changelog bookkeeping checks. Code, security and
    branch-protection checks remain required.
- Release:
  - publish via tag push (`v*`) and GoReleaser workflow
  - keep release notes auto-generated or curated manually

## Contact-free repository previews

Render the intended milestones and labels without GitHub authentication or
network access:

```bash
./scripts/bootstrap-github-org.sh
```

The settings helper behaves the same way:

```bash
./scripts/bootstrap-github-settings.sh
```

Both scripts default to `DRY_RUN=1` and reject `DRY_RUN=0`. They only emit
shell-escaped command previews and canonical JSON payloads. They never invoke
`gh`, authenticate, or mutate a repository.

The manually dispatched workflow is also preview-only and has only
`contents: read`:

```bash
gh workflow run bootstrap-github-org.yml
```

Any later settings change is a separate live action outside these helpers. It
requires an exact target, current human approval, fresh readback, least-
privilege credentials, dry-run/diff where supported, independent verification,
and rollback planning. A printed preview never authorizes that action.

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

If authentication or elevated manual work is required, the script writes a
reviewable helper script to `.codex/state/manual-admin-steps.sh` by default.
Override `MANUAL_STEPS_FILE` to place it elsewhere.

Run the full local check gate:

```bash
./scripts/check.sh
```

The project expects Go `1.26.6`, GoReleaser `v2.16.0`, Syft `v1.44.0` for release SBOM
generation, Gitleaks `v8.30.1`, actionlint `v1.7.12`, and govulncheck
`v1.1.4`. The full check creates only an unpublished snapshot and verifies it
with `scripts/verify_release_artifacts.py`.

## Milestone practice

- Create milestones for every release cycle before merging related changes.
- Track milestone planning and closing in [`docs/milestones.md`](docs/milestones.md).
- Keep issue and pull request assignment consistent with the target milestone.
- Only close milestones after all planned pull requests are merged and documented in the changelog.
