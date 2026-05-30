# Sicherheitskonzept

## Sicherheitsleitbild

Der Agent ist ein Beobachter. Er darf keine Identität besitzen, keine Tokens verwalten und keine Autorisierungsentscheidung treffen. Authentifizierung, Refresh und Session-Lebenszyklus bleiben vollständig beim Provider-Client, im Pre-Alpha-Fall bei OpenAI Codex.

## Harte Verbote

- Kein Aufruf von `codex login`, Login-JSON-RPC-Methoden oder Device-Auth-Flows.
- Kein `account/read` mit `refreshToken:true`.
- Kein Lesen, Decodieren, Kopieren oder Persistieren von `auth.json`-Inhalten.
- Kein Zugriff auf OS-Keyring-APIs.
- Kein Speichern von API-Keys, OAuth-Tokens, Refresh-Tokens, Cookies oder Passwörtern.
- Kein Proxy, MITM, TLS-Intercept oder Header-Sniffing.
- Kein Umgehen oder Verlängern von Nutzungslimits.

## Erlaubte Handlungen

- Starten eines Codex App Servers als Kindprozess, sofern Codex selbst die Authentifizierung hält.
- Nutzung stabiler read-only JSON-RPC-Methoden.
- Lesen nicht-geheimer Konfigurations- und Statusdaten.
- Exportieren normalisierter Usage-/Health-Metriken.

## Datenklassifikation

| Datenart | Beispiel | Klassifikation | Default-Verhalten |
|---|---|---|---|
| Secret | Access Token, Refresh Token, API-Key | verboten | nie lesen/exportieren |
| Personenbezug | E-Mail, User-ID, Account-ID | sensibel | redigieren/hashen |
| Quota-Daten | Used %, Reset-Zeit, Window-Dauer | operational | exportieren |
| Plan-Typ | Plus, Pro, Business | potentiell sensibel | optional, standardmäßig erlaubt ohne Personendaten |
| Fehlerdetails | RPC-Fehler, Provider nicht erreichbar | operational | exportieren, aber redigiert |

## Threat Model Kurzfassung

| Bedrohung | Risiko | Gegenmaßnahme |
|---|---|---|
| Token-Exfiltration durch falsches Parsen von `auth.json` | hoch | `auth.json` nie öffnen; Tests mit Canary-Secrets |
| Versehentliche Token-Erneuerung | hoch | Method-Allowlist; `refreshToken:false`; Mock-Tests |
| Preisgabe von E-Mail/User-ID via Prometheus-Labels | mittel | Redaction Default; keine personenbeziehbaren Labels |
| Hohe Label-Kardinalität | mittel | Limit-IDs normalisieren; keine Request-IDs in Labels |
| Provider-API-Drift | hoch | Quellenqualität im Snapshot; Contract Tests; Versionserkennung |
| Lokaler Port remote erreichbar | mittel | Default bind nur `127.0.0.1`; Doku für Reverse Proxy |
| Debug-Logs enthalten Secrets | hoch | zentraler Redactor; Tests mit Secret Patterns |

## Logging-Regeln

- Kein Dump roher JSON-RPC-Antworten im Standardlog.
- Debug-Logs nur nach expliziter Aktivierung.
- Redactor vor jeder Logausgabe.
- Request-/Conversation-IDs nur wenn nicht personenbeziehbar und nicht geheim; sonst auslassen.

## Betriebsmodell

Empfohlen ist ein systemd user service unter dem Benutzer, der auch Codex verwendet. Rootbetrieb ist weder nötig noch erwünscht.
