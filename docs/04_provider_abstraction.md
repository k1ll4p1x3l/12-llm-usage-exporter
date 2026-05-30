# Provider-Abstraktionskonzept

## Prinzipien

1. Provider-Collector sind austauschbar und isoliert.
2. Jeder Provider deklariert Fähigkeiten und Datenqualität.
3. Jeder Collector besitzt eine Policy-Allowlist für erlaubte lokale Methoden.
4. Das neutrale Modell darf keine providerinternen Annahmen erzwingen.
5. Instabile Datenquellen werden im Modell als solche markiert.

## Konzeptuelle Go-Schnittstellen

```go
type Collector interface {
    ID() ProviderID
    Capabilities(ctx context.Context) (Capabilities, error)
    Collect(ctx context.Context, req CollectRequest) (*Snapshot, error)
    Health(ctx context.Context) Health
}

type Capabilities struct {
    SupportsUsageWindows bool
    SupportsCredits      bool
    SupportsAccountInfo  bool
    SupportsPushUpdates  bool
    SourceQuality        SourceQuality
}
```

## Provider-Policy

Jeder Provider erhält eine Policy-Datei:

```yaml
provider: codex
allowed_methods:
  - account/read: { refreshToken: false }
  - account/rateLimits/read: {}
forbidden_methods:
  - login/*
  - account/read: { refreshToken: true }
  - token/*
forbidden_files:
  - ~/.codex/auth.json: read_contents
```

## Fehlerklassen

| Code | Bedeutung |
|---|---|
| `provider_not_installed` | CLI/App nicht gefunden |
| `provider_not_authenticated` | Provider meldet keine gültige Session |
| `provider_rpc_unavailable` | App Server nicht erreichbar |
| `provider_schema_changed` | Antwort nicht kompatibel |
| `permission_denied` | lokaler Zugriff verweigert |
| `policy_violation` | Collector wollte verbotene Aktion ausführen |

## Provider-Roadmap

- Codex: App Server, Rate Limits, Credits, Health.
- Claude Code: nur nach Nachweis stabiler lokaler maschinenlesbarer Usage-Daten.
- Gemini CLI: wegen Produktmigration/Quota-Änderungen zunächst Research-only.
- Cursor: erst mit stabiler CLI/API-Quelle; Analytics API wäre admin/API-key-basiert und damit separates Modul.
- GitHub Copilot: eher Admin-/API-Modul als lokaler read-only Agent, weil Usage Metrics API Tokens/Scopes erfordert.
