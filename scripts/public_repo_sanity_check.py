#!/usr/bin/env python3
"""Lightweight public-repo sanity check.

This is not a full secret scanner. It catches common mistakes before publishing.
Use established tools as well for serious repositories.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {'.git', '__pycache__', '.venv', 'venv', 'node_modules'}
SKIP_FILES = {
    'scripts/public_repo_sanity_check.py',
    'docs/PUBLIC_REPO_SAFETY.md',
    'templates/project/PUBLIC_REPO_GITIGNORE_SNIPPET.template',
    '.gitignore',
}
TEXT_NAMES = {'AGENTS.md', 'README.md', 'TREE.txt'}
TEXT_SUFFIXES = {'.md', '.txt', '.toml', '.yml', '.yaml', '.json', '.py', '.sh', '.rules', '.example', '.template'}

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ('private reference path', re.compile(r'(^|/)references/(private|local)(/|$)')),
    ('RFC1918 private IPv4', re.compile(r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b')),
    ('private key block', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('obvious assigned secret', re.compile(r'(?i)\b(password|passwd|api[_-]?key|secret|token|bearer)\b\s*[:=]\s*[^\s#]+')),
]


SAFE_PERMISSION_VALUES = {'read', 'write', 'none'}


def is_text(path: Path) -> bool:
    return path.name in TEXT_NAMES or path.suffix.lower() in TEXT_SUFFIXES


def is_false_positive(label: str, line: str) -> bool:
    if label != 'obvious assigned secret':
        return False
    key_value = re.match(r'(?i)^\s*[a-z0-9_.-]*token\s*:\s*([a-z-]+)\s*$', line)
    return bool(key_value and key_value.group(1).lower() in SAFE_PERMISSION_VALUES)


def main() -> int:
    extra = os.environ.get('PUBLIC_SCAN_EXTRA_REGEX')
    if extra:
        try:
            PATTERNS.append(('extra user regex', re.compile(extra, re.I)))
        except re.error as exc:
            print(f'Invalid PUBLIC_SCAN_EXTRA_REGEX: {exc}', file=sys.stderr)
            return 2

    findings: list[str] = []
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT).as_posix()
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if rel in SKIP_FILES:
            continue
        if path.is_dir():
            for label, pattern in PATTERNS[:1]:
                if pattern.search(rel + '/'):
                    findings.append(f'{rel}/: {label}')
            continue
        if not path.is_file() or not is_text(path):
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pattern in PATTERNS:
                if pattern.search(line) and not is_false_positive(label, line):
                    findings.append(f'{rel}:{lineno}: {label}: {line[:180]}')

    if findings:
        print('Potential public-repo safety findings:')
        for finding in findings:
            print(f'- {finding}')
        return 1
    print('OK: no obvious public-repo safety findings detected.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
