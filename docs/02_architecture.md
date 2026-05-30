# Architecture

## Layered flow

```text
cli -> service -> collectors -> model -> exporters -> files/metrics
```

## Modules

- `cmd/llm-usage-exporter`: command entrypoints.
- `internal/config`: configuration parsing and validation.
- `internal/collectors`: provider interfaces and implementation packages.
- `internal/model`: neutral internal representation.
- `internal/exporters`: JSON and Prometheus exports.
- `internal/service`: scheduler and orchestration.
- `internal/redact`: PII-safe redaction helpers.

## Execution modes

- `serve`: periodic polling.
- `snapshot`: single run, print and/or write snapshot.
- `validate-config`: validate effective configuration.
