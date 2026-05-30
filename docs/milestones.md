# Milestone Operations

This project uses GitHub milestones as the planning unit for each release cycle.
The workflow and PR checks treat milestone assignment as a required maintainer habit.

## Standard workflow

1. Create a new milestone in GitHub before merging the first change for that release.
2. Assign each issue and PR that targets the same release to the milestone.
3. Keep issue scope, code changes, and changelog updates inside the milestone boundary.
4. Only close the milestone once all planned PRs are merged and changelog entries are present.

## GitHub CLI examples

Create a milestone:

```bash
gh api repos/<OWNER>/<REPO>/milestones \
  -X POST \
  -f title="0.2" \
  -f state="open" \
  -f description="Hardening and resilience"
```

Assign an issue and PR batch to a milestone:

```bash
for n in $(gh issue list --state open --search "milestone:0.2" --json number -q '.[].number'); do
  gh issue edit "$n" --milestone "0.2"
done
for n in $(gh pr list --state open --search "milestone:0.2" --json number -q '.[].number'); do
  gh pr edit "$n" --milestone "0.2"
done
```

Export milestone release notes:

```bash
gh workflow run milestone-release-notes.yml \
  -f milestone_number=12 \
  -f release_tag=v0.2.0
```

Alternatively, dispatch by title:

```bash
gh workflow run milestone-release-notes.yml \
  -f milestone_title="0.2" \
  -f release_tag=v0.2.0
```

To just generate a notes artifact without creating/updating a release, omit `release_tag`.

The workflow writes a markdown artifact named:

- `milestone-<number>-release-notes.md`

and posts/updates a draft release when a tag is supplied.

## Review check before closing a milestone

- Open items in the milestone are now in scope and should be either intentionally deferred
  or moved before closing.
- If a PR is in-progress, re-open the milestone and re-run planning rather than forcing completion.
- The release should only be published after changelog and docs are updated for all merged changes.
