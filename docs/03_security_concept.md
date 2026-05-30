# Security Concept

## Mandatory boundaries

- Never persist, rotate, proxy, or send provider credentials.
- Only read local provider RPC channels marked in provider policy.
- Forbidden data paths: `~/.codex/auth.json` and equivalent credential stores in normal operation.
- No browser automation, no UI scraping, no header sniffing.

## Error handling

- Provider schema mismatch must set provider status to `error`.
- Missing or restricted credentials must not crash the process; they must produce a health-aware snapshot.

## Privacy

- Hash or redact account identifiers.
- Avoid high-cardinality labels in Prometheus metrics by design.
