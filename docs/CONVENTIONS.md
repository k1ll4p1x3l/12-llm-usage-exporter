# Development Conventions

## Language

All public project documentation, user-facing messages, and API-facing comments must be in English.

## Architecture rules

- Every provider path uses the same pipeline:
  `collector -> neutral model -> exporters`.
- Collectors only read local provider state via provider-specific approved methods.
- Exporters must not add provider-specific semantics to the neutral schema.

## Safety

- No credential persistence.
- No network collection outside provider transport channels.
- No scraping, header sniffing, or CLI credential file parsing.

## Error handling

- All external calls return either:
  - `ok` provider status with data, or
  - structured error status with redacted message.
- Collector schema drift is a hard error status, never silent adaptation.

## Metrics naming

- Prometheus metrics use base units and ratio semantics.
- Avoid unbounded labels and account-level high-cardinality labels by default.

## Release quality

- New code should include focused tests.
- New provider support requires a provider policy document.
