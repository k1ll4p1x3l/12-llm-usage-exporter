#!/usr/bin/env python3
"""Fail-closed, session-scoped guard for accidental primary-checkout work.

The hook is stdlib-only and follows the current Codex command-hook JSON
contract. Approval is accepted only from an exact user prompt and is stored as
a minimal marker outside the repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


CONFIRMATION_PROMPT = "MAIN_WORKTREE_OK"
STATE_DIRECTORY = Path(tempfile.gettempdir()) / "codex-worktree-guard"
STATE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class WorktreeStatus:
    kind: str  # linked, primary, non_git, unknown
    root: Path
    detail: str = ""


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


def detect_worktree(cwd: Path) -> WorktreeStatus:
    cwd = cwd.expanduser().resolve()
    rc, inside, error = _run_git(["rev-parse", "--is-inside-work-tree"], cwd)
    if rc != 0:
        lowered = error.lower()
        if "not a git repository" in lowered or "outside repository" in lowered:
            return WorktreeStatus("non_git", cwd)
        return WorktreeStatus("unknown", cwd, error or "git detection failed")
    if inside != "true":
        return WorktreeStatus("non_git", cwd)

    rc, root_raw, error = _run_git(["rev-parse", "--show-toplevel"], cwd)
    if rc != 0 or not root_raw:
        return WorktreeStatus("unknown", cwd, error or "missing worktree root")
    root = Path(root_raw).resolve()

    rc, git_dir_raw, error = _run_git(["rev-parse", "--absolute-git-dir"], root)
    if rc != 0 or not git_dir_raw:
        return WorktreeStatus("unknown", root, error or "missing git directory")
    git_dir = Path(git_dir_raw).resolve()

    rc, common_raw, error = _run_git(["rev-parse", "--git-common-dir"], root)
    if rc != 0 or not common_raw:
        return WorktreeStatus("unknown", root, error or "missing common git directory")
    common_dir = Path(common_raw)
    if not common_dir.is_absolute():
        common_dir = (root / common_dir).resolve()
    else:
        common_dir = common_dir.resolve()

    if git_dir == common_dir:
        return WorktreeStatus("primary", root)
    return WorktreeStatus("linked", root)


def _session_id(payload: Dict[str, Any]) -> Optional[str]:
    value = payload.get("session_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _cwd(payload: Dict[str, Any]) -> Path:
    value = payload.get("cwd")
    if isinstance(value, str) and value.strip():
        return Path(value)
    return Path.cwd()


def _state_key(root: Path, session_id: str) -> str:
    digest = hashlib.sha256()
    digest.update(str(root.resolve()).encode("utf-8"))
    digest.update(b"\0")
    digest.update(session_id.encode("utf-8"))
    return digest.hexdigest()


def _ensure_state_directory() -> None:
    try:
        STATE_DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=False)
    except FileExistsError:
        metadata = STATE_DIRECTORY.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or STATE_DIRECTORY.is_symlink():
            raise OSError(f"unsafe worktree-guard state path: {STATE_DIRECTORY}")
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            raise OSError(f"worktree-guard state directory has unexpected owner: {STATE_DIRECTORY}")
    os.chmod(STATE_DIRECTORY, 0o700)


def _prune_stale_markers() -> None:
    try:
        _ensure_state_directory()
        threshold = time.time() - STATE_MAX_AGE_SECONDS
        for path in STATE_DIRECTORY.glob("*.json"):
            try:
                if path.stat().st_mtime < threshold:
                    path.unlink()
            except OSError:
                continue
    except OSError:
        return


def _state_path(root: Path, session_id: Optional[str]) -> Optional[Path]:
    if not session_id:
        return None
    return STATE_DIRECTORY / f"{_state_key(root, session_id)}.json"


def _approved(root: Path, session_id: Optional[str]) -> bool:
    path = _state_path(root, session_id)
    if path is None:
        return False
    descriptor: Optional[int] = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return False
        if stat.S_IMODE(metadata.st_mode) != 0o600:
            return False
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            return False
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = None
            return json.load(handle) == {"approved": True}
    except (OSError, json.JSONDecodeError):
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _approve(root: Path, session_id: Optional[str]) -> bool:
    path = _state_path(root, session_id)
    if path is None:
        return False
    _ensure_state_directory()
    temporary = STATE_DIRECTORY / f".{path.stem}.{secrets.token_hex(8)}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write('{"approved":true}\n')
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return True


def _clear(root: Path, session_id: Optional[str]) -> None:
    path = _state_path(root, session_id)
    if path is None:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _context(event: str, message: str) -> Dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": message,
        }
    }


def _gate_message(status: WorktreeStatus, approved: bool) -> str:
    if status.kind == "linked":
        return (
            "WORKTREE_GUARD: linked Git worktree verified. Normal work may proceed "
            "within the user's authorized scope."
        )
    if status.kind == "non_git":
        return "WORKTREE_GUARD: current directory is not a Git worktree; no worktree gate applies."
    if approved:
        return (
            "WORKTREE_GUARD: explicit MAIN_WORKTREE_OK confirmation is recorded for "
            "this session and repository. Work may proceed within the remaining scope."
        )
    label = "primary Git checkout" if status.kind == "primary" else "unknown Git topology"
    return (
        f"WORKTREE_GUARD: {label} detected. Do not call local tools. Warn the user that "
        "parallel work in this checkout may conflict, ask whether this is explicitly intended, "
        "and require the exact standalone reply MAIN_WORKTREE_OK. Retain the original task and "
        "continue it only after that reply."
    )


def handle_session_start(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = detect_worktree(_cwd(payload))
    session_id = _session_id(payload)
    source = payload.get("source")
    if source not in {"resume", "compact"}:
        _clear(status.root, session_id)
    _prune_stale_markers()
    return _context("SessionStart", _gate_message(status, _approved(status.root, session_id)))


def handle_user_prompt_submit(payload: Dict[str, Any]) -> Dict[str, Any]:
    status = detect_worktree(_cwd(payload))
    session_id = _session_id(payload)
    prompt = payload.get("prompt")
    exact_confirmation = isinstance(prompt, str) and prompt.strip() == CONFIRMATION_PROMPT
    if status.kind in {"primary", "unknown"} and exact_confirmation:
        _approve(status.root, session_id)
    return _context(
        "UserPromptSubmit",
        _gate_message(status, _approved(status.root, session_id)),
    )


def handle_pre_tool_use(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    status = detect_worktree(_cwd(payload))
    session_id = _session_id(payload)
    if status.kind in {"linked", "non_git"} or _approved(status.root, session_id):
        return None
    reason = (
        "Worktree guard denied this local tool call: the primary checkout or an unknown "
        "Git topology requires the user's exact standalone MAIN_WORKTREE_OK reply first."
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def handle_session_end(payload: Dict[str, Any]) -> None:
    status = detect_worktree(_cwd(payload))
    _clear(status.root, _session_id(payload))
    return None


def dispatch(payload: Dict[str, Any], argv_event: Optional[str] = None) -> Optional[Dict[str, Any]]:
    event = payload.get("hook_event_name")
    if not isinstance(event, str) or not event:
        event = argv_event or ""
    if event == "SessionStart":
        return handle_session_start(payload)
    if event == "UserPromptSubmit":
        return handle_user_prompt_submit(payload)
    if event == "PreToolUse":
        return handle_pre_tool_use(payload)
    if event == "SessionEnd":
        return handle_session_end(payload)
    return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            raise ValueError("hook input must be a JSON object")
        argv_event = sys.argv[1] if len(sys.argv) > 1 else None
        result = dispatch(payload, argv_event)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        # A malformed/unsafe PreToolUse must fail closed. Other hook events may
        # inject diagnostic context without inventing an approval.
        event = sys.argv[1] if len(sys.argv) > 1 else "PreToolUse"
        if event == "PreToolUse":
            result = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Worktree guard failed closed: {exc}",
                }
            }
        else:
            result = _context(event, f"WORKTREE_GUARD: check failed; treat topology as unknown: {exc}")
    if result is not None:
        sys.stdout.write(json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
