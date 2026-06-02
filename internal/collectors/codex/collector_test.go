package codex

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
)

type fakeRPCClient struct {
	calls []rpcCall
	errs  map[string]error
	raw   map[string]json.RawMessage
}

type rpcCall struct {
	method string
	params any
}

func (f *fakeRPCClient) Call(_ context.Context, method string, params any, out any) error {
	f.calls = append(f.calls, rpcCall{method: method, params: params})
	if err := f.errs[method]; err != nil {
		return err
	}
	if out == nil {
		return nil
	}
	raw := f.raw[method]
	if rm, ok := out.(*json.RawMessage); ok {
		*rm = append((*rm)[0:0], raw...)
		return nil
	}
	if len(raw) == 0 {
		return nil
	}
	return json.Unmarshal(raw, out)
}

func (f *fakeRPCClient) Notify(_ context.Context, method string, params any) error {
	f.calls = append(f.calls, rpcCall{method: method, params: params})
	return nil
}

func (f *fakeRPCClient) Close() error { return nil }

func TestCollectUsesReadOnlyCodexCalls(t *testing.T) {
	t.Parallel()

	client := &fakeRPCClient{
		errs: map[string]error{},
		raw: map[string]json.RawMessage{
			policyMethodAccountRead:    json.RawMessage(`{"account":{"accountId":"acct-123","planType":"pro"}}`),
			policyMethodRateLimitsRead: json.RawMessage(`{"rateLimits":[{"limitId":"rpm","limitName":"requests","windowDurationMins":1,"used":2,"limit":10,"usedPercent":20}]}`),
		},
	}

	collector := NewCollector("codex-main", client)
	snapshot, err := collector.Collect(context.Background())
	if err != nil {
		t.Fatalf("Collect returned error: %v", err)
	}
	if snapshot.Status != model.ProviderStatusOK {
		t.Fatalf("expected ok snapshot, got %q", snapshot.Status)
	}
	if snapshot.Account == nil || snapshot.Account.ProviderAccountID == "acct-123" {
		t.Fatalf("expected hashed account id, got %#v", snapshot.Account)
	}
	if len(snapshot.UsageWindows) != 1 || snapshot.UsageWindows[0].LimitID != "rpm" {
		t.Fatalf("unexpected windows: %#v", snapshot.UsageWindows)
	}
	if len(client.calls) != 4 {
		t.Fatalf("expected initialize/account/rate limit calls, got %#v", client.calls)
	}
	if client.calls[0].method != policyMethodInitialize {
		t.Fatalf("unexpected first call: %#v", client.calls[0])
	}
	if client.calls[1].method != policyMethodInitialized {
		t.Fatalf("unexpected second call: %#v", client.calls[1])
	}
	if client.calls[2].method != policyMethodAccountRead {
		t.Fatalf("unexpected third call: %#v", client.calls[2])
	}
	params, ok := client.calls[2].params.(map[string]any)
	if !ok || params["refreshToken"] != false {
		t.Fatalf("account/read must pass refreshToken=false, got %#v", client.calls[2].params)
	}
}

func TestCollectNormalizesCurrentCodexRateLimitBuckets(t *testing.T) {
	t.Parallel()

	client := &fakeRPCClient{
		errs: map[string]error{},
		raw: map[string]json.RawMessage{
			policyMethodAccountRead: json.RawMessage(`{"account":{"email":"user@example.com","planType":"pro"}}`),
			policyMethodRateLimitsRead: json.RawMessage(`{
				"rateLimits": {
					"limitId": "codex",
					"limitName": null,
					"primary": {"usedPercent": 25, "windowDurationMins": 15, "resetsAt": 1730947200},
					"secondary": null
				},
				"rateLimitsByLimitId": {
					"codex": {
						"limitId": "codex",
						"limitName": "Codex",
						"primary": {"usedPercent": 25, "windowDurationMins": 15, "resetsAt": 1730947200},
						"secondary": {"usedPercent": 42, "windowDurationMins": 60, "resetsAt": 1730950800}
					}
				}
			}`),
		},
	}

	collector := NewCollector("codex-main", client)
	snapshot, err := collector.Collect(context.Background())
	if err != nil {
		t.Fatalf("Collect returned error: %v", err)
	}
	if snapshot.Account == nil || snapshot.Account.ProviderAccountID == "" {
		t.Fatalf("expected hashed account info: %#v", snapshot.Account)
	}
	if len(snapshot.UsageWindows) != 2 {
		t.Fatalf("expected two usage windows, got %#v", snapshot.UsageWindows)
	}
	if snapshot.UsageWindows[0].LimitID != "codex" || snapshot.UsageWindows[0].Used != 25 || snapshot.UsageWindows[0].Limit != 100 {
		t.Fatalf("unexpected primary window: %#v", snapshot.UsageWindows[0])
	}
	if snapshot.UsageWindows[1].LimitID != "codex.secondary" || snapshot.UsageWindows[1].UsedPercent != 42 {
		t.Fatalf("unexpected secondary window: %#v", snapshot.UsageWindows[1])
	}
	if snapshot.UsageWindows[0].ResetsAt == nil {
		t.Fatal("expected reset time from unix timestamp")
	}
}

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
		"limitId":            "x",
		"windowDurationMins": 1.0,
		"used":               1.0,
		"limit":              4.0,
		"usedPercent":        -1,
	}
	parsed, err := normalizeRateLimit(record)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if parsed.usedPct != 25.0 {
		t.Fatalf("expected fallback percent 25.0, got %f", parsed.usedPct)
	}
}

func TestGetFloatHelper(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"f": 1.25,
	}
	if getFloat(record, "f") != 1.25 {
		t.Fatalf("getFloat failed")
	}
}

func TestNormalizeRateLimitRejectsBadResetTime(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"limitId":            "bad",
		"windowDurationMins": 1.0,
		"used":               1.0,
		"limit":              2.0,
		"resetsAt":           "not-a-time",
		"usedPercent":        50.0,
	}
	if _, err := normalizeRateLimit(record); err == nil {
		t.Fatal("expected invalid reset time error")
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
		"limitId":            "id",
		"windowDurationMins": 1.0,
		"used":               0.0,
		"limit":              10.0,
		"resetsAt":           "2026-06-01T00:00:00Z",
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

func TestNormalizeRateLimitRejectsMissingRequiredCounters(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"limitId":            "id",
		"windowDurationMins": 1.0,
		"limit":              10.0,
	}
	if _, err := normalizeRateLimit(record); err == nil {
		t.Fatal("expected missing used error")
	}
}

func TestNormalizeRateLimitRejectsNonIntegerCounter(t *testing.T) {
	t.Parallel()

	record := map[string]any{
		"limitId":            "id",
		"windowDurationMins": 1.5,
		"used":               1.0,
		"limit":              10.0,
	}
	if _, err := normalizeRateLimit(record); err == nil {
		t.Fatal("expected non-integer window error")
	}
}
