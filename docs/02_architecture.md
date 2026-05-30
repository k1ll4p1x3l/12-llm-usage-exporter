# Architekturvorschlag

## Zielarchitektur

```text
cmd/llm-usage-exporter
  -> internal/config
  -> internal/service/scheduler
  -> internal/collectors/codex
  -> internal/model
  -> internal/exporters/json
  -> internal/exporters/prometheus
```

## Komponenten

### Collectors

Provider-spezifische Adapter. Jeder Collector darf nur die Schnittstellen verwenden, die im Provider-Policy-Dokument freigegeben sind.

Pre-Alpha:

```text
internal/collectors/codex/
  appserver_client.go      # JSON-RPC Transport zu Codex App Server
  collector.go             # Mapping Codex -> neutrales Modell
  policy.go                # erlaubte/verbotene Methoden
  fixtures/                # JSON-RPC Testdaten
```

Später:

```text
internal/collectors/claude/
internal/collectors/gemini/
internal/collectors/cursor/
internal/collectors/copilot/
```

### Model

Neutrales, providerunabhängiges Datenmodell. Provider-spezifische Details landen in `evidence` und `source`, nicht in Prometheus-Labels.

### Exporters

- `json`: atomarer Datei-Write via temporäre Datei + Rename
- `prometheus`: lokaler HTTP-Server, Default `127.0.0.1:9738/metrics`
- später: `stdout`, `influxdb`, OpenTelemetry

### Service

- Scheduler mit Jitter
- Backoff bei Provider-Fehlern
- Signal-Handling
- Konfigurationsvalidierung

## Bewertete Datenquellen für OpenAI Codex

| Datenquelle | Bewertung | Entscheidung |
|---|---|---|
| Codex App Server `account/rateLimits/read` | offiziell dokumentiert, maschinenlesbar | **Standard** |
| Codex App Server Notifications | geeignet für spätere Push-Updates | später |
| `~/.codex/auth.json` | enthält Secrets | nicht lesen |
| OS-Keyring | Credential Store, kein Usage-Store | nicht lesen |
| lokale JSONL-Rollouts | potentiell nützlich, aber fragil/personenbezogen | optional später |
| Header-Sniffing | technisch sichtbar, aber fragil/sicherheitskritisch | vermeiden |
| ChatGPT/Codex Usage-Webseite | UI-Scraping fragil | vermeiden |
| Enterprise Analytics API | stabil, aber API-Key/Auth nötig | später separates Admin-Modul |

## Datenfluss Pre-Alpha

1. Scheduler triggert Collector.
2. Codex Collector startet oder verbindet zu Codex App Server.
3. Collector ruft `account/read` mit `refreshToken:false` auf.
4. Collector ruft `account/rateLimits/read` auf.
5. Mapping in `model.Snapshot`.
6. Validierung: keine Secrets, keine E-Mail in Default-Export.
7. JSON-Exporter schreibt Datei.
8. Prometheus-Exporter aktualisiert Registry.

## Konfigurationsentwurf

```toml
[server]
listen_address = "127.0.0.1:9738"
metrics_path = "/metrics"

[polling]
interval = "60s"
jitter = "10s"
timeout = "5s"

[export.json]
enabled = true
path = "~/.local/state/llm-usage-exporter/snapshot.json"

[providers.codex]
enabled = true
codex_home = "~/.codex"
transport = "stdio-app-server"
allow_experimental_api = false
redact_account_identifiers = true
```
