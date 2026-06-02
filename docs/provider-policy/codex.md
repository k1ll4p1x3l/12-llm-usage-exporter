---
provider: codex
---

# Codex Provider Policy

## Allowed operations

- `initialize` for JSON-RPC session setup only.
- `initialized` notification after successful JSON-RPC session setup.
- `account/read` with `refreshToken: false`.
- `account/rateLimits/read`.

## Forbidden operations

- Any token refresh/login/logout flow.
- Any `initialize` parameter that authenticates, refreshes, or mutates local
  provider state.
- Reading or forwarding `~/.codex/auth.json`.
- Header sniffing, browser automation, or UI scraping.
- Using provider credentials as pass-through secrets.

## Mapping expectations

- `account/read`: read-only account metadata only.
- `account/rateLimits/read`: normalize provider limits into `usage_windows`.
  Current App Server bucket responses are mapped from `rateLimitsByLimitId`
  when present and fall back to the backward-compatible single-bucket or legacy
  list shapes.
- Schema drift must fail the current snapshot with provider status `error`.
