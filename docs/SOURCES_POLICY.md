# Sources Policy

## Source hierarchy

1. Primary sources for implementation and behavior: official docs (provider API, language, CI, packaging).
2. Versioned standards and release notes (vendor/tooling changes over time).
3. Reputable repositories and standards bodies.
4. Community sources only for operational examples, never as authority for security policy.

## Mandatory source logging

- Any externally significant fact used in implementation decisions is logged in `docs/99_sources.md`.
- Changes driven by API behavior or protocol assumptions include date and source URL.
- For volatile facts and rapidly changing APIs, at least two independent sources are preferred.
