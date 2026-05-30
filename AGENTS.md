# AGENTS.md

## Zweck dieser Datei

Diese Datei enthält verbindliche Arbeitsanweisungen für Codex und andere Coding Agents in diesem Repository. Sie soll Codex ermöglichen, dieses Projekt weitgehend autonom, reproduzierbar und sicher weiterzuentwickeln, ohne bei jeder Kleinigkeit menschliche Zeremonien zu verlangen. Menschen sind schon langsam genug.

Projektname: `llm-usage-exporter`  
Projektstatus: Konzept / Pre-Alpha-Planung  
Primärsprache der Implementierung: Go  
Primärplattform Pre-Alpha: Linux  
Hauptziel: lokale Nutzungs-, Quota-, Credit- und Reset-Daten von LLM-/Coding-Agent-Installationen erfassen, normalisieren und exportieren.

Der Agent ist ein Datenübersetzer, kein Authentifizierungsclient, kein Dashboard und kein GUI-Projekt.

```text
Provider-spezifische lokale Datenquelle
  -> Collector
  -> neutrales internes Datenmodell
  -> Exporter
  -> Monitoring-System