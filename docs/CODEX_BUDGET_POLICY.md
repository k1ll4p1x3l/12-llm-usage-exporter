# Codex Budget and Limit Policy

Stand: 2026-05-30

## Ziel

Dieses Paket soll Kapazitätslimits schonen, indem es starke Modelle für Entscheidungen und Reviews reserviert und günstigere Agenten für klar abgegrenzte Arbeit nutzt.

## Was zuverlässig geht

- Parallelität begrenzen.
- Kleine Modelle für read-heavy Aufgaben verwenden.
- Kontextumfang reduzieren.
- Checkpoints schreiben, bevor Limits erreicht werden.
- Manuelle Budgetstatus-Datei nutzen.
- Bei offiziellen Limitwarnungen stoppen und Resume-Plan liefern.

## Was nicht zuverlässig geht

Codex kann nicht garantiert aus dem Repo heraus den exakten verbleibenden ChatGPT-/Codex-Kontostand sehen. Wenn keine offizielle Usage-Anzeige, kein Limit-Banner und kein vom Nutzer bereitgestellter Status verfügbar ist, ist jede Prozentzahl nur manuell oder heuristisch. Genauigkeit herbeizaubern ist weiterhin kein unterstütztes Dateiformat.

## Budgetstatus-Datei

Pfad:

```text
.codex/state/budget_status.json
```

Schema:

```json
{
  "updated_at": "2026-05-30T21:00:00+02:00",
  "remaining_percent": 60,
  "reset_at": "2026-05-31T02:00:00+02:00",
  "mode": "normal",
  "notes": "manual update from Codex usage panel"
}
```

## Modi

| Mode | Verbleibend | Verhalten |
|---|---:|---|
| normal | >50 % oder unbekannt | 3–4 Subagenten, normale Umsetzung |
| conserve | 20–50 % | max. 2 Subagenten, keine unnötigen Heavy-Läufe |
| low | 5–20 % | sequenziell, nur Mini/Spark außer Blocker |
| critical | <5 % | Checkpoint schreiben, keine neue Arbeit starten |

## Modell-/Agentenwahl

- `gpt-5.4-mini`: Mapping, Triage, Inventar, Datenprofiling.
- `gpt-5.3-codex-spark`: kleine Patches, Doku, Boilerplate.
- `gpt-5.3-codex`: normale Implementierung, CI/CD, Datenanalyse.
- `gpt-5.4`: schwere Teilaufgaben, Review, Planung.
- Frontier-Hauptthread: Orchestrierung, finale Entscheidung, schwierige Erklärungen.

## Checkpoint-Pflicht

Checkpoint schreiben bei:

- Wechsel in `low` oder `critical`.
- Nach jedem abgeschlossenen Meilenstein.
- Vor riskanten Infrastructure-/Security-/Datenänderungen.
- Wenn mehr als ungefähr 10 Dateien betroffen sind.
- Vor längeren Test-/Build-Läufen, falls Budget knapp ist.

Nutze `long_context_summarizer`.
