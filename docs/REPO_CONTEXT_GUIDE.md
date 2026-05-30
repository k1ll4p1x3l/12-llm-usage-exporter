# Repo Context Guide

## Zweck

`PROJECT_PROFILE.md` reduziert Kontextkosten und Fehlentscheidungen. Der Agent muss dann nicht jedes Mal raten, ob `npm test`, `pytest`, `go test` oder ein ritueller Tanz um die CI-Pipeline nötig ist.

## Empfohlenes Minimum

- Projektzweck.
- Tech Stack.
- Installations-/Test-/Buildbefehle.
- wichtige Pfade.
- Deployment-/Infrastruktur-Bezug.
- Sicherheits- und Datenschutzrisiken.
- Definition of Done.
- bekannte offene Punkte.

## Erstellung

```bash
python3 scripts/create_repo_context.py --write
```

Das Skript erzeugt einen Vorschlag. Codex oder der Nutzer sollten ihn prüfen.
