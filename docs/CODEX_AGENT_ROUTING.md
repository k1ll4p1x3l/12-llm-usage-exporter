# Codex Agent Routing Guide

Stand: 2026-05-30

Dieses Dokument ergänzt `AGENTS.md`. Es erklärt, wann welcher Subagent sinnvoll ist und wann der Hauptthread selbst entscheiden muss.

## Prinzipien

1. **Hauptthread entscheidet.** Architektur, Risiko, finale Abnahme und Nutzererklärung bleiben im Hauptthread.
2. **Read-only zuerst, wenn Scope unklar ist.** Mapping ist billiger als falsches Editieren.
3. **Kleinster ausreichender Worker.** Nicht jedes Problem braucht ein starkes Modell. Man kann auch mit einem Schraubendreher eine Schraube drehen, statt einen Bagger zu mieten.
4. **Review vor Abschluss.** Nicht-triviale Diffs gehen durch `code_review_gate` oder entsprechenden Security-/Source-Reviewer.
5. **Keine rekursive Agentenlawine.** Standard: max. Tiefe 1, max. 3–4 parallele Agenten.

## Routing nach Risiko

| Risiko | Beispiele | Vorgehen |
|---|---|---|
| Niedrig | README, kleine Texte, einfache Tests | direkter Worker, optional Review |
| Mittel | mehrdateiiger Bugfix, CI, Compose im Repo | Mapper → Worker → Review |
| Hoch | Security/Auth, Datenmigration, Storage, DNS, Firewall | Planner → Hauptthread → Patch Author → Security Review → Nutzerfreigabe |

## Typische Ketten

### Normales Feature

1. `requirements_analyst` bei unklarem Auftrag.
2. `code_mapper` für relevante Dateien.
3. `code_medium_worker` für Umsetzung.
4. `code_review_gate` für Review.
5. Hauptthread finalisiert und erklärt.

### Schwerer Bug

1. `code_mapper` und `code_test_triage` parallel, falls Budgetmodus nicht `low`.
2. Hauptthread entscheidet Fixstrategie.
3. `code_heavy_worker` oder `code_medium_worker` implementiert.
4. `code_review_gate` prüft.

### Neues Repo / unklare Struktur

1. `$repo-bootstrap` Skill.
2. `repo_bootstrapper` erstellt `PROJECT_PROFILE.md` und Task-Log.
3. Hauptthread erstellt erste Roadmap.

### Infrastruktur kritisch

1. `$infrastructure-change-control` Skill.
2. `infra_inventory` sammelt Fakten.
3. `infra_critical_planner` erstellt Plan.
4. Hauptthread prüft.
5. `infra_critical_patch_author` bereitet nur Repo-Patches vor.
6. `infra_security_reviewer` prüft.
7. Nutzerfreigabe vor Live-Anwendung.

### Recherche / Entscheidung

1. `$research-dossier` oder `$decision-record` Skill.
2. `research_mapper` für Quellenplan.
3. Hauptthread recherchiert mit aktuellen Quellen, falls nötig.
4. `source_reliability_reviewer` prüft Evidenz.
5. `decision_analyst` erstellt Optionenmatrix, wenn Entscheidung gewünscht.

## Eskalation an Hauptthread

Immer eskalieren bei:

- Architektur- oder Produktentscheidung.
- Security/Auth/Permissions.
- Datenverlust-/Migrationsrisiko.
- Irreversiblen oder produktiven Infrastrukturänderungen.
- Neue Dependencies oder externe Dienste.
- Unklare Tests, widersprüchliche Evidenz.
- Budgetmodus `critical`.
