# Safety Boundaries

Stand: 2026-05-30

## Allgemein verboten ohne explizite Freigabe

- Produktive Daten löschen oder migrieren.
- Firewall, Routing, DNS, VPN, IAM, SSH, Secrets, Backups oder Storage live ändern.
- Service-Restarts oder Deployments in produktiven Umgebungen.
- Neue externe Dienste aktivieren.
- Secrets ausgeben, kopieren oder in Dateien schreiben.
- Öffentliche Scans oder offensive Security-Aktionen.

## Erlaubt ohne Live-Freigabe

- Repository-Dateien lesen.
- Patches vorbereiten.
- Templates erstellen.
- Dry-run-/Validierungsskripte schreiben.
- Lokale Syntaxchecks und Tests ausführen, sofern sie nicht produktiv wirken.
- Risiko- und Rollbackpläne erstellen.

## Stop-and-ask bzw. Stop-and-escalate

- Befehl könnte außerhalb des Repos wirken.
- Unklar, ob Zielumgebung produktiv ist.
- Änderung betrifft Identitäten, Rechte oder Datenintegrität.
- Backup-/Restore-Stand unbekannt.
- Tests fehlen für kritische Änderung.
