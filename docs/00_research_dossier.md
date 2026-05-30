# Recherche-Dossier: LLM Usage Exporter

**Stand:** 30.05.2026, Europe/Berlin  
**Ziel:** belastbares Fundament für ein Open-Source-Projekt zur lokalen Erfassung und Normalisierung von LLM-/Coding-Agent-Nutzungsdaten.

## Executive Summary

Die technisch tragfähigste Pre-Alpha-Strategie ist ein read-only OpenAI-Codex-Collector, der über den offiziellen Codex App Server Nutzungsfenster, Credits und Account-Metadaten ausliest, ohne selbst Authentifizierung zu besitzen. OpenAI Codex stellt über App-Server-Methoden und interne Rate-Limit-Snapshots die passendste lokale Maschinen-Schnittstelle bereit; `auth.json` und Credential Stores müssen dagegen als Geheimnisquellen behandelt und nicht geparst werden. Claude Code, Gemini CLI, Cursor und GitHub Copilot verfügen zwar über Usage-/Billing-Informationen, diese sind häufig webbasiert, admin-/API-key-gebunden oder nur halbmaschinenlesbar. Der erste Release sollte deshalb bewusst Codex-only sein und Provider-Abstraktion nur strukturell vorbereiten. Der größte Langfristrisikofaktor ist Anbieterdrift: Abrechnungsmodelle, lokale Dateien, Header und CLI-Ausgaben ändern sich schnell.

## Methodik

Untersucht wurden offizielle Produktdokumentationen, offizielle Repositories, Preis-/Quota-Dokumentationen, API-Referenzen, Help-Center-Artikel und ausgewählte Community-Issues. Quellen wurden nach Autorität, Aktualität, Nachvollziehbarkeit, Scope-Relevanz und Neutralität bewertet. Offizielle Provider-Dokumentation und Quellcode wurden als primär belastbar gewertet; GitHub Issues und Foren nur als Indiz für Stabilitäts- und Sicherheitsrisiken.

## Quellenlage nach Provider

| Provider | Offizielle Usage-/Limit-Daten | Lokale maschinenlesbare Quelle | Bewertung für Pre-Alpha |
|---|---:|---:|---|
| OpenAI Codex | Ja: Pricing, Usage Dashboard, Enterprise Analytics/Compliance; App-Server Rate Limits | Ja: App Server `account/rateLimits/read`; Header/SSE intern sichtbar | **geeignet** |
| Claude Code | Teilweise: `/status`, `/cost`, Limits als Meldungen, Enterprise/Team Hinweise | Kein stabiler lokaler Usage-API-Nachweis | später, vorsichtig |
| Gemini CLI | Ja: Quota-Doku, teils `/stats`; aber starke Produkt-/Migrationssignale | Unklar; CLI-Ausgabe vermutlich fragil | später, riskant |
| Cursor | Ja: Dashboard, Usage-Seite, Teams Analytics API, CLI `/usage` | CLI-Ausgabe und Dashboard; Analytics API admin/API-key-gebunden | später, kein Pre-Alpha |
| GitHub Copilot | Ja: Usage Metrics API, AI-Credits-Billing, CLI Auth über GitHub CLI/keychain | Lokale CLI/SKD über stdio; Usage eher API/admin/web | später, API-Key-Scope-Konflikt |

## OpenAI Codex: belastbare Befunde

1. Codex kann mit ChatGPT-Account oder API-Key verwendet werden; CLI/IDE teilen lokale Login-Zustände. Die lokalen Credentials können als `~/.codex/auth.json` oder im OS-Keyring liegen. `auth.json` enthält Zugriffstokens und ist als Passwortäquivalent zu behandeln.
2. Der Codex App Server stellt eine JSON-RPC-Schnittstelle für UIs und Automatisierungen bereit. Für das Projekt relevant sind `account/read` und `account/rateLimits/read`; `account/read` besitzt eine `refreshToken`-Option, die im Projekt **immer false** bleiben muss.
3. `account/rateLimits/read` liefert Rate-Limit-Snapshots mit Limit-IDs, Primär-/Sekundärfenstern, `usedPercent`, `windowDurationMins`, Reset-Zeiten, Plan-Typ und Credits.
4. Im Codex-Quellcode existiert Parsing für Header-Familien wie `x-codex-primary-used-percent`, `x-codex-primary-window-minutes`, `x-codex-primary-reset-at`, sekundäre Fenster und Credits. Das ist Evidenz für Datenherkunft, aber kein Freibrief für Header-Sniffing.
5. Enterprise Analytics/Compliance APIs sind wertvoll, benötigen aber Organisation-/Workspace-Rechte und API-Schlüssel. Sie widersprechen dem Pre-Alpha-Ziel „keine eigene Authentifizierung“ und gehören nicht in die erste Version.

## Offizielle, halb-offizielle und Community-Daten

| Kategorie | Beispiele | Stabilität | Nutzung im Projekt |
|---|---|---:|---|
| Offiziell/stabiler | Codex App Server stabile Methoden; OpenAI Pricing; GitHub Copilot Usage Metrics API; Prometheus Exporter-Konventionen | hoch bis mittel | bevorzugen |
| Offiziell, aber scope-fremd | OpenAI Enterprise Analytics/Compliance, Cursor Analytics API, GitHub Copilot org/enterprise metrics | hoch, aber Auth nötig | spätere Provider-Module mit klarer Auth-Grenze |
| Halb-offiziell/fragil | CLI-Slash-Command-Ausgaben wie `/status`, `/usage`, `/stats`; lokale JSONL-Rollouts | mittel bis niedrig | nur opt-in, nie als Standard |
| Community-Indizien | GitHub Issues zu `auth.json`, Rate-Limit-Headers, Token-Refresh-Problemen | niedrig | nur für Risikoanalyse |
| Ungeeignet | UI-Scraping, MITM/Proxy, direktes Token-Decoding, Refresh-Token-Nutzung | niedrig und sicherheitskritisch | ausschließen |

## Quellen

Siehe `docs/99_sources.md`.
