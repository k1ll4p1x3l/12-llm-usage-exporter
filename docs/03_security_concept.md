# Security Concept

## Mandatory boundaries

- Never persist, rotate, proxy, or send provider credentials.
- Only read local provider RPC channels marked in provider policy.
- Forbidden data paths: `~/.codex/auth.json` and equivalent credential stores in normal operation.
- No browser automation, no UI scraping, no header sniffing.
- No dynamic shell evaluation in repository automation. GitHub metadata and
  settings helpers render escaped previews only and reject any apply request.

## Error handling

- Provider schema mismatch must set provider status to `error`.
- Missing or restricted credentials must not crash the process; they must produce a health-aware snapshot.

## Privacy

- Hash or redact account identifiers.
- Avoid high-cardinality labels in Prometheus metrics by design.
- Public-repository scanning rejects symlinks, special files, private-reference
  paths, control characters, high-confidence credentials, and private network
  identifiers without printing matched values.

## Supply chain

- Dependabot groups minor/patch Go and Actions updates to reduce partial pin
  drift; major changes remain independently reviewable.
- The currently reviewed major action updates and module updates are
  consolidated in one branch and pinned by immutable action commit or
  `go.sum`; the seven superseded hosted PRs must not be closed until the
  replacement PR is merged.
- Pull-request CI runs the Go race detector and builds an unpublished
  GoReleaser snapshot.
- The release contract requires Linux, macOS, and Windows archives for amd64
  and arm64, safe archive members, matching checksums, and a recognized,
  non-empty SBOM for every archive.
