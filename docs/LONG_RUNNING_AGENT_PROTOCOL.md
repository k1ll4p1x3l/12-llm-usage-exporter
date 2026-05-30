# Long-running Agent Protocol

Stand: 2026-05-30

## Ziel

Lang laufende Aufgaben sollen fortsetzbar bleiben, selbst wenn Kontext, Budget oder Geduld der beteiligten Spezies enden.

## Regeln

1. Immer ein sichtbares Ziel und Done-Kriterien definieren.
2. Arbeit in Meilensteine schneiden.
3. Je Meilenstein maximal eine Hauptänderung.
4. Tests/Checks nach jedem relevanten Meilenstein.
5. `docs/TASK_LOG.md` aktuell halten.
6. Bei Budgetmodus `low` nur noch den aktuellen Meilenstein sauber abschließen oder checkpointen.
7. Bei Budgetmodus `critical` keine neuen Agenten starten.

## TASK_LOG-Struktur

```markdown
# Task Log

## Active goal

## Current plan

## Completed

## Changed files

## Checks

## Open risks

## Next safe step

## Resume prompt
```

## Resume-Prompt

Ein guter Resume-Prompt enthält:

- Ziel.
- aktueller Stand.
- relevante Dateien.
- letzte Tests.
- offene Risiken.
- nächste sichere Aktion.
- verbotene Aktionen.

## Stop-Bedingungen

Stoppe und liefere Resume-Plan bei:

- Limitwarnung oder Budget `critical`.
- unklarem Risiko.
- produktiver Infrastrukturberührung ohne Freigabe.
- fehlenden Tests, die für Sicherheit nötig wären.
- widersprüchlichen Anforderungen.
