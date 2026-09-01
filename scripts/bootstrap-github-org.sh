#!/usr/bin/env bash

set -euo pipefail

DRY_RUN="${DRY_RUN:-1}"
REPO="${GITHUB_REPO:-OWNER/REPOSITORY}"
REQUIRE_BRANCH_PROTECTION="${REQUIRE_BRANCH_PROTECTION:-0}"
REQUIRED_BRANCH="${PROTECTION_BRANCH:-main}"
REQUIRED_STATUS_CHECKS_JSON="${REQUIRED_STATUS_CHECKS_JSON_OVERRIDE:-[\"ci\",\"analyze\",\"vulncheck\",\"check-milestone\",\"ensure-changelog\"]}"
REQUIRE_LINEAR_HISTORY="${REQUIRE_LINEAR_HISTORY:-false}"
REQUIRED_APPROVING_REVIEW_COUNT="${REQUIRED_APPROVING_REVIEW_COUNT:-0}"

log() {
  printf '[github-metadata-preview] %s\n' "$*"
}

fail() {
  printf '[github-metadata-preview] %s\n' "$*" >&2
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
  [[ "$REQUIRED_BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]] || fail "invalid PROTECTION_BRANCH"
  [[ "$REQUIRE_BRANCH_PROTECTION" =~ ^[01]$ ]] || fail "REQUIRE_BRANCH_PROTECTION must be 0 or 1"
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

ensure_label() {
  preview gh label create "$1" --repo "$REPO" --color "$2" --description "$3"
}

ensure_milestone() {
  preview gh api -X POST "repos/$REPO/milestones" \
    -f "title=$1" -f state=open -f "description=$2"
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

preview_branch_protection() {
  [[ "$REQUIRE_BRANCH_PROTECTION" == "1" ]] || {
    log "Branch protection preview skipped."
    return
  }
  preview gh api -X PUT "repos/$REPO/branches/$REQUIRED_BRANCH/protection" \
    -H "Accept: application/vnd.github+json" --input -
  branch_protection_payload
}

main() {
  validate_inputs
  log "Previewing GitHub metadata for $REPO; no network call or mutation will run."

  ensure_label "no-changelog-required" "0E8A16" "Skip CHANGELOG.md requirement for this PR."
  ensure_label "dependencies" "0366D6" "Dependency update or dependency maintenance."
  ensure_label "security" "D73A4A" "Security hardening or vulnerability handling."
  ensure_label "automation" "5319E7" "CI, release, or repository automation."
  ensure_label "area/core" "1D76DB" "Core collector, model, service, or exporter logic."
  ensure_label "area/docs" "0075CA" "Documentation-only or documentation-heavy change."
  ensure_label "area/provider" "FBCA04" "Provider policy, mapping, or integration work."
  ensure_label "area/release" "C2E0C6" "Release process, versioning, or distribution work."

  ensure_milestone "0.1" "MVP Foundation and JSON export baseline."
  ensure_milestone "0.2" "Release readiness and hardening workstream."
  ensure_milestone "0.3" "Provider expansion and policy coverage."
  ensure_milestone "0.4" "Public operations baseline and release tooling."
  preview_branch_protection
  log "Preview complete. Apply is intentionally unavailable in this repository."
}

main "$@"
