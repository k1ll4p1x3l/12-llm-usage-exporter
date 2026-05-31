#!/usr/bin/env bash

set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
REPO="${GITHUB_REPO:-}"
REQUIRE_BRANCH_PROTECTION="${REQUIRE_BRANCH_PROTECTION:-0}"
REQUIRED_BRANCH="${PROTECTION_BRANCH:-main}"
REQUIRED_STATUS_CHECKS_JSON='["ci","analyze","vulncheck","check-milestone","ensure-changelog"]'
REQUIRED_STATUS_CHECKS_JSON="${REQUIRED_STATUS_CHECKS_JSON_OVERRIDE:-$REQUIRED_STATUS_CHECKS_JSON}"
REQUIRE_LINEAR_HISTORY="${REQUIRE_LINEAR_HISTORY:-false}"
REQUIRED_APPROVING_REVIEW_COUNT="${REQUIRED_APPROVING_REVIEW_COUNT:-0}"

if [[ "$REQUIRE_LINEAR_HISTORY" == "1" ]]; then
  REQUIRE_LINEAR_HISTORY=true
else
  REQUIRE_LINEAR_HISTORY=false
fi

if [[ "${REQUIRED_STATUS_CHECKS_JSON}" != \[*\] ]]; then
  echo "Invalid REQUIRED_STATUS_CHECKS_JSON: ${REQUIRED_STATUS_CHECKS_JSON}" >&2
  exit 1
fi

if [[ ! "$REQUIRED_APPROVING_REVIEW_COUNT" =~ ^[0-9]+$ ]]; then
  echo "Invalid REQUIRED_APPROVING_REVIEW_COUNT: $REQUIRED_APPROVING_REVIEW_COUNT" >&2
  exit 1
fi

resolve_repo() {
  if [[ -n "$REPO" ]]; then
    return
  fi

  if [[ "$DRY_RUN" == "1" ]]; then
    REPO="REPO/NAME"
    return
  fi

  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
}

log() {
  echo "[github-bootstrap] $*"
}

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing dependency: $1" >&2
    exit 1
  fi
}

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    echo "[dry-run] $*"
  else
    eval "$1"
  fi
}

ensure_label() {
  local name=$1
  local color=$2
  local description=$3
  if [[ "${DRY_RUN}" == "1" ]]; then
    run "gh label create \"$name\" --repo \"$REPO\" --color \"$color\" --description \"$description\""
    return
  fi

  if gh label list --repo "$REPO" --search "$name" --limit 200 --json name --jq ".[].name" | grep -x "$name" >/dev/null; then
    log "Label already exists: $name"
    return
  fi

  log "Creating label: $name"
  run "gh label create \"$name\" --repo \"$REPO\" --color \"$color\" --description \"$description\""
}

ensure_milestone() {
  local title=$1
  local description=$2
  if [[ "${DRY_RUN}" == "1" ]]; then
    run "gh api -X POST repos/$REPO/milestones -f title=\"$title\" -f state=\"open\" -f description=\"$description\""
    return
  fi
  local existing
  existing="$(gh api "repos/$REPO/milestones" --paginate --jq ".[] | select(.title == \"$title\") | .number" | tr -d '\n' )"
  if [[ -n "$existing" ]]; then
    log "Milestone exists: $title (#$existing)"
    return
  fi
  log "Creating milestone: $title"
  run "gh api -X POST repos/$REPO/milestones -f title=\"$title\" -f state=\"open\" -f description=\"$description\""
}

ensure_branch_protection() {
  if [[ "$REQUIRE_BRANCH_PROTECTION" != "1" ]]; then
    log "Branch protection bootstrap skipped."
    return
  fi

  local branch=$1
  local payload
  payload=$(cat <<EOF
{
  "required_pull_request_reviews": {
    "required_approving_review_count": $REQUIRED_APPROVING_REVIEW_COUNT,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "require_last_push_approval": false
  },
  "required_status_checks": {
    "strict": true,
    "contexts": $REQUIRED_STATUS_CHECKS_JSON
  },
  "required_conversation_resolution": false,
  "enforce_admins": true,
  "required_linear_history": $REQUIRE_LINEAR_HISTORY,
  "allow_force_pushes": false,
  "required_signatures": false,
  "allow_deletions": false,
  "lock_branch": false,
  "restrictions": null
}
EOF
)

  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] gh api -X PUT repos/$REPO/branches/$branch/protection --input - <<< '$payload'"
    return
  fi

  log "Applying branch protection rule for: $branch"
  gh api -X PUT "repos/$REPO/branches/$branch/protection" \
    -H "Accept: application/vnd.github+json" \
    --input - <<< "$payload"
}

main() {
  need gh
  resolve_repo
  log "Bootstrapping GitHub metadata for $REPO"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "Dry run mode active; commands will not mutate the repository."
    log "No existence checks are performed while in DRY_RUN mode."
  else
    gh auth status >/dev/null 2>&1 || {
      echo "GitHub authentication missing or invalid. Run: gh auth login" >&2
      exit 1
    }
  fi

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
  ensure_branch_protection "$REQUIRED_BRANCH"

  log "Bootstrap complete."
  log "Optional: apply additional repository rules using docs/operations.md."
}

main "$@"
