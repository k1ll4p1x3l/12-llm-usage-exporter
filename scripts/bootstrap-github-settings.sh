#!/usr/bin/env bash

set -euo pipefail

DRY_RUN="${DRY_RUN:-1}"
REPO="${GITHUB_REPO:-OWNER/REPOSITORY}"
BRANCH="${PROTECTION_BRANCH:-main}"
REQUIRED_STATUS_CHECKS_JSON="${REQUIRED_STATUS_CHECKS_JSON:-[\"ci\",\"analyze\",\"vulncheck\",\"check-milestone\",\"ensure-changelog\"]}"
REQUIRE_LINEAR_HISTORY="${REQUIRE_LINEAR_HISTORY:-false}"
REQUIRED_APPROVING_REVIEW_COUNT="${REQUIRED_APPROVING_REVIEW_COUNT:-0}"

log() {
  printf '[github-settings-preview] %s\n' "$*"
}

fail() {
  printf '[github-settings-preview] %s\n' "$*" >&2
  exit 2
}

preview() {
  printf '[preview]'
  printf ' %q' "$@"
  printf '\n'
}

validate_inputs() {
  [[ "$DRY_RUN" == "1" ]] || fail "apply mode is disabled; this helper is preview-only"
  [[ "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || fail "invalid GITHUB_REPO"
  [[ "$BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]] || fail "invalid PROTECTION_BRANCH"
  [[ "$REQUIRED_APPROVING_REVIEW_COUNT" =~ ^[0-9]+$ ]] || fail "invalid REQUIRED_APPROVING_REVIEW_COUNT"
  case "$REQUIRE_LINEAR_HISTORY" in
    true|false|0|1) ;;
    *) fail "REQUIRE_LINEAR_HISTORY must be true, false, 0, or 1" ;;
  esac
  command -v python3 >/dev/null 2>&1 || fail "python3 is required"
  REQUIRED_STATUS_CHECKS_JSON="$({
    python3 -c '
import json
import sys

value = json.loads(sys.argv[1])
if not isinstance(value, list) or not value or not all(
    isinstance(item, str) and item and len(item) <= 100 for item in value
):
    raise SystemExit("status checks must be a non-empty JSON string array")
if len(value) != len(set(value)):
    raise SystemExit("status checks must be unique")
print(json.dumps(value, separators=(",", ":")))
' "$REQUIRED_STATUS_CHECKS_JSON"
  } 2>&1)" || fail "invalid REQUIRED_STATUS_CHECKS_JSON: $REQUIRED_STATUS_CHECKS_JSON"
}

branch_protection_payload() {
  local linear_history=false
  if [[ "$REQUIRE_LINEAR_HISTORY" == "true" || "$REQUIRE_LINEAR_HISTORY" == "1" ]]; then
    linear_history=true
  fi
  python3 - "$REQUIRED_APPROVING_REVIEW_COUNT" "$REQUIRED_STATUS_CHECKS_JSON" "$linear_history" <<'PY'
import json
import sys

payload = {
    "required_pull_request_reviews": {
        "required_approving_review_count": int(sys.argv[1]),
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": False,
        "require_last_push_approval": False,
    },
    "required_status_checks": {"strict": True, "contexts": json.loads(sys.argv[2])},
    "required_conversation_resolution": False,
    "enforce_admins": True,
    "required_linear_history": sys.argv[3] == "true",
    "allow_force_pushes": False,
    "required_signatures": False,
    "allow_deletions": False,
    "lock_branch": False,
    "restrictions": None,
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
PY
}

main() {
  validate_inputs
  log "Previewing settings for $REPO; no network call, authentication, or mutation will run."

  preview gh api -X PATCH "repos/$REPO" \
    -H "Accept: application/vnd.github+json" \
    -F has_wiki=false -F has_discussions=true -F delete_branch_on_merge=true \
    -F allow_squash_merge=true -F allow_merge_commit=true -F allow_rebase_merge=true
  preview gh api -X PUT "repos/$REPO/topics" \
    -H "Accept: application/vnd.github+json" \
    -f 'names[]=go' -f 'names[]=prometheus' -f 'names[]=telemetry' \
    -f 'names[]=llm-tools' -f 'names[]=codex'
  preview gh api -X PUT "repos/$REPO/vulnerability-alerts" \
    -H "Accept: application/vnd.github+json"
  preview gh api -X PUT "repos/$REPO/automated-security-fixes" \
    -H "Accept: application/vnd.github+json"
  preview gh api -X PATCH "repos/$REPO" \
    -H "Accept: application/vnd.github+json" \
    -f 'security_and_analysis[secret_scanning][status]=enabled' \
    -f 'security_and_analysis[secret_scanning_push_protection][status]=enabled'
  preview gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" \
    -H "Accept: application/vnd.github+json" --input -
  branch_protection_payload
  log "Preview complete. Apply is intentionally unavailable in this repository."
}

main "$@"
