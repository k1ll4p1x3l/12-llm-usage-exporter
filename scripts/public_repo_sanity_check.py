#!/usr/bin/env python3
"""Fail-closed, redacting sanity scan for consumer-owned public repository data."""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}
SKIP_PREFIXES = (".agent-core/", ".agents/", ".codex/", "cache/", "dist/", "tmp/", "vendor/")
SKIP_FILES = {
    ".agent-core.lock.json",
    "AGENTS.md",
    ".gitignore",
    "scripts/public_repo_sanity_check.py",
}
MAX_FILES = 20_000
MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_TOTAL_SIZE = 128 * 1024 * 1024
CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
PRIVATE_PATH_PATTERN = re.compile(r"(^|/)references/(private|local)(/|$)")

CONTENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\b(?:gh[psuro]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("bearer credential", re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    (
        "assigned high-entropy secret",
        re.compile(
            r"(?i)\b(?:password|passwd|api[_-]?key|secret|token)\b\s*[:=]\s*[\"']?"
            r"[A-Za-z0-9._~+/=-]{16,}[\"']?"
        ),
    ),
    (
        "RFC1918 private IPv4",
        re.compile(
            r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|"
            r"192\.168\.\d{1,3}\.\d{1,3})\b"
        ),
    ),
    (
        "personal home path",
        re.compile(
            r"(?:/Users/(?!test(?:/|$)|example(?:/|$)|username(?:/|$))[A-Za-z0-9._-]+/|"
            r"/home/(?!test(?:/|$)|example(?:/|$)|user(?:/|$))[A-Za-z0-9._-]+/|"
            r"[A-Za-z]:\\Users\\(?!test\\|example\\|username\\)[^\\\s]+\\)"
        ),
    ),
)


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    label: str

    def render(self) -> str:
        suffix = f":{self.line}" if self.line else ""
        return f"{self.path}{suffix}: {self.label}"


def is_skipped(relative: str) -> bool:
    return relative in SKIP_FILES or any(relative.startswith(prefix) for prefix in SKIP_PREFIXES)


def canonical_root(raw_root: str) -> Path:
    candidate = Path(raw_root).expanduser()
    try:
        if candidate.is_symlink() or not candidate.is_dir():
            raise ValueError("scan root must be a non-symlink directory")
        return candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"cannot resolve scan root: {exc}") from exc


def configured_extra_literal(cli_value: str | None) -> str | None:
    value = cli_value if cli_value is not None else os.environ.get("PUBLIC_SCAN_EXTRA_LITERAL")
    if value is None:
        return None
    if not value or len(value) > 200 or CONTROL_PATTERN.search(value):
        raise ValueError("extra literal must contain 1-200 printable characters")
    return value


def stable_read(candidate: Path, expected: os.stat_result, relative: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(candidate, flags)
    except OSError as exc:
        raise ValueError(f"cannot open {relative} without following links: {exc}") from exc
    try:
        opened = os.fstat(descriptor)
        expected_identity = (
            expected.st_dev,
            expected.st_ino,
            expected.st_size,
            expected.st_mtime_ns,
        )
        opened_identity = (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
        )
        if not stat.S_ISREG(opened.st_mode) or opened_identity != expected_identity:
            raise ValueError(f"file changed before reading: {relative}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(MAX_FILE_SIZE + 1)
        after = os.fstat(descriptor)
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if after_identity != opened_identity or len(raw) != expected.st_size:
            raise ValueError(f"file changed while scanning: {relative}")
        return raw
    finally:
        os.close(descriptor)


def scan_text(
    relative: str, text: str, extra_literal: str | None, findings: list[Finding]
) -> None:
    for line_number, line in enumerate(text.splitlines(), 1):
        for label, pattern in CONTENT_PATTERNS:
            if pattern.search(line):
                findings.append(Finding(relative, line_number, label))
        if extra_literal is not None and extra_literal in line:
            findings.append(Finding(relative, line_number, "configured literal"))


def scan(root: Path, extra_literal: str | None) -> list[Finding]:
    findings: list[Finding] = []
    file_count = 0
    total_size = 0

    def walk_error(error: OSError) -> None:
        raise ValueError(f"cannot walk public tree: {error}")

    for current, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False, onerror=walk_error
    ):
        current_path = Path(current)
        directory_names.sort()
        file_names.sort()
        retained_directories: list[str] = []

        for name in directory_names:
            candidate = current_path / name
            relative = candidate.relative_to(root).as_posix()
            if name in SKIP_DIRS or is_skipped(relative + "/"):
                continue
            try:
                mode = candidate.lstat().st_mode
            except OSError as exc:
                raise ValueError(f"cannot inspect {relative}: {exc}") from exc
            if CONTROL_PATTERN.search(name):
                findings.append(Finding(relative + "/", 0, "control character in path"))
            if PRIVATE_PATH_PATTERN.search(relative + "/"):
                findings.append(Finding(relative + "/", 0, "private reference path"))
            if stat.S_ISLNK(mode):
                findings.append(Finding(relative + "/", 0, "symbolic link"))
                continue
            if not stat.S_ISDIR(mode):
                findings.append(Finding(relative + "/", 0, "special directory entry"))
                continue
            retained_directories.append(name)
        directory_names[:] = retained_directories

        for name in file_names:
            candidate = current_path / name
            relative = candidate.relative_to(root).as_posix()
            if is_skipped(relative):
                continue
            if CONTROL_PATTERN.search(name):
                findings.append(Finding(relative, 0, "control character in path"))
            if PRIVATE_PATH_PATTERN.search(relative):
                findings.append(Finding(relative, 0, "private reference path"))
            try:
                file_stat = candidate.lstat()
            except OSError as exc:
                raise ValueError(f"cannot inspect {relative}: {exc}") from exc
            if stat.S_ISLNK(file_stat.st_mode):
                findings.append(Finding(relative, 0, "symbolic link"))
                continue
            if not stat.S_ISREG(file_stat.st_mode):
                findings.append(Finding(relative, 0, "special file"))
                continue
            file_count += 1
            total_size += file_stat.st_size
            if file_count > MAX_FILES:
                raise ValueError(f"public tree exceeds {MAX_FILES} files")
            if file_stat.st_size > MAX_FILE_SIZE:
                findings.append(Finding(relative, 0, "file exceeds public scan size limit"))
                continue
            if total_size > MAX_TOTAL_SIZE:
                raise ValueError("public tree exceeds total scan size limit")
            raw = stable_read(candidate, file_stat, relative)
            if b"\x00" in raw:
                scan_text(relative, raw.decode("latin-1"), extra_literal, findings)
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                findings.append(Finding(relative, 0, "non-UTF-8 non-binary content"))
                continue
            scan_text(relative, text, extra_literal, findings)

    return sorted(set(findings))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--extra-literal")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = canonical_root(args.root)
        findings = scan(root, configured_extra_literal(args.extra_literal))
    except ValueError as exc:
        print(f"Public-safety scan failed closed: {exc}", file=sys.stderr)
        return 2

    if findings:
        print("Potential public-repository safety findings (values redacted):")
        for finding in findings:
            print(f"- {finding.render()}")
        return 1
    print("OK: consumer-owned public content passed the redacting safety scan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
