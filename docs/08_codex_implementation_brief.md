# Codex Implementation Brief

## Allowed calls

- `account/read` with `refreshToken: false`
- `account/rateLimits/read`

## Transport

- Spawn and communicate with the local Codex app server process as configured.
- Use JSON-RPC 2.0 frame decoding.
- Never read `~/.codex/auth.json` in normal collection path.

## Mapping

- `account/read` -> account identifier and plan fields.
- `account/rateLimits/read` -> usage windows list.
- Missing required fields -> provider error status with no secret logging.
