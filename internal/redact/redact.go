package redact

import (
	"crypto/sha256"
	"encoding/hex"
	"strings"
)

func HashAccountID(accountID string) string {
	id := strings.TrimSpace(accountID)
	if id == "" {
		return ""
	}

	sum := sha256.Sum256([]byte(id))
	return "sha256:" + hex.EncodeToString(sum[:])
}
