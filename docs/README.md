# Codex Agent Orchestration Pack — Public

Stand: 2026-05-30

Public-safe Variante: enthält keine privaten IPs, Hostnames, Domains, persönlichen Namen, Secrets oder lokalen Inventare.

Dieses Paket ist ein public-safe Drop-in-Orchestrierungsgerüst für GitHub-Repositories, die mit Codex bearbeitet werden sollen. Es ist absichtlich breit angelegt: Code, Infrastructure/IaC, Recherche, Datenanalyse, Automatisierung, Entscheidungsfindung und Schreibprojekte.

## Zweck

Der Hauptthread, idealerweise ein starkes Frontier-Modell, arbeitet als Orchestrator und finaler Reviewer. Subagenten übernehmen klar abgegrenzte, billigere oder risikoärmere Teilaufgaben. Ziel ist hoher Automatisierungsgrad ohne Kontrollverlust, Kapazitätsverbrennung oder „Agent hat produktives DNS umdekoriert“-Folklore.

## Installation

Aus diesem Paketordner heraus:

```bash
./scripts/install_into_repo.sh /pfad/zu/deinem/repo
```

Oder manuell in die Wurzel des Ziel-Repos kopieren:

```text
AGENTS.md
.codex/
.agents/skills/
docs/
templates/
scripts/
references/
```

## Empfohlener Start in einem Ziel-Repo

```bash
cd /pfad/zu/deinem/repo
python3 scripts/verify_codex_agent_pack.py
python3 scripts/create_repo_context.py --write
codex -m gpt-5.5
```

Startprompt:

```text
Nutze AGENTS.md und das Agent-Orchestration-Pack. Prüfe zuerst PROJECT_PROFILE.md und docs/TASK_LOG.md, falls vorhanden. Erstelle einen Plan, wähle passende Subagenten kostenbewusst aus und liefere am Ende Tests, Risiken, Erklärungen und nächste sichere Schritte.
```

## Wichtige Dateien

| Pfad | Zweck |
|---|---|
| `AGENTS.md` | zentrale Orchestrator-Anweisung |
| `.codex/config.toml` | Subagent-Parallelität und Laufzeitlimits |
| `.codex/agents/*.toml` | Custom Agents für Rollen und Kosten-/Risikostufen |
| `.agents/skills/*/SKILL.md` | progressive Workflows für Zieltypen |
| `docs/CODEX_AGENT_ROUTING.md` | detaillierte Routing-Regeln |
| `docs/CODEX_BUDGET_POLICY.md` | Budget-/Limitstrategie |
| `docs/LONG_RUNNING_AGENT_PROTOCOL.md` | Checkpoint-/Resume-Protokoll |
| `templates/` | Projektprofil, Task-Brief, Runbook, Entscheidung, Recherche |
| `scripts/codex_budget_guard.py` | manuelle Budgetstatus-Datei pflegen und Empfehlungen anzeigen |
| `scripts/create_repo_context.py` | Projektprofil aus Repo-Dateien vorschlagen |
| `scripts/verify_codex_agent_pack.py` | Syntax- und Strukturprüfung |
| `scripts/public_repo_sanity_check.py` | leichter Vorab-Scan gegen typische Public-Repo-Leaks |
| `docs/PUBLIC_REPO_SAFETY.md` | Checkliste für öffentliche Repositories |

## Budgetsteuerung

Codex kann nicht zuverlässig hellsehen, wie viel Kapazität im Konto noch frei ist. Wenn eine offizielle Usage-Anzeige, ein Limit-Banner oder ein vom Nutzer geposteter Stand verfügbar ist, wird dieser verwendet. Sonst arbeitet das Paket mit einem manuellen Status in `.codex/state/budget_status.json`.

Beispiele:

```bash
python3 scripts/codex_budget_guard.py init
python3 scripts/codex_budget_guard.py update --remaining-percent 35 --reset-at 2026-05-30T23:00:00+02:00
python3 scripts/codex_budget_guard.py status
python3 scripts/codex_budget_guard.py recommend --task-size heavy --risk high
```

## Public-Repo-Sicherheit

Diese Variante enthält bewusst keine privaten Kontextdateien. Private Topologie, IP-Pläne, Inventar, IAM-Details, lokale Budgetzustände und persönliche Daten gehören nicht in öffentliche Repositories.

Vor einem Push in ein öffentliches Repo ausführen:

```bash
python3 scripts/verify_codex_agent_pack.py
python3 scripts/public_repo_sanity_check.py
```

Der Scanner ist nur ein leichter Vorabcheck. Für echte Projekte zusätzlich einen etablierten Secret-Scanner wie `gitleaks` oder `trufflehog` nutzen. Textdateien haben leider keinen Selbsterhaltungstrieb.

## Validierung

```bash
python3 scripts/verify_codex_agent_pack.py
python3 scripts/public_repo_sanity_check.py
```

Erwartung: TOML-Dateien parsen, Pflichtfelder sind vorhanden, Skills haben `name` und `description`, zentrale Dateien existieren.
