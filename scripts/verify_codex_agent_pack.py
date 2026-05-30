#!/usr/bin/env python3
"""Validate the Codex Agent Orchestration Pack.

Checks:
- .codex/config.toml parses as TOML
- every .codex/agents/*.toml parses as TOML
- required custom-agent fields exist
- known model and sandbox values are used
- .agents/skills/*/SKILL.md contains frontmatter with name and description
- important root/docs files exist
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    print("Python 3.11+ is required because tomllib is part of the standard library there.", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
AGENTS_DIR = ROOT / ".codex" / "agents"
CONFIG = ROOT / ".codex" / "config.toml"
SKILLS_DIR = ROOT / ".agents" / "skills"
REQUIRED_AGENT_FIELDS = {"name", "description", "developer_instructions"}
ALLOWED_MODELS = {
    "gpt-5.5",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.3-codex",
    "gpt-5.3-codex-spark",
}
ALLOWED_SANDBOX = {"read-only", "workspace-write", "danger-full-access"}
REQUIRED_FILES = [
    "AGENTS.md",
    ".codex/config.toml",
    "docs/CODEX_AGENT_ROUTING.md",
    "docs/CODEX_BUDGET_POLICY.md",
    "docs/LONG_RUNNING_AGENT_PROTOCOL.md",
    "templates/project/PROJECT_PROFILE.template.md",
]


def load_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"TOML parse error in {path.relative_to(ROOT)}: {exc}") from exc


def parse_skill_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"')
    return data


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")

    if CONFIG.exists():
        config = load_toml(CONFIG)
        agents_cfg = config.get("agents", {})
        if agents_cfg.get("max_depth", 1) > 1:
            warnings.append("agents.max_depth > 1 can cause recursive fan-out and higher usage.")
        if agents_cfg.get("max_threads", 0) > 6:
            warnings.append("agents.max_threads > 6 may burn usage quickly.")

    if not AGENTS_DIR.exists():
        errors.append(f"missing {AGENTS_DIR.relative_to(ROOT)}")
    else:
        files = sorted(AGENTS_DIR.glob("*.toml"))
        if not files:
            errors.append("no agent TOML files found")
        seen_names: set[str] = set()
        for path in files:
            data = load_toml(path)
            missing = REQUIRED_AGENT_FIELDS - data.keys()
            if missing:
                errors.append(f"{path.name}: missing required fields: {', '.join(sorted(missing))}")
            name = data.get("name")
            if isinstance(name, str):
                if name in seen_names:
                    errors.append(f"{path.name}: duplicate agent name {name!r}")
                seen_names.add(name)
                if path.stem != name:
                    warnings.append(f"{path.name}: filename stem differs from name {name!r}")
            else:
                errors.append(f"{path.name}: field 'name' must be a string")
            model = data.get("model")
            if model is not None and model not in ALLOWED_MODELS:
                errors.append(f"{path.name}: unexpected model {model!r}")
            sandbox = data.get("sandbox_mode")
            if sandbox is not None and sandbox not in ALLOWED_SANDBOX:
                errors.append(f"{path.name}: unexpected sandbox_mode {sandbox!r}")
            for field in REQUIRED_AGENT_FIELDS:
                if field in data and not isinstance(data[field], str):
                    errors.append(f"{path.name}: field {field!r} must be a string")

    if SKILLS_DIR.exists():
        skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
        if not skill_files:
            warnings.append(".agents/skills exists but contains no SKILL.md files")
        seen_skills: set[str] = set()
        for path in skill_files:
            fm = parse_skill_frontmatter(path)
            name = fm.get("name")
            desc = fm.get("description")
            if not name or not desc:
                errors.append(f"{path.relative_to(ROOT)}: missing frontmatter name or description")
            if name in seen_skills:
                warnings.append(f"duplicate skill name: {name}")
            if name:
                seen_skills.add(name)
    else:
        warnings.append("no .agents/skills directory found")

    agents_md = ROOT / "AGENTS.md"
    if agents_md.exists():
        size = agents_md.stat().st_size
        if size > 65536:
            warnings.append(f"AGENTS.md is {size} bytes; consider shortening or moving details to skills/docs")

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"- {w}")

    if errors:
        print("Validation failed:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    agent_count = len(list(AGENTS_DIR.glob("*.toml"))) if AGENTS_DIR.exists() else 0
    skill_count = len(list(SKILLS_DIR.glob("*/SKILL.md"))) if SKILLS_DIR.exists() else 0
    print(f"OK: {agent_count} custom agents and {skill_count} skills validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
