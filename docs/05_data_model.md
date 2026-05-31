# Data Model

## Snapshot schema

- `schema_version`: `usage.snapshot.v1alpha1`
- `generated_at`: snapshot generation time
- `source`: source application (default `local-collectors`)
- `agent`: exporter identity
- `health`: overall status and message
- `providers`: list of provider snapshots

## Provider snapshot

- Provider id and type
- Provider status (`ok` / `error`)
- Account block with hashed account identifier and optional plan metadata
- Usage windows with `limit_id`, `limit_name`, `used`, `limit`, `used_percent`, `window_duration_mins`, and optional `resets_at`

## Prometheus mapping

- `llm_usage_window_used_ratio`: ratio of used / limit.
- `llm_usage_window_used` / `llm_usage_window_limit`: raw numeric gauges.
- `llm_usage_window_reset_timestamp_seconds`: reset deadline.
- `llm_usage_provider_health`: provider health signal.

## JSON Schema

The versioned JSON schema is tracked at
[`schemas/usage.snapshot.v1alpha1.json`](../schemas/usage.snapshot.v1alpha1.json).
Schema changes must be additive while the snapshot remains `v1alpha1`, unless
the changelog explicitly calls out a breaking pre-alpha adjustment.
