---
provider: claude-code
status: deferred
checked: 2026-05-31
---

# Claude Code Provider Policy

## Current decision

Claude Code collection is deferred until this project has a documented, local,
read-only source for quota windows or subscription usage that does not read
credentials or require billing-role API access.

## Allowed future operations

- Read documented local telemetry output produced by Claude Code OpenTelemetry
  configuration, if the user explicitly enables that telemetry outside this
  exporter.
- Normalize non-secret usage counters that are already available in a local
  metrics/log backend controlled by the user.

## Forbidden operations

- Reading Claude Code authentication tokens, API keys, or helper outputs.
- Running login, refresh, account-switch, or credential helper flows.
- Scraping terminal output, UI state, browser sessions, or web account pages.
- Treating approximate cost telemetry as authoritative billing data.

## Source assessment

Anthropic documents Claude Code settings, including user/project settings and
environment variables that may contain authentication material. Those files are
not valid collector inputs for this project.

Anthropic also documents Claude Code OpenTelemetry metrics. The documented cost
metric is approximate, and the official guidance is to use the billing provider
for official billing data. That makes OTel useful for optional future
observability, but not a safe default quota source for this exporter.
