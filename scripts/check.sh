#!/usr/bin/env bash

set -euo pipefail

export GOCACHE="${GOCACHE:-$HOME/.cache/llm-usage-exporter/go-build}"
export GOMODCACHE="${GOMODCACHE:-$HOME/.cache/llm-usage-exporter/go-mod-cache}"

mkdir -p "$GOCACHE" "$GOMODCACHE"

echo "[check] gofmt"
if [[ -n "$(find . \
  -path './.codex' -prune -o \
  -path './.git' -prune -o \
  -path './dist' -prune -o \
  -path './vendor' -prune -o \
  -name '*.go' -type f -print0 | xargs -0 gofmt -l)" ]]; then
  echo "Go files are not formatted." >&2
  exit 1
fi

echo "[check] go test"
go test ./...

echo "[check] go vet"
go vet ./...

echo "[check] govulncheck"
govulncheck ./...

echo "[check] actionlint"
actionlint

echo "[check] gitleaks"
gitleaks detect --source . --no-banner --redact --exit-code 1

echo "[check] codex agent pack"
python3 scripts/verify_codex_agent_pack.py
python3 scripts/public_repo_sanity_check.py

echo "[check] goreleaser"
goreleaser healthcheck
goreleaser check

echo "[check] ok"
