# Public Repo Safety Checklist

Stand: 2026-05-30

Öffentliche Repositories dürfen generische Arbeitsregeln, Coding-Standards, Agentenrollen, Templates und öffentliche Dokumentation enthalten. Sie dürfen keine lokalen Topologieinformationen, personenbezogenen Daten, Secrets, Zugangsdaten oder privaten Betriebszustände enthalten.

## Vor jedem öffentlichen Push

```bash
python3 scripts/verify_codex_agent_pack.py
python3 scripts/public_repo_sanity_check.py
```

Zusätzlich empfohlen:

```bash
gitleaks detect --source .
```

## Nicht veröffentlichen

- echte interne Hostnames oder private Domains
- private IP-Pläne, VLAN-Tabellen, Firewall-Regeln oder erreichbare Topologie
- personenbezogene Daten, Familien-/Gastkonten, Kundennamen oder interne Rollen
- API-Schlüssel, Tokens, Cookies, Recovery Codes, Private Keys oder Passwörter
- lokale Budgetstände, private Inventare oder operative Notizen

## Öffentlich unkritisch

- generische Agentenrollen
- generische Infrastruktur-Change-Control
- Budget- und Orchestrierungsregeln ohne Kontodaten
- Templates ohne echte Werte
