# Human Explanation Standard

Stand: 2026-05-30

Der Nutzer möchte nachvollziehen, was passiert, auch wenn er nicht jedes Detail selbst entwickeln könnte. Deshalb muss jede nicht-triviale Antwort verständlich erklären.

## Minimum

```text
## Was wurde geändert?
...

## Warum wurde es so gelöst?
...

## Wie kann ich prüfen, dass es funktioniert?
...

## Welche Risiken bleiben?
...

## Wie mache ich es rückgängig?
...

## Lernnotiz
...
```

## Stil

- Fachbegriffe kurz erklären.
- Keine unnötige Theorie.
- Keine falsche Sicherheit.
- Keine „einfach“-Floskeln bei Dingen, die für Anfänger nicht einfach sind.
- Konkrete Dateipfade, Befehle und erwartete Ergebnisse nennen.

## Für Infrastruktur

Zusätzlich immer:

- Impact auf Dienste/Netzwerk/Daten.
- Pre-checks.
- Rollback.
- Validierung nach Änderung.
- Freigabepunkte.

## Für Recherche

Zusätzlich immer:

- Stichtag.
- Quellenqualität.
- widersprüchliche Quellen.
- Annahmen und Unsicherheiten.
