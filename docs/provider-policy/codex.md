---
provider: codex
---

# Codex Provider Policy

## Allowed operations

- `account/read` with `refreshToken: false`.
- `account/rateLimits/read`.

## Forbidden operations

- Any token refresh/login/logout flow.
- Reading or forwarding `~/.codex/auth.json`.
- Header sniffing, browser automation, or UI scraping.
- Using provider credentials as pass-through secrets.

## Mapping expectations

- `account/read`: read-only account metadata only.
- `account/rateLimits/read`: normalize provider limits into `usage_windows`.
- Schema drift must fail the current snapshot with provider status `error`.
