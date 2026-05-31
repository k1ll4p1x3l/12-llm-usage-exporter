# Provider Abstraction

## Collector interface

Each collector implements:

- `ID() string`
- `Capabilities() []string`
- `Collect(ctx) (ProviderSnapshot, error)`

## Provider policy

- All providers are validated against a provider policy document under `docs/provider-policy/<provider>.md`.
- Policy violations are surfaced as provider `error` state.
- New providers require:
  - dedicated collector package
  - policy doc
  - integration tests for schema mapping
- Provider candidates may be documented as deferred when no safe, local,
  read-only source exists yet. Deferred providers must not be accepted in
  runtime configuration until a collector and tests are added.

## Policy evolution

- Schema changes are treated as breaking unless mapped intentionally.
- Unknown fields are ignored only when non-sensitive and when they do not change semantics.
