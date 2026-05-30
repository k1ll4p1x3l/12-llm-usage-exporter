# AGENTS.md

## Scope

This repository builds `llm-usage-exporter`, a local data translator for usage and quota telemetry from LLM coding agents.

- Project name: `llm-usage-exporter`
- Language: Go
- Primary pre-alpha platform: Linux
- Main objective: collect usage, limit, credit, and reset data and export it in neutral JSON and Prometheus formats
- Explicitly out of scope: authentication clients, web dashboards, web scraping, token vaulting, or quota bypass

## Architecture

```text
Provider data source
  -> Collector
  -> Neutral model
  -> Exporter
  -> Monitoring
```

## Core policy

- The project must be read-only with respect to provider sessions and credentials.
- No credential reading, rotation, or persistence in this project.
- No login, logout, token refresh, or MITM/proxy collection paths.
- Collectors must only use local provider paths documented in their provider policy.
- Any design change that increases risk must be recorded in project docs and justified.

## Operating rules

- Keep code changes in small, reviewable diffs.
- Any repository change should be reflected in `CHANGELOG.md` and `README.md`.
- Run lint/test commands in the affected scope before merging release changes.
- Dangerous operations require explicit user confirmation.
- Keep public documentation in English; operational private notes are external to this repository.
