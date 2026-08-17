#!/usr/bin/env python3
"""Conservative policy annotations for local Codex lifecycle events.

This hook never auto-approves a request.  It can deny a known mutating tool in
an opt-in contracted run when the required action envelope is structurally
invalid.  Unknown and hosted tools remain subject to Codex and human policy;
the hook is a guardrail, not a complete enforcement boundary.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import run_guard


MUTATING_LOCAL_TOOLS = {"Bash", "apply_patch", "Edit", "Write", "write_file"}
TOOL_ZONES = {
    "read_local",
    "write_current_worktree",
    "external_read",
    "external_write_or_message",
    "live_or_privileged",
    "destructive_or_irreversible",
}
TOOL_APPROVALS = {"none", "prompt", "explicit-human"}
INTEGRATION_KINDS = {"mcp", "plugin", "app", "connector"}
DATA_CLASSES = {"public", "internal", "confidential", "secret-bearing"}
MUTATION_CLASSES = {"read-only", "write", "destructive", "mixed"}
APPROVAL_MODES = {"disabled", "prompt", "writes", "per-tool"}


def _event(payload: Dict[str, Any], fallback: Optional[str]) -> str:
    value = payload.get("hook_event_name")
    return value if isinstance(value, str) and value else fallback or ""


def _tool_name(payload: Dict[str, Any]) -> str:
    value = payload.get("tool_name")
    return value if isinstance(value, str) else ""


def _inventory_entry(
    root: Path, tool_name: str
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return an enabled inventory entry and reject malformed active inventory.

    The canonical consumer path is deliberately fixed.  A template elsewhere
    in the repository is documentation until it is copied to this path.
    """

    path = root / run_guard.STATE_DIRECTORY / "tool-inventory.json"
    inventory, error = run_guard._read_json_regular(
        path
    )
    if error:
        return None, error
    if inventory is None:
        return None, None
    if inventory.get("schema_version") != 1:
        return None, f"{path} schema_version must be 1"
    if set(inventory) != {"schema_version", "integrations"}:
        return None, f"{path} contains unknown or missing top-level fields"
    integrations = inventory.get("integrations", [])
    if not isinstance(integrations, list):
        return None, f"{path} integrations must be a list"
    found: Optional[Dict[str, Any]] = None
    seen_names = set()
    for integration in integrations:
        if not isinstance(integration, dict):
            return None, f"{path} integrations must contain objects"
        required = {
            "id", "kind", "owner", "data_class", "mutation",
            "approval_mode", "enabled", "last_reviewed", "tools",
        }
        missing = sorted(required - set(integration))
        if missing:
            return None, f"{path} integration missing fields: {missing}"
        if set(integration) != required:
            return None, f"{path} integration contains unknown fields"
        for field in ("id", "owner"):
            if not isinstance(integration.get(field), str) or not integration[field].strip():
                return None, f"{path} integration {field} must be non-empty"
        if integration.get("kind") not in INTEGRATION_KINDS:
            return None, f"{path} integration kind is invalid"
        if integration.get("data_class") not in DATA_CLASSES:
            return None, f"{path} integration data_class is invalid"
        if integration.get("mutation") not in MUTATION_CLASSES:
            return None, f"{path} integration mutation is invalid"
        if integration.get("approval_mode") not in APPROVAL_MODES:
            return None, f"{path} integration approval_mode is invalid"
        if not isinstance(integration.get("enabled"), bool):
            return None, f"{path} integration enabled must be boolean"
        try:
            date.fromisoformat(integration.get("last_reviewed", ""))
        except (TypeError, ValueError):
            return None, f"{path} integration last_reviewed must be an ISO date"
        tools = integration.get("tools", [])
        if not isinstance(tools, list):
            return None, f"{path} integration tools must be a list"
        for tool in tools:
            if not isinstance(tool, dict):
                return None, f"{path} tools must contain objects"
            if set(tool) != {"canonical_name", "zone", "approval"}:
                return None, f"{path} tool contains unknown or missing fields"
            name = tool.get("canonical_name")
            if not isinstance(name, str) or not name.strip():
                return None, f"{path} tool canonical_name must be non-empty"
            if name in seen_names:
                return None, f"{path} duplicate canonical tool name: {name}"
            seen_names.add(name)
            if tool.get("zone") not in TOOL_ZONES:
                return None, f"{path} tool {name} has invalid zone"
            if tool.get("approval") not in TOOL_APPROVALS:
                return None, f"{path} tool {name} has invalid approval"
            if integration["enabled"] and name == tool_name:
                found = tool
    return found, None


def _is_mutating(payload: Dict[str, Any], entry: Optional[Dict[str, Any]]) -> bool:
    name = _tool_name(payload)
    if name in MUTATING_LOCAL_TOOLS:
        return True
    return bool(
        entry
        and entry.get("zone")
        in {"write_current_worktree", "external_write_or_message", "live_or_privileged", "destructive_or_irreversible"}
    )


def _pre_tool_use(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    status = run_guard.load_status(payload)
    name = _tool_name(payload)
    entry, inventory_error = _inventory_entry(status.root, name)
    if name.startswith("mcp__") and (inventory_error or entry is None):
        reason = inventory_error or (
            "MCP tool is absent from the enabled consumer inventory at "
            f"{run_guard.STATE_DIRECTORY}/tool-inventory.json"
        )
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Untrusted MCP tool denied: {reason}",
            }
        }
    mutating = _is_mutating(payload, entry)
    if status.errors and mutating:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "Mutating tool denied because the opt-in run contract is invalid: "
                    + "; ".join(status.errors)
                ),
            }
        }
    contract = status.contract
    if contract is None or not mutating:
        return None
    enforcement = contract.get("enforcement", {})
    if not enforcement.get("action_envelope_required"):
        return None
    if contract.get("state") not in {"authorized", "executing", "verifying"}:
        reason = "Contracted mutating tool denied: run state is not authorized/executing/verifying."
    else:
        errors = run_guard._validate_action_envelope(status.root, contract)
        if not errors:
            return None
        reason = "Contracted mutating tool denied: " + "; ".join(errors)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _permission_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    name = _tool_name(payload) or "unknown tool"
    return {
        "systemMessage": (
            f"POLICY_GUARD: review {name} against exact target, scope, tool zone and current "
            "human authorization. Worktree permission, credentials, a run contract, or an action "
            "envelope do not themselves grant operational authority. This hook never auto-allows."
        )
    }


def _post_tool_use(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    status = run_guard.load_status(payload)
    entry, _ = _inventory_entry(status.root, _tool_name(payload))
    if not _is_mutating(payload, entry):
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "POLICY_GUARD: a potentially mutating tool has already run. PostToolUse cannot "
                "undo side effects. Record the exact result, perform independent readback, and "
                "stop on ambiguous or negative validation."
            ),
        }
    }


def _subagent_event(event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if event == "SubagentStart":
        message = (
            "POLICY_GUARD: accept only explicit responsibility and path ownership; preserve other "
            "agents' edits; do not recursively delegate unless the user explicitly authorized it."
        )
    else:
        message = (
            "POLICY_GUARD: rejoin with factual result, evidence, changed paths, tests and unresolved "
            "risks. The primary agent owns integration and final acceptance."
        )
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}}


def dispatch(payload: Dict[str, Any], fallback: Optional[str] = None) -> Optional[Dict[str, Any]]:
    event = _event(payload, fallback)
    if event == "PreToolUse":
        return _pre_tool_use(payload)
    if event == "PermissionRequest":
        return _permission_request(payload)
    if event == "PostToolUse":
        return _post_tool_use(payload)
    if event in {"SubagentStart", "SubagentStop"}:
        return _subagent_event(event, payload)
    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            raise ValueError("hook input must be a JSON object")
        result = dispatch(payload, sys.argv[1] if len(sys.argv) > 1 else None)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        event = sys.argv[1] if len(sys.argv) > 1 else "unknown"
        if event == "PreToolUse":
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"policy guard failed closed: {exc}",
                }
            }
        else:
            result = {"systemMessage": f"POLICY_GUARD check failed: {exc}"}
    if result is not None:
        sys.stdout.write(json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
