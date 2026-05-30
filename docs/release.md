# Release Process

This project uses milestone-first release management with optional automation in
GitHub Actions.

## Prerequisites

- Milestone exists and includes the scoped issues/PRs for the release.
- PRs merged are linked to the same milestone.
- `CHANGELOG.md` is updated for user-visible and operational changes.

## Recommended sequence

1. Freeze the milestone:
   - Resolve and close planned PRs.
   - Reassign or defer any out-of-scope issue.
2. Generate milestone notes:
   - Dispatch `.github/workflows/milestone-release-notes.yml` with:
     - `milestone_number` (preferred) or `milestone_title`
     - optional `release_tag` (for creating/updating a draft release)
3. Review notes artifact and adjust draft release text manually if needed.
4. Create and push a semver tag (for example `v0.1.0`).
5. Let `.github/workflows/release.yml` publish archives and SBOM.
6. Keep milestone open until release notes, changelog, and version docs match
   the published state.
7. Optional local release validation (preflight):

```bash
go install github.com/goreleaser/goreleaser/v2@latest
goreleaser check
goreleaser release --snapshot --skip=publish --clean
```

## Reference commands

Dispatch release notes workflow by number:

```bash
gh workflow run milestone-release-notes.yml \
  -f milestone_number=12 \
  -f release_tag=v0.1.0
```

Dispatch by title:

```bash
gh workflow run milestone-release-notes.yml \
  -f milestone_title="0.1"
```

## Rollback/forward notes

- If the draft release is incomplete, re-run the milestone workflow after
  milestone changes and edit the release notes.
- Keep release actions explicit: create new tags only at final release decision
  points, and use follow-up workflow runs only to refine draft notes.
