#!/usr/bin/env python3
"""Manual budget guard for Codex orchestration.

This does not call OpenAI APIs. It records a user- or UI-provided usage estimate
and prints conservative routing recommendations for AGENTS.md workflows.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
STATE = ROOT / ".codex" / "state" / "budget_status.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def mode_for(percent: float | None) -> str:
    if percent is None:
        return "normal"
    if percent < 5:
        return "critical"
    if percent < 20:
        return "low"
    if percent < 50:
        return "conserve"
    return "normal"


def read_state() -> dict[str, Any]:
    if not STATE.exists():
        return {
            "updated_at": now_iso(),
            "remaining_percent": None,
            "reset_at": None,
            "mode": "normal",
            "notes": "No budget status recorded. Treat as unknown/normal with conservative defaults.",
        }
    return json.loads(STATE.read_text(encoding="utf-8"))


def write_state(data: dict[str, Any]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def recommendation(mode: str, task_size: str, risk: str) -> str:
    if mode == "critical":
        return "Do not start new work. Write checkpoint/resume plan with long_context_summarizer."
    if mode == "low":
        if risk == "high" or task_size == "heavy":
            return "Avoid starting. Run only read-only mapping or checkpoint; ask main thread for prioritization."
        return "Run sequentially. Prefer mini/spark agents. Checkpoint after this step."
    if mode == "conserve":
        if task_size == "heavy" or risk == "high":
            return "Map first with read-only agent, then decide. Max 1 implementation agent and 1 review agent."
        return "Max 2 parallel agents. Prefer mapper/triage before implementation."
    return "Normal routing allowed. Keep fan-out <= 4 and use smallest sufficient model."


def cmd_init(args: argparse.Namespace) -> None:
    data = read_state()
    write_state(data)
    print(f"Initialized {STATE}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_update(args: argparse.Namespace) -> None:
    percent = args.remaining_percent
    data = {
        "updated_at": now_iso(),
        "remaining_percent": percent,
        "reset_at": args.reset_at,
        "mode": mode_for(percent),
        "notes": args.notes or "Manual update.",
    }
    write_state(data)
    print(f"Updated {STATE}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_status(args: argparse.Namespace) -> None:
    data = read_state()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()
    print(recommendation(data.get("mode", "normal"), "medium", "medium"))


def cmd_recommend(args: argparse.Namespace) -> None:
    data = read_state()
    print(f"mode={data.get('mode', 'normal')} task_size={args.task_size} risk={args.risk}")
    print(recommendation(data.get("mode", "normal"), args.task_size, args.risk))


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual Codex budget guard")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("init")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("update")
    p.add_argument("--remaining-percent", type=float, required=True)
    p.add_argument("--reset-at", default=None, help="ISO timestamp, preferably with timezone")
    p.add_argument("--notes", default=None)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("status")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("recommend")
    p.add_argument("--task-size", choices=["small", "medium", "heavy"], default="medium")
    p.add_argument("--risk", choices=["low", "medium", "high"], default="medium")
    p.set_defaults(func=cmd_recommend)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
