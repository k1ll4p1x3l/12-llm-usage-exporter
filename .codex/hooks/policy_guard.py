#!/usr/bin/env python3
"""Conservative policy annotations for local Codex lifecycle events.

This hook never auto-approves a request.  It can deny a known mutating tool in
an opt-in contracted run when the required action envelope is structurally
invalid, and it can require an explicitly listed stage for high-confidence
Git/PR lifecycle commands. Unknown and hosted tools remain subject to Codex
and human policy; the hook is a guardrail, not a complete enforcement boundary.
"""

from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import run_guard


MUTATING_LOCAL_TOOLS = {
    "Bash",
    "exec_command",
    "functions.exec_command",
    "shell",
    "apply_patch",
    "Edit",
    "Write",
    "write_file",
    "write_stdin",
}
DIRECT_WRITE_TOOLS = {"apply_patch", "Edit", "Write", "write_file"}
SHELL_TOOLS = {"Bash", "exec_command", "functions.exec_command", "shell"}
SHELL_CONTROL = re.compile(r"[;&|<>`$\n\r]")
SENSITIVE_LIFECYCLE_COMMAND = re.compile(
    r"(?:git\s+(?:add|branch|checkout|cherry-pick|clean|commit|config|fetch|merge|"
    r"pull|push|rebase|remote|reset|switch|tag|worktree)|"
    r"gh\s+(?:api|issue|pr|release|repo|run|secret|variable|workflow))"
)
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


def _command(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    for field in ("command", "cmd"):
        value = tool_input.get(field)
        if isinstance(value, str):
            return value
    return ""


def _lifecycle_stages_for_tool(
    payload: Dict[str, Any],
) -> Tuple[set[str], Optional[str]]:
    """Classify only high-confidence lifecycle mutations.

    An empty stage set means that this local hook cannot classify the command;
    it is not an allow decision.  Sensitive GitHub/Git mutations fail closed
    when shell composition prevents exact classification.
    """

    name = _tool_name(payload)
    if name in DIRECT_WRITE_TOOLS:
        return {"modify_allowed_paths"}, None
    if name not in SHELL_TOOLS:
        return set(), None
    command = _command(payload).strip()
    if not command:
        return set(), None
    if SHELL_CONTROL.search(command):
        if SENSITIVE_LIFECYCLE_COMMAND.search(command):
            return set(), "composed sensitive lifecycle command cannot be classified safely"
        return set(), None
    try:
        tokens = shlex.split(command)
    except ValueError:
        return set(), "lifecycle command cannot be parsed safely"
    if len(tokens) < 2:
        return set(), None

    executable = Path(tokens[0]).name
    if executable == "git":
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
            if any(argument == "--output" or argument.startswith("--output=") for argument in tokens[2:]):
                return set(), "write-capable Git read command is outside the lifecycle envelope"
            return set(), None
        if subcommand in {"add", "commit"}:
            return {"milestone_commit"}, None
        if subcommand == "fetch":
            return {"validate"}, None
        if subcommand == "switch" and any(
            token in {"-c", "--create"} for token in tokens[2:]
        ):
            return {"create_task_branch"}, None
        if subcommand == "push":
            deleting = "--delete" in tokens[2:] or any(
                token.startswith(":") for token in tokens[2:]
            )
            return {"delete_remote_branch" if deleting else "push_topic_branch"}, None
        if subcommand == "branch" and any(
            token in {"-d", "-D", "--delete"} for token in tokens[2:]
        ):
            return {"delete_local_branch"}, None
        if subcommand == "branch" and any(
            token in {"--contains", "--list", "--show-current", "-l"}
            for token in tokens[2:]
        ):
            return set(), None
        if subcommand == "worktree" and len(tokens) >= 3 and tokens[2] == "remove":
            return {"remove_linked_worktree"}, None
        if subcommand == "worktree" and len(tokens) >= 3 and tokens[2] == "list":
            return set(), None
        if subcommand == "remote" and len(tokens) >= 3 and tokens[2] in {
            "-v",
            "get-url",
            "show",
        }:
            return set(), None
        if subcommand == "config" and len(tokens) >= 3 and tokens[2] in {
            "--get",
            "--get-all",
            "--list",
            "-l",
        }:
            return set(), None
        if subcommand == "tag" and len(tokens) >= 3 and tokens[2] in {"--list", "-l"}:
            return set(), None
        return set(), f"git {subcommand} is outside the classified lifecycle commands"

    if executable != "gh":
        if SENSITIVE_LIFECYCLE_COMMAND.search(command):
            return set(), "wrapped sensitive lifecycle command is not allowed"
        return set(), None
    if tokens[1] == "repo" and len(tokens) >= 3 and tokens[2] == "view":
        return set(), None
    if tokens[1] == "workflow" and len(tokens) >= 3 and tokens[2] in {"list", "view"}:
        return set(), None
    if tokens[1] == "run" and len(tokens) >= 3 and tokens[2] in {"list", "view"}:
        return set(), None
    if tokens[1] == "auth" and len(tokens) >= 3 and tokens[2] == "status":
        return set(), None
    if tokens[1] == "search":
        return set(), None
    if tokens[1] in {"release", "workflow", "repo", "run", "secret", "variable"}:
        return set(), f"gh {tokens[1]} mutation is outside a Git lifecycle approval envelope"
    if tokens[1] == "api":
        mutating_method = any(
            token in {"-X", "--method"}
            or token.startswith("--method=")
            or token.startswith("-X")
            or token in {"-f", "-F", "--field", "--raw-field", "--input"}
            or token.startswith("--field=")
            or token.startswith("--raw-field=")
            or token.startswith("--input=")
            for token in tokens[2:]
        )
        if mutating_method:
            return set(), "mutating gh api is outside the classified lifecycle commands"
        return set(), None
    if tokens[1] != "pr" or len(tokens) < 3:
        return set(), None
    operation = tokens[2]
    mapping = {
        "create": "create_draft_pr",
        "edit": "update_pr_metadata",
        "ready": "mark_ready_for_review",
        "merge": "merge_pr",
    }
    if operation in mapping and any(
        re.fullmatch(r"-[A-Za-z]", argument) for argument in tokens[3:]
    ):
        return set(), "short flags are not allowed for lifecycle PR mutations"
    if operation == "create" and "--draft" not in tokens[3:]:
        return set(), "lifecycle PR creation must use --draft"
    if operation == "ready" and "--undo" in tokens[3:]:
        return set(), "gh pr ready --undo is not an approved lifecycle stage"
    if operation == "merge" and "--delete-branch" in tokens[3:]:
        return set(), (
            "gh pr merge --delete-branch has ambiguous local/remote cleanup effects; "
            "merge and exact cleanup must be separate commands"
        )
    if operation == "merge" and any(
        option in tokens[3:] for option in {"--admin", "--auto", "--disable-auto"}
    ):
        return set(), "admin/auto merge modes are outside a lifecycle approval envelope"
    if operation in mapping:
        return {mapping[operation]}, None
    if operation in {"checks", "diff", "list", "status", "view"}:
        return set(), None
    if operation in {"close", "reopen"}:
        return set(), f"gh pr {operation} is not a lifecycle-envelope stage"
    return set(), f"gh pr {operation} is outside the classified lifecycle commands"


def _option_value(arguments: list[str], option: str) -> Optional[str]:
    for index, argument in enumerate(arguments):
        if argument == option and index + 1 < len(arguments):
            return arguments[index + 1]
        prefix = option + "="
        if argument.startswith(prefix):
            return argument[len(prefix):]
    return None


def _option_values(arguments: list[str], option: str) -> list[str]:
    values = []
    for index, argument in enumerate(arguments):
        if argument == option and index + 1 < len(arguments):
            values.append(arguments[index + 1])
        else:
            prefix = option + "="
            if argument.startswith(prefix):
                values.append(argument[len(prefix):])
    return values


def _flatten_comma_values(values: list[str]) -> set[str]:
    return {
        item.strip()
        for value in values
        for item in value.split(",")
        if item.strip()
    }


def _pr_metadata_mismatch(
    arguments: list[str], metadata: Dict[str, Any], *, create: bool
) -> Optional[str]:
    title = _option_value(arguments, "--title")
    if create and title != metadata["title"]:
        return "lifecycle PR creation must use the exact approved --title"
    if not create and title is not None and title != metadata["title"]:
        return "lifecycle PR edit title differs from the approved title"

    body_inputs = _option_values(arguments, "--body") + _option_values(
        arguments, "--body-file"
    )
    if create and len(body_inputs) != 1:
        return "lifecycle PR creation must provide exactly one explicit body input"
    if any(
        argument in {"--fill", "--fill-first", "--fill-verbose"}
        for argument in arguments
    ):
        return "implicit fill-generated PR metadata is outside the lifecycle envelope"

    label_option = "--label" if create else "--add-label"
    labels = _flatten_comma_values(_option_values(arguments, label_option))
    if labels - set(metadata["labels"]):
        return "lifecycle PR labels exceed the exact approved label set"

    reviewer_option = "--reviewer" if create else "--add-reviewer"
    reviewers = _flatten_comma_values(_option_values(arguments, reviewer_option))
    if reviewers - set(metadata["reviewers"]):
        return "lifecycle PR reviewers exceed the exact approved reviewer set"

    milestone = _option_value(arguments, "--milestone")
    if milestone is not None and milestone != metadata["milestone"]:
        return "lifecycle PR milestone differs from the exact approved milestone"

    forbidden_metadata_flags = {
        "--add-assignee",
        "--add-project",
        "--assignee",
        "--dry-run",
        "--editor",
        "--no-maintainer-edit",
        "--project",
        "--recover",
        "--remove-assignee",
        "--remove-label",
        "--remove-milestone",
        "--remove-project",
        "--remove-reviewer",
        "--template",
        "--web",
    }
    if any(
        argument in forbidden_metadata_flags
        or any(argument.startswith(flag + "=") for flag in forbidden_metadata_flags)
        for argument in arguments
    ):
        return "PR metadata removal, assignee, or project mutation is outside the envelope"
    return None


def _git_read(root: Path, arguments: list[str]) -> Optional[str]:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=str(root),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else None


def _repository_slug_from_remote_url(value: str) -> Optional[str]:
    if "://" in value:
        path = urlparse(value).path
    elif ":" in value and not value.startswith("/"):
        path = value.split(":", 1)[1]
    else:
        path = value
    normalized = path.rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    parts = [part for part in normalized.strip("/").split("/") if part]
    return "/".join(parts[-2:]) if len(parts) >= 2 else None


def _repo_path_allowed(candidate: str, patterns: list[str]) -> bool:
    if not candidate or candidate.startswith(":") or "\x00" in candidate:
        return False
    path = PurePosixPath(candidate)
    if path.is_absolute() or ".." in path.parts:
        return False
    normalized = path.as_posix()
    for pattern in patterns:
        if pattern == ".":
            return True
        base = pattern.rstrip("/")
        if not any(character in pattern for character in "*?["):
            if normalized == base or normalized.startswith(base + "/"):
                return True
        elif path.match(pattern):
            return True
    return False


def _git_push_mismatch(tokens: list[str], repository: Dict[str, Any]) -> Optional[str]:
    arguments = tokens[2:]
    if any(
        argument.startswith("--force")
        or argument.startswith("+")
        or (argument.startswith("-") and not argument.startswith("--") and "f" in argument)
        for argument in arguments
    ):
        return "force-push is outside a lifecycle approval envelope"
    deleting = "--delete" in arguments or any(
        argument.startswith(":") for argument in arguments
    )
    retained = [
        argument
        for argument in arguments
        if argument not in {"--delete", "--set-upstream", "-u"}
    ]
    remote = repository["remote"]
    topic = repository["topic_branch"]
    if deleting:
        if retained != [remote, topic]:
            return "remote cleanup must name the exact remote and topic branch"
        return None
    allowed = {
        (remote, topic),
        (remote, f"HEAD:{topic}"),
        (remote, f"HEAD:refs/heads/{topic}"),
    }
    if tuple(retained) not in allowed:
        return "push must name the exact remote and topic-branch refspec"
    return None


def _lifecycle_command_matches_envelope(
    root: Path,
    payload: Dict[str, Any],
    envelope: Dict[str, Any],
    required_stages: set[str],
) -> Optional[str]:
    repository = envelope["repository"]
    remote_bound_stages = required_stages & {
        "push_topic_branch",
        "create_draft_pr",
        "update_pr_metadata",
        "mark_ready_for_review",
        "merge_pr",
        "delete_remote_branch",
    }
    if remote_bound_stages:
        remote_url = _git_read(root, ["remote", "get-url", repository["remote"]])
        if (
            remote_url is None
            or _repository_slug_from_remote_url(remote_url) != repository["slug"]
        ):
            return "Git remote URL does not match the lifecycle repository slug"
    base_bound_stages = required_stages & {
        "push_topic_branch",
        "create_draft_pr",
        "update_pr_metadata",
        "apply_review_fixes",
        "mark_ready_for_review",
        "merge_pr",
    }
    if base_bound_stages:
        base_ref = (
            f"refs/remotes/{repository['remote']}/{repository['base_branch']}"
        )
        observed_base = _git_read(root, ["rev-parse", base_ref])
        if observed_base != repository["base_sha"]:
            return "current remote base SHA does not match the lifecycle envelope"
    if "create_task_branch" in required_stages:
        observed_head = _git_read(root, ["rev-parse", "HEAD"])
        if observed_head != repository["base_sha"]:
            return "task branch must be created from the exact approved base SHA"
    branch_bound_stages = required_stages - {
        "create_task_branch",
        "remove_linked_worktree",
        "delete_local_branch",
    }
    if branch_bound_stages:
        current_branch = _git_read(root, ["symbolic-ref", "--quiet", "--short", "HEAD"])
        if current_branch != repository["topic_branch"]:
            return "current Git branch does not match the lifecycle topic branch"

    command = _command(payload).strip()
    if not command or SHELL_CONTROL.search(command):
        return None
    try:
        tokens = shlex.split(command)
    except ValueError:
        return "lifecycle command cannot be parsed safely"
    if len(tokens) < 2:
        return None

    executable = Path(tokens[0]).name
    if executable == "git":
        subcommand = tokens[1]
        if subcommand == "switch" and "create_task_branch" in required_stages:
            expected = repository["topic_branch"]
            if tokens not in (
                ["git", "switch", "-c", expected],
                ["git", "switch", "--create", expected],
            ):
                return "task-branch creation must name the exact lifecycle topic branch"
        elif subcommand == "add":
            arguments = tokens[2:]
            if any(
                argument in {".", "-A", "--all", "-u", "--update"}
                or (argument.startswith("-") and argument != "--")
                for argument in arguments
            ):
                return "git add must use explicit in-scope paths after --"
            paths = [argument for argument in arguments if argument != "--"]
            if not paths or not all(
                _repo_path_allowed(path, envelope["scope"]["allowed_paths"])
                for path in paths
            ):
                return "git add contains a missing or out-of-scope path"
        elif subcommand == "commit":
            arguments = tokens[2:]
            if (
                len(arguments) != 2
                or arguments[0] not in {"-m", "--message"}
                or not arguments[1].strip()
            ):
                return "lifecycle commits must use only one explicit non-empty -m message"
        elif subcommand == "fetch":
            allowed_fetches = {
                (
                    "git",
                    "fetch",
                    repository["remote"],
                    repository["base_branch"],
                ),
                (
                    "git",
                    "fetch",
                    "--no-tags",
                    repository["remote"],
                    repository["base_branch"],
                ),
            }
            if tuple(tokens) not in allowed_fetches:
                return "lifecycle fetch must target only the exact remote base branch"
            remote_url = _git_read(
                root, ["remote", "get-url", repository["remote"]]
            )
            if (
                remote_url is None
                or _repository_slug_from_remote_url(remote_url)
                != repository["slug"]
            ):
                return "Git remote URL does not match the lifecycle repository slug"
        elif subcommand == "push":
            return _git_push_mismatch(tokens, repository)
        return None

    if len(tokens) < 3 or executable != "gh" or tokens[1] != "pr":
        return None

    operation = tokens[2]
    pull_request = envelope["pull_request"]
    if operation in {"create", "edit", "ready", "merge"}:
        selected_repository = _option_value(tokens[3:], "--repo")
        if selected_repository != repository["slug"]:
            return "lifecycle PR mutation must name the exact --repo owner/repository"
    if operation == "create":
        base = _option_value(tokens[3:], "--base")
        head = _option_value(tokens[3:], "--head")
        if base != repository["base_branch"]:
            return "lifecycle PR creation must name the exact --base branch"
        if head != repository["topic_branch"]:
            return "lifecycle PR creation must name the exact --head topic branch"
        metadata_error = _pr_metadata_mismatch(
            tokens[3:], pull_request["metadata"], create=True
        )
        if metadata_error:
            return metadata_error
    elif operation == "edit":
        if any(
            argument == "--base" or argument.startswith("--base=")
            for argument in tokens[3:]
        ):
            return "changing the PR base is outside a lifecycle approval envelope"
        metadata_error = _pr_metadata_mismatch(
            tokens[3:], pull_request["metadata"], create=False
        )
        if metadata_error:
            return metadata_error
    elif operation == "merge":
        selected_methods = {
            option for option in {"--merge", "--squash", "--rebase"} if option in tokens[3:]
        }
        merge_method = pull_request["merge_method"]
        if merge_method == "queue":
            if selected_methods:
                return "lifecycle merge queue must not specify a direct merge method"
        else:
            expected_method = "--" + merge_method
            if selected_methods != {expected_method}:
                return f"lifecycle merge must use the exact method {expected_method}"
        if _option_value(tokens[3:], "--match-head-commit") is None:
            return "lifecycle merge must bind the run-produced tip with --match-head-commit"
        expected_head = _git_read(root, ["rev-parse", "HEAD"])
        matched_head = _option_value(tokens[3:], "--match-head-commit")
        if expected_head is None or matched_head != expected_head:
            return "--match-head-commit does not equal the current run-produced local tip"
    return None


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
        if errors:
            reason = "Contracted mutating tool denied: " + "; ".join(errors)
        else:
            envelope, envelope_error = run_guard._read_json_regular(
                status.root / run_guard.STATE_DIRECTORY / run_guard.ENVELOPE_NAME
            )
            if envelope_error or envelope is None:
                reason = "Contracted mutating tool denied: action envelope readback failed"
            elif envelope.get("schema_version") != 2:
                return None
            else:
                required_stages, classification_error = _lifecycle_stages_for_tool(payload)
                if classification_error:
                    reason = "Contracted mutating tool denied: " + classification_error
                else:
                    allowed_stages = set(envelope["scope"]["allowed_stages"])
                    missing = sorted(required_stages - allowed_stages)
                    command_mismatch = _lifecycle_command_matches_envelope(
                        status.root,
                        payload,
                        envelope,
                        required_stages,
                    )
                    if not missing and command_mismatch is None:
                        return None
                    if missing:
                        reason = (
                            "Contracted mutating tool denied: lifecycle stage(s) not approved: "
                            + ", ".join(missing)
                        )
                    else:
                        reason = "Contracted mutating tool denied: " + command_mismatch
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
