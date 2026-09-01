# Repository policy

Status: consumer-owned working copy
Managed-by-source: no

## Scope

- Applies to this repository, its linked worktrees, automation, releases, and
  local development artifacts.
- The central Agent Core owns only the paths recorded in
  `.agent-core.lock.json`. Project code, workflows, documentation, and this
  policy remain consumer-owned.

## Worktree safety

- Normal work must use a linked worktree.
- The primary worktree blocks local tools until the user sends the exact
  standalone line `MAIN_WORKTREE_OK` for that session and repository.
- The hook may store only the resulting session marker outside the repository.
- Unknown or failed topology detection fails closed.

## Approval gates

- Live production, Homelab, monitoring, provider, and GitHub-setting changes
  require explicit current approval.
- External messages, releases, tags, commits, pushes, pull requests, and merges
  require the corresponding authorization.
- Destructive cleanup or difficult-to-recover changes require exact targets,
  a reviewed rollback, and explicit approval.
- New runtime dependencies and new provider transports require explicit scope
  confirmation, focused tests, and documentation.
- `scripts/bootstrap-github-org.sh`, `scripts/bootstrap-github-settings.sh`,
  and `.github/workflows/bootstrap-github-org.yml` are permanently
  preview-only. They must not authenticate, call GitHub, accept an apply mode,
  or hold write permissions.

## Immutable provider and security boundaries

- No credential storage, decoding, forwarding, proxying, login, logout, or
  refresh-token operations.
- Do not read provider credential blobs such as `~/.codex/auth.json` outside
  explicit deny-list test fixtures.
- No web UI scraping, header sniffing, browser automation, or MITM collection.
- Provider schema drift is an explicit error state, never silent adaptation.
- Follow `docs/SECURITY.md`, `docs/03_security_concept.md`, and the applicable
  policy under `docs/provider-policy/` before changing a collector.

## Public and private boundary

- Every tracked path is public-safe. Run the repository public-safety and
  secret scans before publication.
- Private operational notes belong only in ignored paths such as
  `references/local/`, `references/private/`, `.agent-state/`, or external
  protected systems.
- Never commit credentials, tokens, cookies, private keys, private topology,
  internal hostnames, private IP plans, personal data, or unsanitized usage
  snapshots.
- Only the central `public` Agent Core profile is permitted in this repository.

## Validation expectations

- Minimum code handoff: `gofmt`, `go test ./...`, `go vet ./...`, relevant
  focused tests, `git diff --check`, and documentation review.
- Concurrency-sensitive changes additionally require `go test -race ./...`.
- Release changes require an unpublished snapshot and independent verification
  of all six platform archives, archive members, checksums, and one valid SBOM
  per archive before the publishing job can start.
- Normal full gate: `./scripts/check.sh` with the tool versions documented in
  `VERSIONS.md`.
- Agent Core changes additionally require central `verify-consumer`, a second
  sync returning `noop`, public-safety scanning, and Hosted CI.
- Release work additionally follows `docs/release.md` and requires verified
  artifacts, checksums, SBOMs, tags, and GitHub release readback.
- A checkpoint is acceptable only when a missing external environment,
  credential, approval, or platform makes further safe progress impossible.

## Local conventions

- Branches use the `codex/` prefix for Codex work.
- Prefer Conventional Commit subjects and small, reviewable commits.
- Public documentation, user-facing messages, and API-facing comments are in
  English.
- Material behavior, automation, dependency, policy, and Agent Core changes
  update `CHANGELOG.md` plus the relevant documentation.
- Long-running state and resume evidence live in `docs/TASK_LOG.md`.
- Do not edit centrally managed files directly; update the central source and
  consume a new pinned artifact through a sync PR.
