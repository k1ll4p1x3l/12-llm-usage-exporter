# Roadmap und Milestones

## MVP-Definition

Ein lokal ausführbarer Go-Prozess erzeugt aus einem simulierten Codex-App-Server-Response einen validen JSON-Snapshot und Prometheus-Metriken. Noch keine echte Codex-Integration nötig.

## Pre-Alpha

Ziel: echte Codex-Integration auf Linux.

- Codex App Server Transport
- `account/read` mit `refreshToken:false`
- `account/rateLimits/read`
- JSON Export
- Prometheus Export
- systemd-user Beispiel
- Security Tests gegen verbotene Methoden
- README + Security Policy

## Alpha

- stabilisierte Konfiguration
- Integrationstests mit mehreren Codex-Versionen
- optionale App-Server-Notification-Unterstützung
- Paketierung für Linux amd64/arm64
- erste experimentelle Research-Collector für Claude/Gemini/Cursor ohne Release-Versprechen

## Beta

- Provider-SDK stabilisieren
- Windows/macOS prüfen
- InfluxDB/OpenTelemetry optional
- Grafana Beispiel-Dashboard als separater Ordner, nicht Primärprodukt

## Milestones

| Milestone | Ergebnis |
|---|---|
| M0 Research Freeze | Quellen, Scope, Security-Regeln final |
| M1 Skeleton | Repo-Struktur, CI, Docs, Modelltypen |
| M2 Mock Collector | Tests mit Fixtures, JSON + Prometheus |
| M3 Codex Integration | App Server read-only integriert |
| M4 Pre-Alpha Release | Linux Binary, Checksums, SBOM, Release Notes |
| M5 Provider Research | Claude/Gemini/Cursor/Copilot Evaluierungsberichte |
