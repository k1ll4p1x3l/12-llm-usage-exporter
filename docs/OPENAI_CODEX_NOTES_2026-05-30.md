# OpenAI Codex Notes — 2026-05-30

Diese Datei ist eine knappe Arbeitsnotiz für dieses Pack. Vor produktiver Übernahme sollten die offiziellen OpenAI-Dokumente erneut geprüft werden.

## Relevante offizielle Konzepte

- `AGENTS.md` kann global und repo-lokal genutzt werden; `AGENTS.override.md` kann näher am Arbeitsverzeichnis spezialisieren.
- Projektlokale `.codex/config.toml`-Dateien werden nur in trusted projects geladen.
- Custom Agents liegen unter `.codex/agents/*.toml` oder `~/.codex/agents/*.toml` und benötigen `name`, `description`, `developer_instructions`.
- Repo-Skills liegen unter `.agents/skills/.../SKILL.md` und werden progressiv geladen.
- Rules unter `.codex/rules/*.rules` sind experimentell; dieses Pack liefert deshalb nur Beispiele, keine automatisch aktive harte Policy.
- Permission Profiles sind neuer als ältere `sandbox_mode`-Einstellungen und sollten nicht mit diesen gemischt werden.

## Quellen

- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/config-reference
- https://developers.openai.com/codex/subagents
- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/rules
- https://developers.openai.com/codex/permissions
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://help.openai.com/en/articles/20001106-codex-rate-card
