#!/usr/bin/env python3
"""Create a conservative PROJECT_PROFILE.md draft from visible repository files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path.cwd()


def exists(*parts: str) -> bool:
    return (ROOT.joinpath(*parts)).exists()


def detect() -> dict:
    stack: list[str] = []
    commands: dict[str, str] = {}
    notes: list[str] = []

    if exists("package.json"):
        stack.append("Node.js/JavaScript/TypeScript")
        try:
            pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
            scripts = pkg.get("scripts", {})
            for key in ["test", "lint", "build", "dev", "start"]:
                if key in scripts:
                    commands[key] = f"npm run {key}" if key not in {"start", "test"} else f"npm {key}"
        except Exception as exc:  # noqa: BLE001
            notes.append(f"package.json could not be parsed: {exc}")
    if exists("pnpm-lock.yaml"):
        commands = {k: v.replace("npm", "pnpm", 1) for k, v in commands.items()}
        notes.append("pnpm-lock.yaml found; prefer pnpm over npm if project uses it consistently.")
    if exists("yarn.lock"):
        notes.append("yarn.lock found; verify package manager before installing dependencies.")
    if exists("pyproject.toml") or exists("requirements.txt"):
        stack.append("Python")
        commands.setdefault("test", "pytest")
        if exists("ruff.toml") or exists("pyproject.toml"):
            commands.setdefault("lint", "ruff check .")
    if exists("go.mod"):
        stack.append("Go")
        commands.setdefault("test", "go test ./...")
        commands.setdefault("build", "go build ./...")
    if exists("Cargo.toml"):
        stack.append("Rust")
        commands.setdefault("test", "cargo test")
        commands.setdefault("build", "cargo build")
    if exists("docker-compose.yml") or exists("compose.yml") or exists("docker-compose.yaml") or exists("compose.yaml"):
        stack.append("Docker Compose")
        notes.append("Compose file found. Do not run productive `up -d` without explicit approval.")
    if exists(".github", "workflows"):
        stack.append("GitHub Actions")
    if exists("ansible.cfg") or exists("playbooks"):
        stack.append("Ansible")
        notes.append("Ansible detected. Do not run playbooks against live hosts without approval.")

    return {"stack": sorted(set(stack)) or ["Unknown"], "commands": commands, "notes": notes}


def render(profile: dict) -> str:
    commands = profile["commands"]
    rows = []
    for purpose in ["install", "test", "lint", "build", "run local"]:
        cmd = commands.get(purpose.replace(" ", "_"), commands.get(purpose, ""))
        rows.append(f"| {purpose} | `{cmd}` | {'verify' if not cmd else ''} |")
    notes = "\n".join(f"- {n}" for n in profile["notes"]) or "- Keine automatisch erkannten besonderen Hinweise."
    stack = ", ".join(profile["stack"])
    return f"""# PROJECT_PROFILE

Stand: AUTO-DRAFT, bitte prüfen

## Zweck

Noch ausfüllen. Dieser Entwurf wurde automatisch aus sichtbaren Repo-Dateien erzeugt.

## Tech Stack

{stack}

## Wichtige Pfade

| Pfad | Zweck |
|---|---|
| `AGENTS.md` | Codex-Orchestrierungsregeln |
| `.codex/agents/` | Custom Agents |
| `.agents/skills/` | Repo-Skills |
| `docs/` | Projekt- und Betriebsdokumentation |

## Befehle

| Zweck | Befehl | Hinweise |
|---|---|---|
{chr(10).join(rows)}

## Sicherheits-/Datenschutzrisiken

- Noch prüfen.
- Secrets niemals committen.
- Produktive Infrastrukturänderungen nur mit Plan, Rollback und Freigabe.

## Deployment / Infrastruktur / Infrastruktur

- Noch prüfen.

## Definition of Done

- Relevante Tests/Checks laufen oder Abweichung ist begründet.
- Änderungen sind zusammengefasst.
- Risiken und Rollback sind dokumentiert, falls relevant.

## Automatisch erkannte Hinweise

{notes}

## Offene Punkte

- Projektzweck präzisieren.
- Verlässliche Install-/Test-/Buildbefehle bestätigen.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write PROJECT_PROFILE.md if absent, otherwise PROJECT_PROFILE.draft.md")
    args = parser.parse_args()
    content = render(detect())
    if args.write:
        target = ROOT / "PROJECT_PROFILE.md"
        if target.exists():
            target = ROOT / "PROJECT_PROFILE.draft.md"
        target.write_text(content, encoding="utf-8")
        print(f"Wrote {target.relative_to(ROOT)}")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
