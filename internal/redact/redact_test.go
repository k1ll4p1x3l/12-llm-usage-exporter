package redact

import "testing"

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
