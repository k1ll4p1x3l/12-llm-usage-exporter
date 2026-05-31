package redact

import (
	"crypto/sha256"
	"encoding/hex"
	"regexp"
	"strings"
)

var (
	authorizationPattern  = regexp.MustCompile(`(?i)(["']?authorization["']?\s*[:=]\s*)(["']?)[^"',;]+(["']?)`)
	sensitiveValuePattern = regexp.MustCompile(`(?i)(["']?(?:token|secret|password|api[_-]?key|refresh[_-]?token)["']?\s*[:=]\s*)(["']?)[^"'\s,;]+(["']?)`)
)

func HashAccountID(accountID string) string {
	id := strings.TrimSpace(accountID)
	if id == "" {
		return ""
	}

	sum := sha256.Sum256([]byte(id))
	return "sha256:" + hex.EncodeToString(sum[:])
}

func Message(message string) string {
	trimmed := strings.TrimSpace(message)
	if trimmed == "" {
		return ""
	}

	redacted := authorizationPattern.ReplaceAllString(trimmed, "$1$2[REDACTED]$3")
	redacted = sensitiveValuePattern.ReplaceAllString(redacted, "$1$2[REDACTED]$3")
	redacted = strings.ReplaceAll(redacted, ".codex/auth.json", ".codex/[REDACTED]")
	return redacted
}
