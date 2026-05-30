# Neutrales Datenmodell

## JSON Snapshot v1alpha1

```json
{
  "schema_version": "usage.snapshot.v1alpha1",
  "generated_at": "2026-05-30T12:00:00Z",
  "agent": {
    "name": "llm-usage-exporter",
    "version": "0.0.0-prealpha",
    "hostname_hash": "sha256:..."
  },
  "providers": [
    {
      "provider_id": "codex",
      "collector_version": "0.0.0-prealpha",
      "source": {
        "type": "codex_app_server",
        "quality": "official_documented",
        "experimental": false
      },
      "account": {
        "auth_owner": "provider_client",
        "auth_mode": "chatgpt_or_api_key_observed",
        "plan_type": "redacted_or_provider_value",
        "subject_hash": null
      },
      "health": {
        "status": "ok",
        "last_success_at": "2026-05-30T12:00:00Z",
        "last_error_code": null,
        "stale": false
      },
      "usage_windows": [
        {
          "limit_id": "codex",
          "limit_name": "Codex Local",
          "window_kind": "primary",
          "scope": "local_or_shared",
          "unit": "percent",
          "used_percent": 42.0,
          "window_duration_seconds": 18000,
          "resets_at": "2026-05-30T16:30:00Z",
          "evidence": "account/rateLimits/read"
        }
      ],
      "credits": {
        "has_credits": true,
        "unlimited": false,
        "balance_display": "redacted_or_provider_value"
      }
    }
  ]
}
```

## Prometheus-Metriken

| Metrik | Typ | Labels | Bedeutung |
|---|---|---|---|
| `llm_usage_provider_up` | Gauge | `provider` | 1 wenn letzter Scrape erfolgreich war |
| `llm_usage_provider_last_success_timestamp_seconds` | Gauge | `provider` | Unix-Zeit letzter Erfolg |
| `llm_usage_provider_scrape_errors_total` | Counter | `provider`, `error_code` | Fehlerzähler |
| `llm_usage_window_used_percent` | Gauge | `provider`, `limit_id`, `window_kind` | Verbrauchtes Fenster in Prozent |
| `llm_usage_window_duration_seconds` | Gauge | `provider`, `limit_id`, `window_kind` | Fensterdauer |
| `llm_usage_window_reset_timestamp_seconds` | Gauge | `provider`, `limit_id`, `window_kind` | Reset-Zeit |
| `llm_usage_credits_balance` | Gauge | `provider` | numerischer Credit-Bestand, nur wenn sicher parsebar |
| `llm_usage_credits_info` | Gauge | `provider`, `has_credits`, `unlimited` | Credit-Info ohne Freitextbalance |
| `llm_usage_account_info` | Gauge | `provider`, `auth_mode`, `plan_type` | Info-Metrik, Wert 1, ohne E-Mail/User-ID |

## Prometheus-Designregeln

- Keine E-Mails, Account-IDs, Conversation-IDs, Request-IDs oder Dateipfade in Labels.
- Units im Metriknamen: `_seconds`, `_percent`, `_total`.
- Label-Kardinalität strikt begrenzen.
- Provider-spezifische Details nicht als freie Labels, sondern in JSON exportieren.
