#!/usr/bin/env bash
set -euo pipefail

base_sha="${1:-}"
head_sha="${2:-HEAD}"
output_name="${CI_SCOPE_OUTPUT_NAME:-run_heavy}"
scope_mode="${CI_SCOPE_MODE:-non-doc}"
skip_docs_only="${CI_SKIP_DOCS_ONLY:-true}"
path_regex="${CI_SCOPE_PATH_REGEX:-}"

if ! [[ "$output_name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
  printf '[ci-scope] invalid output name: %s\n' "$output_name" >&2
  exit 2
fi

emit() {
  local value="$1"
  local reason="$2"

  printf '[ci-scope] %s=%s (%s)\n' "$output_name" "$value" "$reason"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf '%s=%s\n' "$output_name" "$value" >>"$GITHUB_OUTPUT"
  fi
}

case "$scope_mode" in
  all)
    emit true "scope mode is all"
    exit 0
    ;;
  non-doc)
    if [[ "$skip_docs_only" != "true" && "$skip_docs_only" != "false" ]]; then
      printf '[ci-scope] CI_SKIP_DOCS_ONLY must be true or false\n' >&2
      exit 2
    fi
    if [[ "$skip_docs_only" == "false" ]]; then
      emit true "docs-only optimization is disabled"
      exit 0
    fi
    ;;
  paths)
    if [[ -z "$path_regex" ]]; then
      printf '[ci-scope] CI_SCOPE_PATH_REGEX is required in paths mode\n' >&2
      exit 2
    fi
    ;;
  *)
    printf '[ci-scope] unsupported CI_SCOPE_MODE: %s\n' "$scope_mode" >&2
    exit 2
    ;;
esac

if [[ -z "$base_sha" || "$base_sha" =~ ^0+$ ]]; then
  emit true "base revision is unavailable; failing open"
  exit 0
fi

if ! git cat-file -e "$base_sha^{commit}" 2>/dev/null; then
  emit true "base revision is not present; failing open"
  exit 0
fi

if ! changed_files="$(git diff --name-only "$base_sha" "$head_sha")"; then
  emit true "change detection failed; failing open"
  exit 0
fi

if [[ -z "$changed_files" ]]; then
  emit true "empty change set; failing open"
  exit 0
fi

# Do not use grep -q in these pipelines. With pipefail, an early grep exit can
# SIGPIPE printf for large diffs and invert a positive match.
if [[ "$scope_mode" == "paths" ]]; then
  if printf '%s\n' "$changed_files" | grep -E "$path_regex" >/dev/null; then
    emit true "a changed path matches the configured scope"
  else
    emit false "no changed path matches the configured scope"
  fi
  exit 0
fi

if printf '%s\n' "$changed_files" | grep -Eiv '(^|/)[^/]+\.(md|mdx)$|^(LICENSE|NOTICE)(\.[^/]*)?$' >/dev/null; then
  emit true "non-documentation files changed"
else
  emit false "only Markdown or root license/notice files changed"
fi
