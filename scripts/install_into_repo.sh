#!/usr/bin/env bash
set -euo pipefail

PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-$(pwd)}"
STAMP="$(date +%Y%m%d-%H%M%S)"

if [[ ! -d "$TARGET" ]]; then
  echo "Target directory does not exist: $TARGET" >&2
  exit 1
fi

copy_path() {
  local rel="$1"
  local src="$PACK_DIR/$rel"
  local dst="$TARGET/$rel"

  if [[ ! -e "$src" ]]; then
    return 0
  fi

  if [[ -e "$dst" ]]; then
    local backup="$dst.bak.$STAMP"
    echo "Backing up existing $rel -> ${rel}.bak.$STAMP"
    mv "$dst" "$backup"
  fi

  mkdir -p "$(dirname "$dst")"
  cp -a "$src" "$dst"
  echo "Installed $rel"
}

copy_path "AGENTS.md"
copy_path ".codex"
copy_path ".agents"
copy_path "docs"
copy_path "templates"
copy_path "references/README.md"
copy_path "scripts/verify_codex_agent_pack.py"
copy_path "scripts/codex_budget_guard.py"
copy_path "scripts/create_repo_context.py"
copy_path "scripts/public_repo_sanity_check.py"

chmod +x "$TARGET/scripts/verify_codex_agent_pack.py" "$TARGET/scripts/codex_budget_guard.py" "$TARGET/scripts/create_repo_context.py" "$TARGET/scripts/public_repo_sanity_check.py" 2>/dev/null || true

echo
if command -v python3 >/dev/null 2>&1; then
  (cd "$TARGET" && python3 scripts/verify_codex_agent_pack.py) || true
else
  echo "python3 not found; skipped validation. Naturally, the one tool everyone assumes exists chose drama."
fi

echo
cat <<EOF
Installed Codex Agent Orchestration Pack into:
  $TARGET

Recommended next steps:
  cd "$TARGET"
  python3 scripts/create_repo_context.py --write
  python3 scripts/codex_budget_guard.py init
  python3 scripts/public_repo_sanity_check.py
  codex -m gpt-5.5
EOF
