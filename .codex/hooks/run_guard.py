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
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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
LIFECYCLE_ENVELOPE_TYPE = "git-lifecycle"
LIFECYCLE_HEAD_BINDING = "run-produced-tip"
LIFECYCLE_PR_BINDING = "created-from-topic-branch"
MAX_LIFECYCLE_ENVELOPE_HOURS = 168
LIFECYCLE_STAGES = frozenset(
    {
        "create_task_branch",
        "modify_allowed_paths",
        "validate",
        "milestone_commit",
        "push_topic_branch",
        "create_draft_pr",
        "update_pr_metadata",
        "apply_review_fixes",
        "mark_ready_for_review",
        "merge_pr",
        "delete_remote_branch",
        "remove_linked_worktree",
        "delete_local_branch",
    }
)
MERGE_METHODS = frozenset({"merge", "squash", "rebase", "queue"})
CLEANUP_MODES = frozenset({"keep", "delete-remote-branch", "delete-remote-and-local"})
REPOSITORY_SLUG = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REMOTE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


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
        def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON key {key!r}")
                result[key] = value
            return result

        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = None
            value = json.load(handle, object_pairs_hook=reject_duplicate_keys)
        if not isinstance(value, dict):
            return None, f"{path} must contain a JSON object"
        return value, None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, f"cannot read {path}: {exc}"
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty_string(item) for item in value)


def _unique_string_list(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (bool(value) or not nonempty)
        and all(_nonempty_string(item) for item in value)
        and len(value) == len(set(value))
    )


def _timestamp(
    value: Any,
    label: str,
    errors: list[str],
    *,
    nullable: bool,
) -> Optional[datetime]:
    if value is None and nullable:
        return None
    if not _nonempty_string(value):
        errors.append(f"{label} must be an ISO-8601 timestamp")
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
        return parsed.astimezone(timezone.utc)
    except ValueError:
        errors.append(f"{label} must be an ISO-8601 timestamp with timezone")
        return None


def _repo_relative_patterns(value: Any, *, nonempty: bool) -> bool:
    if not _unique_string_list(value, nonempty=nonempty):
        return False
    for item in value:
        path = Path(item)
        if path.is_absolute() or ".." in path.parts or "\x00" in item:
            return False
    return True


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


def _validate_human_approval(
    approval: Any,
    *,
    lifecycle: bool,
) -> Tuple[Optional[datetime], Optional[datetime], list[str]]:
    errors = []
    if not isinstance(approval, dict):
        errors.append("action envelope human_approval must be an object")
        return None, None, errors
    if lifecycle and set(approval) != {"conversation_reference", "approved_at", "expires_at"}:
        errors.append("lifecycle envelope human_approval contains unknown or missing fields")
    if not _nonempty_string(approval.get("conversation_reference")):
        errors.append("action envelope needs human_approval.conversation_reference")
    approved_at = _timestamp(
        approval.get("approved_at"),
        "action envelope human_approval.approved_at",
        errors,
        nullable=False,
    )
    expires_at = _timestamp(
        approval.get("expires_at"),
        "action envelope human_approval.expires_at",
        errors,
        nullable=not lifecycle,
    )
    now = datetime.now(timezone.utc)
    if approved_at and approved_at > now + timedelta(minutes=5):
        errors.append("action envelope approved_at is in the future")
    if expires_at and expires_at <= now:
        errors.append("action envelope has expired")
    if approved_at and expires_at:
        duration = expires_at - approved_at
        if duration <= timedelta(0):
            errors.append("action envelope expires_at must be later than approved_at")
        if lifecycle and duration > timedelta(hours=MAX_LIFECYCLE_ENVELOPE_HOURS):
            errors.append(
                "lifecycle envelope validity exceeds "
                f"{MAX_LIFECYCLE_ENVELOPE_HOURS} hours"
            )
    return approved_at, expires_at, errors


def _validate_action_envelope_v1(
    envelope: Dict[str, Any], contract: Dict[str, Any]
) -> Tuple[str, ...]:
    errors: list[str] = []
    if envelope.get("run_id") != contract.get("run_id"):
        errors.append("action envelope run_id does not match run contract")
    _, _, approval_errors = _validate_human_approval(
        envelope.get("human_approval"), lifecycle=False
    )
    errors.extend(approval_errors)
    for key in ("allowed_actions", "targets", "abort_conditions", "validation_steps"):
        if not _string_list(envelope.get(key)):
            errors.append(f"action envelope {key} must be a non-empty string list")
    if not _string_list(envelope.get("constraints")):
        errors.append("action envelope constraints must be a non-empty string list")
    if not _nonempty_string(envelope.get("rollback_reference")):
        errors.append("action envelope rollback_reference must be a non-empty string")
    return tuple(errors)


def _validate_action_envelope_v2(
    root: Path, envelope: Dict[str, Any], contract: Dict[str, Any]
) -> Tuple[str, ...]:
    errors: list[str] = []
    expected_top = {
        "schema_version",
        "envelope_type",
        "run_id",
        "human_approval",
        "repository",
        "scope",
        "pull_request",
        "constraints",
        "abort_conditions",
        "validation_steps",
        "rollback_reference",
    }
    if set(envelope) != expected_top:
        errors.append("lifecycle envelope contains unknown or missing top-level fields")
    if envelope.get("envelope_type") != LIFECYCLE_ENVELOPE_TYPE:
        errors.append(f"lifecycle envelope envelope_type must be {LIFECYCLE_ENVELOPE_TYPE!r}")
    if envelope.get("run_id") != contract.get("run_id"):
        errors.append("action envelope run_id does not match run contract")
    _, _, approval_errors = _validate_human_approval(
        envelope.get("human_approval"), lifecycle=True
    )
    errors.extend(approval_errors)

    repository = envelope.get("repository")
    if not isinstance(repository, dict):
        errors.append("lifecycle envelope repository must be an object")
    else:
        expected_repository = {
            "slug",
            "worktree_root",
            "remote",
            "base_branch",
            "base_sha",
            "topic_branch",
            "head_binding",
        }
        if set(repository) != expected_repository:
            errors.append("lifecycle envelope repository contains unknown or missing fields")
        if not _nonempty_string(repository.get("slug")) or not REPOSITORY_SLUG.fullmatch(
            repository.get("slug", "")
        ):
            errors.append("lifecycle envelope repository.slug must be owner/repository")
        worktree_root = repository.get("worktree_root")
        if not _nonempty_string(worktree_root) or not Path(worktree_root).is_absolute():
            errors.append("lifecycle envelope repository.worktree_root must be absolute")
        elif Path(worktree_root).resolve() != root.resolve():
            errors.append("lifecycle envelope repository.worktree_root does not match this worktree")
        if not _nonempty_string(repository.get("remote")) or not REMOTE_NAME.fullmatch(
            repository.get("remote", "")
        ):
            errors.append("lifecycle envelope repository.remote must be an exact Git remote name")
        base_branch = repository.get("base_branch")
        topic_branch = repository.get("topic_branch")
        if not _nonempty_string(base_branch):
            errors.append("lifecycle envelope repository.base_branch must be non-empty")
        if not _nonempty_string(topic_branch):
            errors.append("lifecycle envelope repository.topic_branch must be non-empty")
        elif topic_branch == base_branch or topic_branch in {"main", "master", "trunk"}:
            errors.append("lifecycle envelope topic_branch must not be protected/base branch")
        if not _nonempty_string(repository.get("base_sha")) or not FULL_GIT_SHA.fullmatch(
            repository.get("base_sha", "")
        ):
            errors.append("lifecycle envelope repository.base_sha must be a full lowercase Git SHA")
        if repository.get("head_binding") != LIFECYCLE_HEAD_BINDING:
            errors.append(
                "lifecycle envelope repository.head_binding must be "
                f"{LIFECYCLE_HEAD_BINDING!r}"
            )

    stages: set[str] = set()
    scope = envelope.get("scope")
    if not isinstance(scope, dict):
        errors.append("lifecycle envelope scope must be an object")
    else:
        if set(scope) != {"allowed_paths", "forbidden_paths", "allowed_stages"}:
            errors.append("lifecycle envelope scope contains unknown or missing fields")
        if not _repo_relative_patterns(scope.get("allowed_paths"), nonempty=True):
            errors.append("lifecycle envelope scope.allowed_paths must be unique repo-relative paths")
        forbidden_paths = scope.get("forbidden_paths")
        if not _repo_relative_patterns(forbidden_paths, nonempty=True):
            errors.append("lifecycle envelope scope.forbidden_paths must be unique repo-relative paths")
        elif not {".git", ".agent-state"}.issubset(set(forbidden_paths)):
            errors.append("lifecycle envelope forbidden_paths must include .git and .agent-state")
        allowed_stages = scope.get("allowed_stages")
        if not _unique_string_list(allowed_stages, nonempty=True):
            errors.append("lifecycle envelope scope.allowed_stages must be a unique non-empty list")
        else:
            stages = set(allowed_stages)
            unknown = sorted(stages - LIFECYCLE_STAGES)
            if unknown:
                errors.append(f"lifecycle envelope has unknown stages: {unknown}")

    pull_request = envelope.get("pull_request")
    cleanup = None
    if not isinstance(pull_request, dict):
        errors.append("lifecycle envelope pull_request must be an object")
    else:
        expected_pr = {
            "identity_binding",
            "draft_first",
            "metadata",
            "required_check_policy",
            "required_approvals",
            "require_no_unresolved_threads",
            "merge_method",
            "cleanup",
        }
        if set(pull_request) != expected_pr:
            errors.append("lifecycle envelope pull_request contains unknown or missing fields")
        if pull_request.get("identity_binding") != LIFECYCLE_PR_BINDING:
            errors.append(
                "lifecycle envelope pull_request.identity_binding must be "
                f"{LIFECYCLE_PR_BINDING!r}"
            )
        if pull_request.get("draft_first") is not True:
            errors.append("lifecycle envelope pull_request.draft_first must be true")
        metadata = pull_request.get("metadata")
        if not isinstance(metadata, dict):
            errors.append("lifecycle envelope pull_request.metadata must be an object")
        else:
            expected_metadata = {"title", "body_policy", "labels", "milestone", "reviewers"}
            if set(metadata) != expected_metadata:
                errors.append("lifecycle envelope PR metadata contains unknown or missing fields")
            if not _nonempty_string(metadata.get("title")):
                errors.append("lifecycle envelope PR metadata.title must be non-empty")
            if metadata.get("body_policy") != "task-scope-evidence-and-risks-only":
                errors.append(
                    "lifecycle envelope PR metadata.body_policy must be "
                    "'task-scope-evidence-and-risks-only'"
                )
            for field in ("labels", "reviewers"):
                if not _unique_string_list(metadata.get(field)):
                    errors.append(f"lifecycle envelope PR metadata.{field} must be a unique list")
            milestone = metadata.get("milestone")
            if milestone is not None and not _nonempty_string(milestone):
                errors.append("lifecycle envelope PR metadata.milestone must be null or non-empty")
        if pull_request.get("required_check_policy") != "all-required-and-reported-green":
            errors.append(
                "lifecycle envelope required_check_policy must be "
                "'all-required-and-reported-green'"
            )
        approvals = pull_request.get("required_approvals")
        if isinstance(approvals, bool) or not isinstance(approvals, int) or approvals < 0:
            errors.append("lifecycle envelope required_approvals must be a non-negative integer")
        if pull_request.get("require_no_unresolved_threads") is not True:
            errors.append("lifecycle envelope require_no_unresolved_threads must be true")
        if pull_request.get("merge_method") not in MERGE_METHODS:
            errors.append(f"lifecycle envelope merge_method must be one of {sorted(MERGE_METHODS)}")
        cleanup = pull_request.get("cleanup")
        if cleanup not in CLEANUP_MODES:
            errors.append(f"lifecycle envelope cleanup must be one of {sorted(CLEANUP_MODES)}")

    dependencies = {
        "milestone_commit": {"modify_allowed_paths", "validate"},
        "push_topic_branch": {"milestone_commit"},
        "create_draft_pr": {"push_topic_branch"},
        "update_pr_metadata": {"create_draft_pr"},
        "apply_review_fixes": {
            "create_draft_pr",
            "modify_allowed_paths",
            "validate",
            "milestone_commit",
            "push_topic_branch",
        },
        "mark_ready_for_review": {"create_draft_pr", "validate"},
        "merge_pr": {"mark_ready_for_review"},
        "delete_remote_branch": {"merge_pr"},
        "remove_linked_worktree": {"merge_pr"},
        "delete_local_branch": {"merge_pr", "remove_linked_worktree"},
    }
    for stage, required in dependencies.items():
        missing = sorted(required - stages)
        if stage in stages and missing:
            errors.append(f"lifecycle stage {stage} requires stages {missing}")
    cleanup_stages = {"delete_remote_branch", "remove_linked_worktree", "delete_local_branch"}
    if cleanup == "keep" and stages & cleanup_stages:
        errors.append("lifecycle cleanup=keep conflicts with cleanup stages")
    elif cleanup == "delete-remote-branch":
        if "delete_remote_branch" not in stages or stages & {
            "remove_linked_worktree",
            "delete_local_branch",
        }:
            errors.append("lifecycle delete-remote-branch cleanup stages are inconsistent")
    elif cleanup == "delete-remote-and-local" and not cleanup_stages.issubset(stages):
        errors.append("lifecycle delete-remote-and-local requires all cleanup stages")

    for key in ("constraints", "abort_conditions", "validation_steps"):
        if not _unique_string_list(envelope.get(key), nonempty=True):
            errors.append(f"lifecycle envelope {key} must be a unique non-empty string list")
    if not _nonempty_string(envelope.get("rollback_reference")):
        errors.append("action envelope rollback_reference must be a non-empty string")
    return tuple(errors)


def _validate_action_envelope(root: Path, contract: Dict[str, Any]) -> Tuple[str, ...]:
    envelope, error = _read_json_regular(root / STATE_DIRECTORY / ENVELOPE_NAME)
    if error:
        return (error,)
    if envelope is None:
        return (f"missing {STATE_DIRECTORY}/{ENVELOPE_NAME}",)
    schema = envelope.get("schema_version")
    if schema == 1:
        return _validate_action_envelope_v1(envelope, contract)
    if schema == 2:
        return _validate_action_envelope_v2(root, envelope, contract)
    return ("action envelope schema_version must be 1 or 2",)


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
            envelope, _ = _read_json_regular(
                status.root / STATE_DIRECTORY / ENVELOPE_NAME
            )
            if envelope and envelope.get("schema_version") == 2:
                repository = envelope["repository"]
                stages = envelope["scope"]["allowed_stages"]
                message += (
                    " Git lifecycle envelope is structurally valid for "
                    f"{repository['slug']}:{repository['topic_branch']}; "
                    f"allowed_stages={stages}. Each stage still requires its fresh "
                    "preflight/readback and must stop on drift. Independently confirm the "
                    "current human approval reference."
                )
            else:
                message += (
                    " Action envelope is structurally valid; independently confirm its "
                    "approval reference."
                )
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
