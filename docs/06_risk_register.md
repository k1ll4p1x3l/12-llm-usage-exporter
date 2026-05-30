# Risikoregister

| ID | Risiko | Eintritt | Auswirkung | Bewertung | Gegenmaßnahme |
|---|---:|---:|---:|---:|---|
| R-001 | Codex App Server Schema ändert sich | mittel | hoch | hoch | Contract Tests, Schema-Versionen, graceful degradation |
| R-002 | Collector triggert versehentlich Token-Refresh | niedrig | sehr hoch | hoch | Method-Allowlist, Tests, `refreshToken:false` hart kodiert |
| R-003 | `auth.json` wird versehentlich gelesen/logged | niedrig | sehr hoch | hoch | File denylist, Canary Tests, Security Review |
| R-004 | Prometheus exportiert personenbeziehbare Labels | mittel | hoch | hoch | Redaction Default, Label-Linter |
| R-005 | Anbieter verschiebt Billing-Modell | hoch | mittel | hoch | neutrales Modell mit `unit`, `source_quality`, `evidence` |
| R-006 | Provider CLI nicht installiert/angemeldet | hoch | niedrig | mittel | Health-Metriken und klare Fehlercodes |
| R-007 | Community-Workarounds werden als stabil missverstanden | mittel | mittel | mittel | Dokumentierte Quellenklassen |
| R-008 | GitHub/Cursor/Gemini API braucht eigene Tokens | hoch | hoch | hoch | nicht im Pre-Alpha-Scope; später separates Admin-Modul |
| R-009 | Lokaler `/metrics` Port offen im Netzwerk | niedrig | mittel | mittel | Default localhost, Security-Doku |
| R-010 | Quota-Werte wirken exakt, sind aber verzögert | mittel | mittel | mittel | `collected_at`, `source`, Staleness und Qualität exportieren |
