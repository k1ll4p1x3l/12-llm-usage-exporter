# Codex Implementation Brief

## Allowed calls

- `initialize` for JSON-RPC session setup only.
- `initialized` notification after successful setup.
- `account/read` with `refreshToken: false`
- `account/rateLimits/read`

## Transport

- Spawn and communicate with the local Codex app server process as configured.
- The default local Codex CLI invocation is `codex app-server`, matching the
  current `codex-cli 0.134.0` subcommand name.
- Use JSON-RPC frame decoding. Current Codex App Server responses can omit the
  `jsonrpc` version field on the wire, so the client accepts either an omitted
  version or `2.0`.
- Run `initialize` before account calls so the App Server session is ready; do
  not use initialization to authenticate, refresh credentials, or mutate local
  provider state. After a successful initialize response, send the `initialized`
  notification required by the App Server lifecycle.
- Ignore unrelated App Server notifications while waiting for the matching
  response id.
- Never read `~/.codex/auth.json` in normal collection path.

## Mapping

- `account/read` -> hashed account identifier and plan fields. If a stable
  account id is absent, hash another returned account identifier such as email
  or account type; never persist the raw value.
- `account/rateLimits/read` -> usage windows. Prefer `rateLimitsByLimitId`
  bucket data when present. Codex percent-only buckets are represented as
  `used=<usedPercent>` and `limit=100` so existing ratio metrics remain stable
  while preserving the reported `used_percent`.
- Missing required fields -> provider error status with no secret logging.
