# Research Dossier

## Scope

- Provider focused: OpenAI Codex pre-alpha.
- Transport focus: official Codex App Server JSON-RPC only.
- Exclusions: UI scraping, proxy/MITM collection, direct local auth file parsing.

## Key references

- OpenAI Codex App Server JSON-RPC API documentation.
- Official Prometheus exporter and naming guidance.
- Go module ecosystem and Go project conventions for production-style command tooling.

## Findings used in design

- Snapshot output should be atomic and deterministic.
- Refresh token flows should remain disabled in standard collection mode (`refreshToken: false`).
- The project should remain read-only for provider credentials.
