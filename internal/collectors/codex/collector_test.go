package codex

import (
	"testing"
	"time"
)

func TestNormalizeRateLimit(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"limitId":            "rpm",
		"limitName":          "requests/minute",
		"windowDurationMins": 1.0,
		"used":               42.0,
		"limit":              100.0,
		"usedPercent":        42.0,
		"resetsAt":           "2026-06-01T12:00:00Z",
	}
	parsed, err := normalizeRateLimit(record)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if parsed.limitID != "rpm" {
		t.Fatalf("expected limitID rpm, got %q", parsed.limitID)
	}
	if parsed.used != 42 || parsed.limit != 100 {
		t.Fatalf("unexpected quota: used=%d limit=%d", parsed.used, parsed.limit)
	}
	if parsed.windowMins != 1 {
		t.Fatalf("unexpected windowMins: %d", parsed.windowMins)
	}
	if parsed.resetsAt == nil || parsed.resetsAt.IsZero() {
		t.Fatalf("expected resetsAt to be set")
	}
}

func TestNormalizeRateLimitMissingLimitID(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"limitName": "requests/minute",
		"used":      1.0,
		"limit":     2.0,
	}
	if _, err := normalizeRateLimit(record); err == nil {
		t.Fatal("expected error for missing limitId")
	}
}

func TestNormalizePercentFallback(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"limitId":     "x",
		"used":        1.0,
		"limit":       4.0,
		"usedPercent": -1,
	}
	parsed, err := normalizeRateLimit(record)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if parsed.usedPct != 25.0 {
		t.Fatalf("expected fallback percent 25.0, got %f", parsed.usedPct)
	}
}

func TestGetFloatAndIntHelpers(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"i": 3,
		"f": 1.25,
	}
	if getInt(record, "i") != 3 {
		t.Fatalf("getInt failed")
	}
	if getFloat(record, "f") != 1.25 {
		t.Fatalf("getFloat failed")
	}
}

func TestNormalizeRateLimitIgnoresBadResetTime(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"limitId":     "bad",
		"used":        1.0,
		"limit":       2.0,
		"resetsAt":    "not-a-time",
		"usedPercent": 50.0,
	}
	parsed, err := normalizeRateLimit(record)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if parsed.resetsAt != nil {
		t.Fatalf("expected invalid reset time to be ignored")
	}
}

func TestGetStringWithAlternativeKey(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"limit_id": "alt-id",
	}
	if got := getString(record, "limitId", "limit_id"); got != "alt-id" {
		t.Fatalf("expected alt key value, got %q", got)
	}
}

func TestRateLimitResetsAtParse(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"limitId":  "id",
		"used":     0.0,
		"limit":    10.0,
		"resetsAt": "2026-06-01T00:00:00Z",
	}
	parsed, err := normalizeRateLimit(record)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if parsed.resetsAt == nil {
		t.Fatal("expected reset time")
	}
	if parsed.resetsAt.Sub(time.Date(2026, 6, 1, 0, 0, 0, 0, time.UTC)) != 0 {
		t.Fatalf("unexpected reset time: %v", parsed.resetsAt)
	}
}
