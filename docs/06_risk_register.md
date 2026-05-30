# Risk Register

## Key risks

- Provider schema drift causing collection failures.
- Accidental token refresh flow through misconfigured RPC calls.
- High cardinality in metrics labels.
- Collector process startup and transport instability.

## Mitigations

- Schema mapping is strict by default and yields explicit errors.
- Collector policy files enforce allowed RPC methods.
- Prometheus labels intentionally limited to provider and limit identifiers.
- Exponential restart and clear diagnostics from service loop.
