#!/usr/bin/env bash

set -euo pipefail

DRY_RUN="${DRY_RUN:-0}"
REPO="${GITHUB_REPO:-}"
BRANCH="${PROTECTION_BRANCH:-main}"
REQUIRED_STATUS_CHECKS_JSON="${REQUIRED_STATUS_CHECKS_JSON:-[\"ci\",\"analyze\",\"vulncheck\",\"check-milestone\",\"ensure-changelog\"]}"
REQUIRE_LINEAR_HISTORY="${REQUIRE_LINEAR_HISTORY:-false}"

log() {
  echo "[github-settings] $*"
}

run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

resolve_repo() {
  if [[ -n "$REPO" ]]; then
    return
  fi
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
}

put_topics() {
  log "Applying repository topics."
  run gh api -X PUT "repos/$REPO/topics" \
    -H "Accept: application/vnd.github+json" \
    -f names[]=go \
    -f names[]=prometheus \
    -f names[]=telemetry \
    -f names[]=llm-tools \
    -f names[]=codex
}

update_repo_options() {
  log "Applying repository options."
  run gh api -X PATCH "repos/$REPO" \
    -H "Accept: application/vnd.github+json" \
    -F has_wiki=false \
    -F has_discussions=true \
    -F delete_branch_on_merge=true \
    -F allow_squash_merge=true \
    -F allow_merge_commit=true \
    -F allow_rebase_merge=true
}

enable_security_features() {
  log "Enabling Dependabot alerts."
  run gh api -X PUT "repos/$REPO/vulnerability-alerts" \
    -H "Accept: application/vnd.github+json"

  log "Enabling Dependabot security updates."
  run gh api -X PUT "repos/$REPO/automated-security-fixes" \
    -H "Accept: application/vnd.github+json"

  log "Requesting secret scanning and push protection where supported."
  run gh api -X PATCH "repos/$REPO" \
    -H "Accept: application/vnd.github+json" \
    -f security_and_analysis[secret_scanning][status]=enabled \
    -f security_and_analysis[secret_scanning_push_protection][status]=enabled
}

apply_branch_protection() {
  local payload
  payload=$(mktemp)
  cat >"$payload" <<EOF
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
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

  log "Applying branch protection for $BRANCH."
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "[dry-run] gh api -X PUT repos/$REPO/branches/$BRANCH/protection --input $payload"
    cat "$payload"
  else
    gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" \
      -H "Accept: application/vnd.github+json" \
      --input "$payload"
  fi
  rm -f "$payload"
}

main() {
  command -v gh >/dev/null 2>&1 || {
    echo "Missing dependency: gh" >&2
    exit 1
  }
  resolve_repo
  log "Bootstrapping repository settings for $REPO."
  gh auth status >/dev/null 2>&1 || {
    echo "GitHub authentication missing or invalid. Run: gh auth login" >&2
    exit 1
  }

  update_repo_options
  put_topics
  enable_security_features
  apply_branch_protection
  log "Settings bootstrap complete."
}

main "$@"
