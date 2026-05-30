# Product Requirements

## Functional requirements

1. Collect provider-local usage, quota, and credit signals for configured providers.
2. Use read-only collection paths for each provider.
3. Export normalized snapshots in JSON format.
4. Export Prometheus metrics on a configurable local endpoint.
5. Provide robust health state per provider and overall snapshot.
6. Implement atomic file writes for JSON output.
7. Redact account identifiers before persistence and export.
8. Expose CLI commands for serve, one-shot snapshot, config validation, and version.
9. Build CI, security checks, and release workflow.

## Non-functional requirements

- Linux primary target for pre-alpha.
- No login/refresh/token credential collection.
- No UI scraping and no secret persistence.
- Default public docs and interfaces in English.
