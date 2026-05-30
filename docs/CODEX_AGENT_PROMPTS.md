# Beispiel-Prompts für Codex mit diesem Pack

## Universalstart

```text
Nutze AGENTS.md und das Agent-Orchestration-Pack. Hauptthread bleibt Orchestrator, Risiko-Owner und finaler Reviewer. Wähle Subagenten kostenbewusst aus, halte Scope klein, führe passende Checks aus und erkläre mir am Ende Was/Warum/Wie prüfen/Risiken/Rollback.
```

## Neues Repo vorbereiten

```text
Nutze $repo-bootstrap. Erstelle ein konservatives PROJECT_PROFILE.md, falls keines existiert. Erkenne Stack, Test-/Buildbefehle, CI, Risiken und offene Punkte. Keine Dependencies installieren, keine produktiven Befehle ausführen.
```

## Langes Ziel / Goal Mode

```text
Nutze $long-running-goal und $budget-aware-orchestration. Zerlege das Ziel in kleine Meilensteine, aktualisiere docs/TASK_LOG.md nach jedem Meilenstein und stoppe mit Resume-Plan, wenn Budgetmodus low oder critical erreicht wird.
```

## Budgetstatus setzen

```text
Aktualisiere .codex/state/budget_status.json anhand meiner Angabe: remaining_percent=35, reset_at=2026-05-30T23:00:00+02:00. Danach arbeite im conserve-Modus.
```

## Normales Coding-Feature

```text
Erstelle zuerst Akzeptanzkriterien. Nutze code_mapper für relevante Dateien und Tests. Implementiere mit code_medium_worker in einem kleinen Patch. Danach code_review_gate. Hauptthread finalisiert und erklärt.
```

## Kleines TODO

```text
Nutze code_simple_worker für dieses isolierte TODO. Scope: nur betroffene Funktion und direkte Tests. Keine neuen Dependencies, keine Architekturänderung. Danach schnelle Checks und Diff-Zusammenfassung.
```

## Schwerer Bug

```text
Nutze code_mapper und code_test_triage, um Ursache, betroffene Dateien und Testsignale zu sammeln. Entscheide danach, ob code_medium_worker reicht oder code_heavy_worker nötig ist. code_review_gate vor finaler Abnahme.
```

## Infrastruktur kritisch

```text
Nutze $infrastructure-change-control. Diese Änderung betrifft kritische Infrastruktur. Zuerst infra_inventory, dann infra_critical_planner mit Impact, Rollback, Validierung und Freigabepunkten. Keine Live-Änderungen ausführen.
```

## Recherche

```text
Nutze $research-dossier. Erstelle Leitfrage, Scope, Suchstrategie, Quellenpriorität und Aktualitätsgrenzen. Bevorzuge Primärquellen. Prüfe Quellen mit source_reliability_reviewer. Liefere Executive Summary, Methodik, Ergebnisse, Risiken, Empfehlung und Quellen.
```

## Datenanalyse

```text
Nutze $data-analysis-project. Prüfe zuerst Datenqualität mit data_quality_auditor. Erstelle dann reproduzierbare Analyse mit data_analyst. Originaldaten nicht überschreiben. Ergebnisse mit Einheiten, Filtern, Annahmen und Reproduktionsbefehl liefern.
```

## Entscheidungsvorlage

```text
Nutze $decision-record. Formuliere Optionen, Kriterien, Gewichtung, Pro/Contra, Risiken, Reversibilität und klare Empfehlung. Wenn Fakten fehlen, markiere Unsicherheiten statt zu raten.
```

## Schreibprojekt

```text
Nutze $writing-project. Erstelle zuerst Outline, Zielgruppe, Ton und Konsistenzregeln. Arbeite abschnittsweise. Keine Fakten erfinden, Recherchebedarf markieren.
```
