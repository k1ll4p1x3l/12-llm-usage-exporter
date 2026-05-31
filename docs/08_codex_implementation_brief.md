# Codex Implementation Brief

## Allowed calls

- `initialize` for JSON-RPC session setup only.
- `account/read` with `refreshToken: false`
- `account/rateLimits/read`

## Transport

- Spawn and communicate with the local Codex app server process as configured.
- Use JSON-RPC 2.0 frame decoding.
- Run `initialize` before account calls so the App Server session is ready; do
  not use initialization to authenticate, refresh credentials, or mutate local
  provider state.
- Never read `~/.codex/auth.json` in normal collection path.

## Mapping

- `account/read` -> account identifier and plan fields.
- `account/rateLimits/read` -> usage windows list.
- Missing required fields -> provider error status with no secret logging.
