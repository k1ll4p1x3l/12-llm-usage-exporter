# Arbeitsbrief für spätere automatisierte Codex-Umsetzung

## Unverhandelbare Regeln

1. Implementiere zuerst Tests, dann Collector.
2. Keine Authentifizierungslogik implementieren.
3. Keine Tokens lesen, speichern, decodieren oder loggen.
4. Keine Login-, Logout-, Refresh- oder Device-Auth-Methoden verwenden.
5. `account/read` ausschließlich mit `refreshToken:false`.
6. `auth.json` darf nur als verbotener Pfad in Tests vorkommen, nicht als Datenquelle.
7. Prometheus-Labels dürfen keine E-Mail, User-ID, Account-ID, Request-ID, Conversation-ID oder lokalen Pfad enthalten.
8. Bei unbekanntem JSON-RPC-Schema: Fehlerstatus exportieren, nicht raten.

## Empfohlene Implementierungsreihenfolge

1. `internal/model` mit Snapshot-Strukturen.
2. `internal/exporters/json` mit atomarem Write.
3. `internal/exporters/prometheus` mit statischem Fixture.
4. `internal/collectors/codex` JSON-RPC Client gegen Mock-Server.
5. Policy-Layer, der nur erlaubte Methoden durchlässt.
6. Integration gegen echten `codex app-server` auf Linux.
7. CLI-Konfiguration und systemd-user Beispiel.
8. Release-Workflow.

## Testfälle

- Forbidden method test: Versuch `account/read refreshToken:true` muss fehlschlagen.
- Secret canary test: Fixture enthält fake token; Ausgabe darf ihn nicht enthalten.
- Schema drift test: unbekannte Felder ignorieren, fehlende Pflichtfelder Health-Fehler.
- Prometheus label test: keine verbotenen Labels und gültige Units.
- Provider unavailable test: Codex nicht installiert/gestartet.
