#!/usr/bin/env python3
"""Conservative Git task-branch guard and lifecycle status reporter.

The hook blocks recognized local mutations on the default branch, fallback
protected branches, and detached HEAD. It intentionally does not claim to
cover hosted or unknown tool paths; AGENTS.md and remote rulesets remain the
authoritative fallback and enforcement boundary.
"""

from __future__ import annotations

import json
import re
import shlex
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


POLICY_PATH = Path(".codex/policies/git_lifecycle.json")
DEFAULT_PREFIX = "codex/"
DEFAULT_PROTECTED = ("main", "master", "trunk")
DIRECT_WRITE_TOOLS = {
    "Edit",
    "Write",
    "apply_patch",
    "write_file",
    "write_stdin",
}
SHELL_TOOLS = {"Bash", "exec_command", "functions.exec_command", "shell"}
SHELL_CONTROL = re.compile(r"[;&|<>`$\n\r]")
LIFECYCLE_INVALIDATIONS = {
    "expiry",
    "repository_or_branch_mismatch",
    "base_sha_drift",
    "unexpected_head_commit",
    "out_of_scope_diff",
    "required_check_failure",
    "changes_requested_review",
    "unresolved_review_thread",
    "mergeability_failure",
    "ambiguous_readback",
}
LIFECYCLE_EXCLUSIONS = {
    "secret_or_credential_change",
    "permission_or_repository_setting_change",
    "release_tag_or_workflow_dispatch",
    "destructive_data_change",
    "live_or_production_change",
    "homelab_infrastructure_change",
    "scope_or_target_expansion",
    "force_push_or_direct_default_branch_push",
}


@dataclass(frozen=True)
class GitPolicy:
    task_branch_prefix: str = DEFAULT_PREFIX
    protected_branch_names: Tuple[str, ...] = DEFAULT_PROTECTED
    force_push: bool = False
    direct_default_branch_push: bool = False


@dataclass(frozen=True)
class GitStatus:
    kind: str  # git, non_git, unknown
    root: Path
    branch: Optional[str] = None
    default_branch: Optional[str] = None
    detached: bool = False
    protected: bool = False
    dirty_count: Optional[int] = None
    upstream: Optional[str] = None
    ahead: Optional[int] = None
    behind: Optional[int] = None
    policy: GitPolicy = GitPolicy()
    errors: Tuple[str, ...] = ()


def _run_git(arguments: list[str], cwd: Path) -> Tuple[int, str, str]:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=str(cwd),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _validate_policy(payload: Any) -> GitPolicy:
    if not isinstance(payload, dict):
        raise ValueError("policy must be a JSON object")
    required = {
        "schema_version",
        "task_branch_prefix",
        "protected_branch_names",
        "local_write_authorization",
        "milestone_commit",
        "remote_gates",
        "lifecycle_approval_envelope",
        "force_push",
        "direct_default_branch_push",
    }
    if set(payload) != required:
        raise ValueError("policy contains unknown or missing top-level fields")
    if payload.get("schema_version") != 2:
        raise ValueError("schema_version must be 2")

    prefix = payload.get("task_branch_prefix")
    if not isinstance(prefix, str) or not prefix or not prefix.endswith("/"):
        raise ValueError("task_branch_prefix must be a non-empty slash-terminated string")
    protected = payload.get("protected_branch_names")
    if (
        not isinstance(protected, list)
        or not protected
        or not all(isinstance(item, str) and item for item in protected)
        or len(set(protected)) != len(protected)
    ):
        raise ValueError("protected_branch_names must contain unique non-empty strings")

    local = payload.get("local_write_authorization")
    if not isinstance(local, dict) or set(local) != {
        "includes_task_branch_creation",
        "includes_milestone_commits",
    } or not all(isinstance(value, bool) for value in local.values()):
        raise ValueError("local_write_authorization is invalid")

    milestone = payload.get("milestone_commit")
    if not isinstance(milestone, dict) or set(milestone) != {
        "required_before",
        "forbid_empty",
        "forbid_known_broken",
        "forbid_unrelated_changes",
    }:
        raise ValueError("milestone_commit is invalid")
    required_before = milestone.get("required_before")
    if (
        not isinstance(required_before, list)
        or not required_before
        or not all(isinstance(item, str) and item for item in required_before)
    ):
        raise ValueError("milestone_commit.required_before is invalid")
    for field in ("forbid_empty", "forbid_known_broken", "forbid_unrelated_changes"):
        if not isinstance(milestone.get(field), bool):
            raise ValueError(f"milestone_commit.{field} must be boolean")

    remote = payload.get("remote_gates")
    expected_remote = {
        "push",
        "pull_request",
        "ready_for_review",
        "merge",
        "branch_cleanup",
    }
    if (
        not isinstance(remote, dict)
        or set(remote) != expected_remote
        or not all(isinstance(value, str) and value for value in remote.values())
    ):
        raise ValueError("remote_gates is invalid")
    expected_remote_values = {
        "push": "explicit-current-or-valid-lifecycle-envelope",
        "pull_request": "explicit-current-or-valid-lifecycle-envelope",
        "ready_for_review": "explicit-current-or-valid-lifecycle-envelope",
        "merge": "separate-stage-explicit-current-or-valid-lifecycle-envelope",
        "branch_cleanup": "separate-stage-explicit-current-or-valid-lifecycle-envelope",
    }
    if remote != expected_remote_values:
        raise ValueError("remote_gates weakens or changes the central lifecycle contract")

    envelope = payload.get("lifecycle_approval_envelope")
    expected_envelope = {
        "active_state_path",
        "schema_version",
        "maximum_validity_hours",
        "requires_finite_expiry",
        "requires_exact_repository",
        "requires_exact_base_sha",
        "requires_exact_topic_branch",
        "head_binding",
        "requires_path_allowlist",
        "requires_stage_allowlist",
        "fresh_readback_before",
        "invalidate_on",
        "excluded_actions",
    }
    if not isinstance(envelope, dict) or set(envelope) != expected_envelope:
        raise ValueError("lifecycle_approval_envelope is invalid")
    if envelope.get("active_state_path") != ".agent-state/action-envelope.json":
        raise ValueError("lifecycle envelope active_state_path is invalid")
    if envelope.get("schema_version") != 2:
        raise ValueError("lifecycle envelope schema_version must be 2")
    maximum_hours = envelope.get("maximum_validity_hours")
    if maximum_hours != 168:
        raise ValueError("lifecycle envelope maximum_validity_hours must be 168")
    for field in (
        "requires_finite_expiry",
        "requires_exact_repository",
        "requires_exact_base_sha",
        "requires_exact_topic_branch",
        "requires_path_allowlist",
        "requires_stage_allowlist",
    ):
        if envelope.get(field) is not True:
            raise ValueError(f"lifecycle envelope {field} must be true")
    if envelope.get("head_binding") != "run-produced-tip":
        raise ValueError("lifecycle envelope head_binding is invalid")
    readbacks = envelope.get("fresh_readback_before")
    required_readbacks = {
        "mark_ready_for_review",
        "merge_pr",
        "delete_remote_branch",
        "remove_linked_worktree",
        "delete_local_branch",
    }
    if (
        not isinstance(readbacks, list)
        or len(readbacks) != len(set(readbacks))
        or set(readbacks) != required_readbacks
    ):
        raise ValueError("lifecycle envelope fresh_readback_before is invalid")
    invalidations = envelope.get("invalidate_on")
    if (
        not isinstance(invalidations, list)
        or len(invalidations) != len(set(invalidations))
        or set(invalidations) != LIFECYCLE_INVALIDATIONS
    ):
        raise ValueError("lifecycle envelope invalidate_on is invalid")
    exclusions = envelope.get("excluded_actions")
    if (
        not isinstance(exclusions, list)
        or len(exclusions) != len(set(exclusions))
        or set(exclusions) != LIFECYCLE_EXCLUSIONS
    ):
        raise ValueError("lifecycle envelope excluded_actions is invalid")
    for field in ("force_push", "direct_default_branch_push"):
        if not isinstance(payload.get(field), bool):
            raise ValueError(f"{field} must be boolean")
    return GitPolicy(
        prefix,
        tuple(protected),
        payload["force_push"],
        payload["direct_default_branch_push"],
    )


def load_policy(root: Path) -> Tuple[GitPolicy, Optional[str]]:
    path = root / POLICY_PATH
    if not path.exists():
        return GitPolicy(), None
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
            raise ValueError("policy path must be a physical regular file")
        def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON key {key!r}")
                result[key] = value
            return result

        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
        return _validate_policy(payload), None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return GitPolicy(), f"{POLICY_PATH}: {exc}"


def _default_branch(root: Path, policy: GitPolicy) -> str:
    rc, value, _ = _run_git(
        ["symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"], root
    )
    if rc == 0 and value:
        return value.removeprefix("origin/")
    rc, value, _ = _run_git(["config", "--get", "init.defaultBranch"], root)
    if rc == 0 and value:
        return value
    for candidate in policy.protected_branch_names:
        rc, _, _ = _run_git(["show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"], root)
        if rc == 0:
            return candidate
    return policy.protected_branch_names[0]


def detect_git_status(cwd: Path) -> GitStatus:
    cwd = cwd.expanduser().resolve()
    rc, inside, error = _run_git(["rev-parse", "--is-inside-work-tree"], cwd)
    if rc != 0:
        lowered = error.lower()
        if "not a git repository" in lowered or "outside repository" in lowered:
            return GitStatus("non_git", cwd)
        return GitStatus("unknown", cwd, errors=(error or "git detection failed",))
    if inside != "true":
        return GitStatus("non_git", cwd)

    rc, root_raw, error = _run_git(["rev-parse", "--show-toplevel"], cwd)
    if rc != 0 or not root_raw:
        return GitStatus("unknown", cwd, errors=(error or "missing worktree root",))
    root = Path(root_raw).resolve()
    policy, policy_error = load_policy(root)
    errors = [policy_error] if policy_error else []

    rc, branch_raw, _ = _run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], root)
    detached = rc != 0 or not branch_raw
    branch = None if detached else branch_raw
    default = _default_branch(root, policy)

    rc, dirty_raw, error = _run_git(
        ["status", "--porcelain=v1", "--untracked-files=all"], root
    )
    if rc == 0:
        dirty_count = len(dirty_raw.splitlines()) if dirty_raw else 0
    else:
        dirty_count = None
        errors.append(error or "git status failed")

    rc, upstream_raw, _ = _run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"], root
    )
    upstream = upstream_raw if rc == 0 and upstream_raw else None
    ahead = behind = None
    if upstream:
        rc, counts, error = _run_git(
            ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"], root
        )
        if rc == 0:
            try:
                ahead, behind = (int(item) for item in counts.split())
            except (TypeError, ValueError):
                errors.append("invalid ahead/behind count")
        else:
            errors.append(error or "ahead/behind detection failed")

    protected = detached or branch == default or branch in policy.protected_branch_names
    return GitStatus(
        "git",
        root,
        branch,
        default,
        detached,
        protected,
        dirty_count,
        upstream,
        ahead,
        behind,
        policy,
        tuple(errors),
    )


def _cwd(payload: Dict[str, Any]) -> Path:
    value = payload.get("cwd")
    return Path(value) if isinstance(value, str) and value.strip() else Path.cwd()


def _tool_name(payload: Dict[str, Any]) -> str:
    value = payload.get("tool_name")
    return value if isinstance(value, str) else ""


def _command(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    for field in ("command", "cmd"):
        value = tool_input.get(field)
        if isinstance(value, str):
            return value
    return ""


def _tokens(command: str) -> Optional[list[str]]:
    if not command.strip() or SHELL_CONTROL.search(command):
        return None
    try:
        return shlex.split(command)
    except ValueError:
        return None


def _safe_git_read(tokens: list[str]) -> bool:
    if len(tokens) < 2 or tokens[0] != "git":
        return False
    subcommand = tokens[1]
    if subcommand in {
        "describe",
        "diff",
        "for-each-ref",
        "log",
        "ls-files",
        "ls-tree",
        "merge-base",
        "name-rev",
        "rev-list",
        "rev-parse",
        "show",
        "show-ref",
        "status",
        "symbolic-ref",
    }:
        return not any(item == "--output" or item.startswith("--output=") for item in tokens[2:])
    if subcommand == "branch":
        return len(tokens) >= 3 and tokens[2] in {"--contains", "--list", "--show-current", "-l"}
    if subcommand == "worktree":
        return len(tokens) >= 3 and tokens[2] == "list"
    if subcommand == "remote":
        return len(tokens) >= 3 and tokens[2] in {"-v", "get-url", "show"}
    if subcommand == "config":
        return len(tokens) >= 3 and tokens[2] in {"--get", "--get-all", "--list", "-l"}
    if subcommand == "tag":
        return len(tokens) >= 3 and tokens[2] in {"--list", "-l"}
    return False


def _safe_read_command(command: str) -> bool:
    tokens = _tokens(command)
    if not tokens:
        return False
    if tokens[0] == "git":
        return _safe_git_read(tokens)
    if tokens[0] in {"cat", "file", "grep", "head", "ls", "pwd", "rg", "stat", "tail", "test", "wc", "which"}:
        return True
    if tokens[0] == "sed":
        return "-n" in tokens and not any(item == "-i" or item.startswith("-i") for item in tokens[1:])
    if tokens[0] == "find":
        dangerous = {"-delete", "-exec", "-execdir", "-fprint", "-fprint0", "-ok", "-okdir"}
        return not any(item in dangerous for item in tokens[1:])
    return False


def _safe_branch_escape(command: str, status: GitStatus) -> bool:
    tokens = _tokens(command)
    if not tokens or tokens[0] != "git":
        return False
    prefix = status.policy.task_branch_prefix
    if len(tokens) == 4 and tokens[1:3] in (["switch", "-c"], ["switch", "--create"]):
        return tokens[3].startswith(prefix) and len(tokens[3]) > len(prefix)
    if len(tokens) == 3 and tokens[1] == "switch":
        target = tokens[2]
        return (
            status.dirty_count == 0
            and target not in {"-", "--detach"}
            and target not in status.policy.protected_branch_names
            and target != status.default_branch
        )
    return False


def _forbidden_remote_git_action(command: str, status: GitStatus) -> Optional[str]:
    tokens = _tokens(command)
    if not tokens or len(tokens) < 2 or tokens[:2] != ["git", "push"]:
        return None
    arguments = tokens[2:]
    if not status.policy.force_push and any(
        item.startswith("--force")
        or item.startswith("+")
        or (item.startswith("-") and not item.startswith("--") and "f" in item)
        for item in arguments
    ):
        return "Git guard denied force-push; the repository policy forbids it."
    default = status.default_branch
    if not status.policy.direct_default_branch_push and default:
        if any(
            item in {default, f"refs/heads/{default}"}
            or item.endswith(f":{default}")
            or item.endswith(f":refs/heads/{default}")
            for item in arguments
        ):
            return "Git guard denied a direct push to the default branch."
    return None


def _deny(reason: str) -> Dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _is_recognized_mutation(payload: Dict[str, Any]) -> bool:
    name = _tool_name(payload)
    if name in DIRECT_WRITE_TOOLS:
        return True
    return name in SHELL_TOOLS and not _safe_read_command(_command(payload))


def handle_pre_tool_use(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    status = detect_git_status(_cwd(payload))
    if status.kind == "non_git":
        return None
    if status.kind == "unknown":
        return _deny("Git guard denied a recognized local mutation because Git state is unknown.") if _is_recognized_mutation(payload) else None
    if not _is_recognized_mutation(payload):
        return None
    if status.errors:
        return _deny("Git guard denied a recognized local mutation: " + "; ".join(status.errors))
    command = _command(payload)
    if _tool_name(payload) in SHELL_TOOLS:
        forbidden = _forbidden_remote_git_action(command, status)
        if forbidden:
            return _deny(forbidden)
    if _tool_name(payload) in SHELL_TOOLS and _safe_branch_escape(command, status):
        return None
    if not status.protected:
        return None
    location = "detached HEAD" if status.detached else f"protected branch {status.branch}"
    return _deny(
        f"Git guard denied this local mutation on {location}. Create or switch to the task "
        f"branch {status.policy.task_branch_prefix}<short-purpose> first. MAIN_WORKTREE_OK does "
        "not waive the branch boundary."
    )


def _value(value: Optional[object]) -> str:
    return "unknown" if value is None else str(value)


def _status_line(status: GitStatus) -> str:
    branch = "DETACHED" if status.detached else _value(status.branch)
    return (
        f"branch={branch}; default={_value(status.default_branch)}; "
        f"protected={'yes' if status.protected else 'no'}; dirty={_value(status.dirty_count)}; "
        f"upstream={_value(status.upstream)}; ahead={_value(status.ahead)}; "
        f"behind={_value(status.behind)}"
    )


def handle_session_start(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = detect_git_status(_cwd(payload))
    if status.kind == "non_git":
        message = "GIT_GUARD: not a Git repository; no branch gate applies."
    elif status.kind == "unknown":
        message = "GIT_GUARD: Git state is unknown; allow read-only inspection only."
    else:
        message = "GIT_GUARD: " + _status_line(status) + ". "
        if status.protected:
            message += (
                f"Read-only work only until {status.policy.task_branch_prefix}<short-purpose> "
                "or an existing non-protected task branch is active."
            )
        else:
            message += "Task-branch writes may proceed within the separately authorized scope."
        if status.errors:
            message += " Guard errors: " + "; ".join(status.errors)
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": message,
        }
    }


def handle_stop(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("stop_hook_active") is True:
        return {}
    status = detect_git_status(_cwd(payload))
    if status.kind != "git":
        return {"systemMessage": "GIT_GUARD: report that no Git lifecycle applies."}
    message = "GIT_GUARD handoff required: " + _status_line(status) + ". "
    if status.dirty_count:
        message += (
            "Do not claim a clean completion: commit the coherent validated scope before handoff "
            "or explain why a commit is inapplicable. "
        )
    elif status.ahead:
        message += "Local commits are unpushed; recommend push only when remotely authorized. "
    else:
        message += "Working tree has no uncommitted Git diff. "
    message += (
        "State the last local commit, remote/PR/CI state, merge readiness, recommended next Git "
        "action, and the authorization it requires."
    )
    return {"systemMessage": message}


def dispatch(payload: Dict[str, Any], argv_event: Optional[str] = None) -> Optional[Dict[str, Any]]:
    event = payload.get("hook_event_name")
    if not isinstance(event, str) or not event:
        event = argv_event or ""
    if event == "SessionStart":
        return handle_session_start(payload)
    if event == "PreToolUse":
        return handle_pre_tool_use(payload)
    if event == "Stop":
        return handle_stop(payload)
    return None


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else "PreToolUse"
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            raise ValueError("hook input must be a JSON object")
        result = dispatch(payload, event)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        if event == "PreToolUse":
            result = _deny(f"Git guard failed closed: {exc}")
        else:
            result = {"systemMessage": f"GIT_GUARD check failed: {exc}"}
    if result is not None:
        sys.stdout.write(json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
