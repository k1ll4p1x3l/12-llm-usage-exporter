#!/usr/bin/env python3
"""Optional lifecycle guard for long, explicitly contracted Codex runs.

The guard reads consumer-owned state from ``.agent-state``.  It validates
structure and continuity only: neither the run contract nor the action
envelope grants authority.  Human approval must still exist in the current
conversation and all normal Codex sandbox/approval checks still apply.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


STATE_DIRECTORY = ".agent-state"
CONTRACT_NAME = "run-contract.json"
CHECKPOINT_NAME = "checkpoint.json"
EVIDENCE_NAME = "evidence.json"
ENVELOPE_NAME = "action-envelope.json"
STATES = {
    "intake",
    "planned",
    "authorized",
    "executing",
    "verifying",
    "completed",
    "blocked",
}


@dataclass(frozen=True)
class ContractStatus:
    root: Path
    contract: Optional[Dict[str, Any]]
    errors: Tuple[str, ...]


def _cwd(payload: Dict[str, Any]) -> Path:
    value = payload.get("cwd")
    return Path(value).resolve() if isinstance(value, str) and value.strip() else Path.cwd().resolve()


def _repo_root(cwd: Path) -> Path:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return cwd
    if completed.returncode == 0 and completed.stdout.strip():
        return Path(completed.stdout.strip()).resolve()
    return cwd


def _read_json_regular(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not path.exists():
        return None, None
    descriptor: Optional[int] = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return None, f"{path} is not a regular file"
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = None
            value = json.load(handle)
        if not isinstance(value, dict):
            return None, f"{path} must contain a JSON object"
        return value, None
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"cannot read {path}: {exc}"
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty_string(item) for item in value)


def _validate_contract(contract: Dict[str, Any]) -> Tuple[str, ...]:
    errors = []
    if contract.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for key in ("run_id", "objective"):
        if not _nonempty_string(contract.get(key)):
            errors.append(f"{key} must be a non-empty string")
    if contract.get("state") not in STATES:
        errors.append(f"state must be one of {sorted(STATES)}")

    scope = contract.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
    else:
        if not _string_list(scope.get("allowed_paths")):
            errors.append("scope.allowed_paths must be a non-empty string list")
        if not _string_list(scope.get("forbidden_targets", [])):
            errors.append("scope.forbidden_targets must be a string list")

    done = contract.get("done_criteria")
    if not _string_list(done):
        errors.append("done_criteria must be a non-empty string list")

    enforcement = contract.get("enforcement")
    if not isinstance(enforcement, dict):
        errors.append("enforcement must be an object")
    else:
        for key in ("checkpoint_before_compact", "completion_gate", "action_envelope_required"):
            if not isinstance(enforcement.get(key), bool):
                errors.append(f"enforcement.{key} must be boolean")
        required = enforcement.get("required_evidence_classes", [])
        if not _string_list(required):
            errors.append("enforcement.required_evidence_classes must be a string list")
    return tuple(errors)


def load_status(payload: Dict[str, Any]) -> ContractStatus:
    root = _repo_root(_cwd(payload))
    path = root / STATE_DIRECTORY / CONTRACT_NAME
    contract, error = _read_json_regular(path)
    if error:
        return ContractStatus(root, None, (error,))
    if contract is None:
        return ContractStatus(root, None, ())
    return ContractStatus(root, contract, _validate_contract(contract))


def _context(event: str, message: str) -> Dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": message,
        }
    }


def _anchor(contract: Dict[str, Any]) -> str:
    scope = contract["scope"]["allowed_paths"]
    return (
        "RUN_GUARD: opt-in run contract active. "
        f"run_id={contract['run_id']}; state={contract['state']}; "
        f"objective={contract['objective']}; allowed_paths={scope}. "
        "Re-read docs/TASK_LOG.md and .agent-state/checkpoint.json before continuing. "
        "The contract and action envelope document scope but never create human approval."
    )


def _validate_checkpoint(root: Path, contract: Dict[str, Any]) -> Tuple[str, ...]:
    checkpoint, error = _read_json_regular(root / STATE_DIRECTORY / CHECKPOINT_NAME)
    if error:
        return (error,)
    if checkpoint is None:
        return (f"missing {STATE_DIRECTORY}/{CHECKPOINT_NAME}",)
    errors = []
    if checkpoint.get("schema_version") != 1:
        errors.append("checkpoint.schema_version must be 1")
    if checkpoint.get("run_id") != contract.get("run_id"):
        errors.append("checkpoint.run_id does not match run contract")
    if checkpoint.get("state") not in STATES:
        errors.append("checkpoint.state is invalid")
    for key in ("objective", "last_verified_result", "next_safe_step", "updated_at"):
        if not _nonempty_string(checkpoint.get(key)):
            errors.append(f"checkpoint.{key} must be a non-empty string")
    return tuple(errors)


def _validate_action_envelope(root: Path, contract: Dict[str, Any]) -> Tuple[str, ...]:
    envelope, error = _read_json_regular(root / STATE_DIRECTORY / ENVELOPE_NAME)
    if error:
        return (error,)
    if envelope is None:
        return (f"missing {STATE_DIRECTORY}/{ENVELOPE_NAME}",)
    errors = []
    if envelope.get("schema_version") != 1:
        errors.append("action envelope schema_version must be 1")
    if envelope.get("run_id") != contract.get("run_id"):
        errors.append("action envelope run_id does not match run contract")
    approval = envelope.get("human_approval")
    if not isinstance(approval, dict):
        errors.append("action envelope human_approval must be an object")
    else:
        if not _nonempty_string(approval.get("conversation_reference")):
            errors.append("action envelope needs human_approval.conversation_reference")
        if not _nonempty_string(approval.get("approved_at")):
            errors.append("action envelope needs human_approval.approved_at")
        expires_at = approval.get("expires_at")
        if expires_at is not None:
            try:
                parsed = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError("timezone required")
                if parsed <= datetime.now(timezone.utc):
                    errors.append("action envelope has expired")
            except ValueError:
                errors.append("action envelope expires_at must be null or an ISO-8601 timestamp")
    for key in ("allowed_actions", "targets", "abort_conditions", "validation_steps"):
        if not _string_list(envelope.get(key)):
            errors.append(f"action envelope {key} must be a non-empty string list")
    if not _string_list(envelope.get("constraints")):
        errors.append("action envelope constraints must be a non-empty string list")
    if not _nonempty_string(envelope.get("rollback_reference")):
        errors.append("action envelope rollback_reference must be a non-empty string")
    return tuple(errors)


def _paths_stay_inside(root: Path, values: Iterable[Any]) -> bool:
    for value in values:
        if not _nonempty_string(value):
            return False
        candidate = Path(value)
        if candidate.is_absolute():
            return False
        try:
            (root / candidate).resolve().relative_to(root)
        except ValueError:
            return False
    return True


def _validate_evidence(root: Path, contract: Dict[str, Any]) -> Tuple[str, ...]:
    evidence, error = _read_json_regular(root / STATE_DIRECTORY / EVIDENCE_NAME)
    if error:
        return (error,)
    if evidence is None:
        return (f"missing {STATE_DIRECTORY}/{EVIDENCE_NAME}",)
    errors = []
    if evidence.get("schema_version") != 1:
        errors.append("evidence.schema_version must be 1")
    if evidence.get("run_id") != contract.get("run_id"):
        errors.append("evidence.run_id does not match run contract")
    records = evidence.get("records")
    if not isinstance(records, list):
        return tuple(errors + ["evidence.records must be a list"])
    valid_classes = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"evidence.records[{index}] must be an object")
            continue
        evidence_class = record.get("class")
        paths = record.get("artifacts", [])
        if not _nonempty_string(evidence_class):
            errors.append(f"evidence.records[{index}].class is required")
        elif record.get("result") == "pass" and _nonempty_string(record.get("observed_at")):
            valid_classes.add(evidence_class)
        if not isinstance(paths, list) or not _paths_stay_inside(root, paths):
            errors.append(f"evidence.records[{index}].artifacts must be repo-relative paths")
        else:
            for relative in paths:
                if not (root / relative).is_file():
                    errors.append(f"evidence artifact does not exist: {relative}")
        if not _nonempty_string(record.get("summary")):
            errors.append(f"evidence.records[{index}].summary must be a non-empty string")
    required = set(contract["enforcement"].get("required_evidence_classes", []))
    missing = sorted(required - valid_classes)
    if missing:
        errors.append(f"missing passing evidence classes: {missing}")
    return tuple(errors)


def handle_context_event(event: str, status: ContractStatus) -> Optional[Dict[str, Any]]:
    if status.errors:
        return _context(event, "RUN_GUARD: invalid opt-in state: " + "; ".join(status.errors))
    if status.contract is None:
        return None
    message = _anchor(status.contract)
    enforcement = status.contract["enforcement"]
    if enforcement.get("action_envelope_required") and status.contract["state"] in {
        "authorized",
        "executing",
        "verifying",
        "completed",
    }:
        envelope_errors = _validate_action_envelope(status.root, status.contract)
        if envelope_errors:
            message += " ACTION ENVELOPE INVALID: " + "; ".join(envelope_errors)
        else:
            message += " Action envelope is structurally valid; independently confirm its approval reference."
    return _context(event, message)


def handle_pre_compact(status: ContractStatus) -> Optional[Dict[str, Any]]:
    if status.contract is None and not status.errors:
        return None
    if status.errors:
        return {"continue": False, "stopReason": "Invalid opt-in run contract: " + "; ".join(status.errors)}
    if not status.contract["enforcement"].get("checkpoint_before_compact"):
        return None
    errors = _validate_checkpoint(status.root, status.contract)
    if errors:
        return {
            "continue": False,
            "stopReason": "Write a valid durable checkpoint before compaction: " + "; ".join(errors),
        }
    return None


def handle_stop(payload: Dict[str, Any], status: ContractStatus) -> Dict[str, Any]:
    if payload.get("stop_hook_active") is True:
        return {}
    if status.contract is None:
        if status.errors:
            return {"systemMessage": "RUN_GUARD invalid: " + "; ".join(status.errors)}
        return {}
    contract = status.contract
    if status.errors:
        return {"decision": "block", "reason": "Repair the opt-in run contract: " + "; ".join(status.errors)}
    enforcement = contract["enforcement"]
    if not enforcement.get("completion_gate"):
        return {}
    if contract["state"] in {"executing", "verifying"}:
        return {
            "decision": "block",
            "reason": (
                "The contracted run is still active. Continue toward verification, or record a factual "
                "checkpoint and change the state to blocked before ending."
            ),
        }
    if contract["state"] == "completed":
        errors = _validate_evidence(status.root, contract)
        if errors:
            return {
                "decision": "block",
                "reason": "Completion evidence is structurally incomplete: " + "; ".join(errors),
            }
    return {}


def dispatch(payload: Dict[str, Any], argv_event: Optional[str] = None) -> Optional[Dict[str, Any]]:
    event = payload.get("hook_event_name")
    if not _nonempty_string(event):
        event = argv_event or ""
    status = load_status(payload)
    if event in {"SessionStart", "PostCompact"}:
        return handle_context_event(event, status)
    if event == "PreCompact":
        return handle_pre_compact(status)
    if event == "Stop":
        return handle_stop(payload, status)
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
        if event == "Stop":
            result = {"decision": "block", "reason": f"run guard failed closed: {exc}"}
        elif event == "PreCompact":
            result = {"continue": False, "stopReason": f"run guard failed closed: {exc}"}
        else:
            result = {"systemMessage": f"RUN_GUARD check failed: {exc}"}
    if result is not None:
        sys.stdout.write(json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
