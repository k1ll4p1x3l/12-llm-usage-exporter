# Technisches Lastenheft

## 1. Zielbestimmung

`llm-usage-exporter` soll lokale Nutzungs- und Kontingentdaten von LLM-/Coding-Agent-Installationen erfassen, normalisieren und exportieren. Das Projekt ist kein Dashboard, kein GUI-Projekt und kein Authentifizierungsclient.

## 2. Pre-Alpha-Scope

### Enthalten

- Provider: OpenAI Codex
- Plattform: Linux primär
- Sprache: Go
- Betrieb: CLI und optional systemd-user-service
- Exporter: JSON-Datei, Prometheus `/metrics`
- Authentifizierung: ausschließlich bestehende lokale Codex-Installation
- Datenquelle: Codex App Server JSON-RPC, bevorzugt stabile Methoden

### Ausgeschlossen

- GUI, Webfrontend, eigener Dashboard-Server
- eigene Authentifizierung
- OAuth-Login, Token-Refresh, Token-Rotation
- Speicherung von Zugangsdaten
- Lesen oder Parsen von Tokens aus `auth.json`
- Limit-Umgehung, Session-Manipulation, Proxy-/MITM-Ansätze
- produktive Unterstützung weiterer Provider in Pre-Alpha

## 3. Funktionale Anforderungen

| ID | Muss/Soll | Anforderung |
|---|---|---|
| F-001 | Muss | Collector für OpenAI Codex bereitstellen. |
| F-002 | Muss | `account/rateLimits/read` auswerten, ohne Login-/Refresh-Methoden aufzurufen. |
| F-003 | Muss | `account/read` nur mit `refreshToken:false` verwenden. |
| F-004 | Muss | Internes neutrales Snapshot-Modell erzeugen. |
| F-005 | Muss | JSON-Snapshot atomar auf Datei schreiben. |
| F-006 | Muss | Prometheus `/metrics` auf `127.0.0.1` bereitstellen. |
| F-007 | Muss | Geheimnisse in Logs, JSON und Metrics redigieren. |
| F-008 | Muss | Collector-Fehler als Health-Daten exportieren, nicht verschlucken. |
| F-009 | Soll | Provider-Registry für künftige Provider vorbereiten. |
| F-010 | Soll | Konfiguration via TOML/YAML und Environment Overrides. |
| F-011 | Soll | systemd-user-unit als Beispiel bereitstellen. |
| F-012 | Kann | Opt-in Debug-Modus für Raw-Snapshots ohne Secrets. |

## 4. Nichtfunktionale Anforderungen

| ID | Kategorie | Anforderung |
|---|---|---|
| NF-001 | Sicherheit | Prozess läuft ohne Root-Rechte. |
| NF-002 | Sicherheit | Keine Secrets im Speicher persistieren; kein Credential-Cache. |
| NF-003 | Datenschutz | Account-Identifikatoren standardmäßig hashen oder redigieren. |
| NF-004 | Stabilität | Collector-Ausfälle dürfen Exporter nicht blockieren; letzter erfolgreicher Snapshot bleibt mit Staleness-Kennzeichnung verfügbar. |
| NF-005 | Observability | Jede Quelle erhält `source`, `quality`, `collected_at`, `collector_version`. |
| NF-006 | Performance | Polling-Intervall standardmäßig konservativ, z. B. 60 Sekunden oder länger. |
| NF-007 | Portabilität | Architektur darf macOS/Windows später erlauben, aber Linux bleibt Pre-Alpha-Ziel. |
| NF-008 | Wartbarkeit | Provider-spezifischer Code bleibt unter `internal/collectors/<provider>`. |

## 5. Akzeptanzkriterien Pre-Alpha

- Auf einem Linux-System mit angemeldetem Codex CLI kann ein Snapshot erzeugt werden.
- Der Snapshot enthält mindestens Provider-Health, Plan-Typ soweit verfügbar, Limit-Fenster, Used-Percent, Reset-Zeit und Datenqualität.
- Prometheus liefert valides Textformat ohne hochkardinale oder geheime Labels.
- Ein automatisierter Test beweist, dass keine Login-/Refresh-Methode des App Servers aufgerufen wird.
- Der Prozess funktioniert weiter, wenn Codex nicht erreichbar ist, und exportiert einen klaren Fehlerstatus.
