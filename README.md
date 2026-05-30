# llm-usage-exporter

**Status:** Konzept / Pre-Alpha-Planung  
**Primärziel:** Lokale Nutzungs-, Quota-, Credit- und Reset-Daten von LLM-/Coding-Agent-Installationen erfassen, normalisieren und in Monitoring-Formate exportieren.  
**Pre-Alpha-Scope:** OpenAI Codex, Linux, Go, JSON-Datei, Prometheus `/metrics`, keine GUI, kein Dashboard, keine eigene Authentifizierung.

## Projektprinzip

`llm-usage-exporter` ist ein Datenübersetzer, kein Ersatzclient:

```text
Provider-spezifische lokale Datenquelle
  -> Collector
  -> neutrales internes Datenmodell
  -> Exporter
  -> Monitoring-Systeme wie Prometheus/Grafana
```

Der Agent darf vorhandene lokale Provider-Sessions nur beobachtend nutzen. Er darf keine OAuth-Refreshes auslösen, keine Tokens rotieren, keine Credentials speichern und keine Limits umgehen.

## Wichtigste Architekturentscheidung

Für OpenAI Codex ist die bevorzugte Pre-Alpha-Quelle der offizielle Codex App Server bzw. dessen JSON-RPC-Methoden `account/read` und `account/rateLimits/read`, mit `refreshToken:false` und ohne Login-/Refresh-/Token-Flows. Direkte Auswertung von `~/.codex/auth.json`, Header-Sniffing oder UI-Scraping ist als Standardpfad ausgeschlossen.

## Repository-Inhalt

- `docs/00_research_dossier.md` – Recherche, Quellenlage, Vergleich der Provider
- `docs/01_lastenheft.md` – vollständiges technisches Lastenheft
- `docs/02_architecture.md` – Zielarchitektur und Komponenten
- `docs/03_security_concept.md` – Sicherheitsmodell und Threat Model
- `docs/04_provider_abstraction.md` – Provider-Plugin-Konzept
- `docs/05_data_model.md` – neutrales Datenmodell und Prometheus-Metriken
- `docs/06_risk_register.md` – Risikoregister
- `docs/07_roadmap_milestones.md` – Roadmap, MVP, Pre-Alpha, Alpha
- `docs/08_codex_implementation_brief.md` – Arbeitsbrief für spätere Codex-Umsetzung
- `.github/workflows/*` – CI-/Security-Workflow-Vorschläge

## Lizenzempfehlung

Apache-2.0 wird empfohlen, weil das Projekt als Integrations- und Infrastrukturkomponente von einer permissiven Lizenz mit explizitem Patent-Grant profitiert.
