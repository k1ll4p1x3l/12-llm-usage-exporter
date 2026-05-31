package redact

import (
	"strings"
	"testing"
)

func TestHashAccountIDStable(t *testing.T) {
	t.Parallel()

	first := HashAccountID("abc123")
	second := HashAccountID("abc123")
	if first == "" || second == "" {
		t.Fatal("hash output is empty")
	}
	if first != second {
		t.Fatalf("hashes are not stable: %q != %q", first, second)
	}
}

func TestHashAccountIDEmpty(t *testing.T) {
	t.Parallel()
	if got := HashAccountID("   "); got != "" {
		t.Fatalf("expected empty output, got %q", got)
	}
}

func TestMessageRedactsSensitiveValues(t *testing.T) {
	t.Parallel()

	got := Message(`rpc failed token=abc123 password: hunter2 "api_key":"json-secret" Authorization: Bearer bearer-secret .codex/auth.json`)
	for _, forbidden := range []string{"abc123", "hunter2", "json-secret", "bearer-secret", ".codex/auth.json"} {
		if strings.Contains(got, forbidden) {
			t.Fatalf("message still contains %q: %q", forbidden, got)
		}
	}
	if !strings.Contains(got, "[REDACTED]") {
		t.Fatalf("expected redaction marker, got %q", got)
	}
}
