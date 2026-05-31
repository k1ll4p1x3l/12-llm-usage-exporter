package codex

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/redact"
)

const (
	policyMethodAccountRead    = "account/read"
	policyMethodRateLimitsRead = "account/rateLimits/read"
)

type collector struct {
	id     string
	client RPCClient
}

func NewCollector(id string, client RPCClient) *collector {
	return &collector{
		id:     id,
		client: client,
	}
}

func (c *collector) ID() string {
	return c.id
}

func (c *collector) Capabilities() []string {
	return []string{
		policyMethodAccountRead,
		policyMethodRateLimitsRead,
	}
}

func (c *collector) Collect(ctx context.Context) (model.ProviderSnapshot, error) {
	now := time.Now().UTC()
	snapshot := model.ProviderSnapshot{
		ID:           c.id,
		Source:       "codex_appserver",
		ProviderType: "codex",
		CollectedAt:  now,
		Status:       model.ProviderStatusOK,
	}

	if err := c.client.Call(ctx, "initialize", map[string]any{
		"client": map[string]any{
			"name":    "llm-usage-exporter",
			"version": "0.1.0",
		},
	}, &struct{}{}); err != nil {
		snapshot.Status = model.ProviderStatusError
		return snapshot, fmt.Errorf("initialize: %w", err)
	}

	account, err := c.readAccount(ctx)
	if err != nil {
		snapshot.Status = model.ProviderStatusError
		return snapshot, err
	}
	snapshot.Account = &model.AccountInfo{
		ProviderAccountID: redact.HashAccountID(account.accountID),
		PlanType:          account.planType,
	}

	windows, err := c.readRateLimits(ctx)
	if err != nil {
		snapshot.Status = model.ProviderStatusError
		return snapshot, err
	}
	snapshot.UsageWindows = windows
	return snapshot, nil
}

type accountResult struct {
	accountID string
	planType  string
}

func (c *collector) readAccount(ctx context.Context) (accountResult, error) {
	raw := json.RawMessage{}
	if err := c.client.Call(ctx, policyMethodAccountRead, map[string]any{"refreshToken": false}, &raw); err != nil {
		return accountResult{}, fmt.Errorf("account/read: %w", err)
	}
	payload := map[string]any{}
	if err := json.Unmarshal(raw, &payload); err != nil {
		return accountResult{}, fmt.Errorf("account/read parse: %w", err)
	}

	container := payload
	if nested, ok := payload["account"].(map[string]any); ok {
		container = nested
	}

	accountID := getString(container, "accountId", "account_id")
	planType := getString(container, "planType", "plan_type")
	if accountID == "" {
		return accountResult{}, fmt.Errorf("account/read schema missing accountId")
	}
	if refresh, ok := container["refreshToken"].(bool); ok && refresh {
		return accountResult{}, fmt.Errorf("policy violation: account/read refreshToken=true is forbidden")
	}

	return accountResult{
		accountID: strings.TrimSpace(accountID),
		planType:  strings.TrimSpace(planType),
	}, nil
}

type rateLimitResult struct {
	limitID    string
	limitName  string
	used       int64
	limit      int64
	usedPct    float64
	windowMins int64
	resetsAt   *time.Time
}

func (c *collector) readRateLimits(ctx context.Context) ([]model.UsageWindow, error) {
	raw := json.RawMessage{}
	if err := c.client.Call(ctx, policyMethodRateLimitsRead, map[string]any{}, &raw); err != nil {
		return nil, fmt.Errorf("account/rateLimits/read: %w", err)
	}

	response := map[string]any{}
	if err := json.Unmarshal(raw, &response); err != nil {
		return nil, fmt.Errorf("rateLimits parse: %w", err)
	}

	entries, ok := response["rateLimits"].([]any)
	if !ok {
		return nil, fmt.Errorf("rateLimits schema mismatch: rateLimits missing")
	}
	out := make([]model.UsageWindow, 0, len(entries))
	for _, entry := range entries {
		record, ok := entry.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("rateLimits schema mismatch: entry invalid")
		}
		parsed, err := normalizeRateLimit(record)
		if err != nil {
			return nil, err
		}
		out = append(out, model.UsageWindow{
			LimitID:            parsed.limitID,
			LimitName:          parsed.limitName,
			WindowDurationMins: parsed.windowMins,
			Used:               parsed.used,
			Limit:              parsed.limit,
			UsedPercent:        parsed.usedPct,
			ResetsAt:           parsed.resetsAt,
		})
	}
	return out, nil
}

func normalizeRateLimit(data map[string]any) (rateLimitResult, error) {
	limitID := getString(data, "limitId", "limit_id")
	if limitID == "" {
		return rateLimitResult{}, fmt.Errorf("rateLimits schema missing limitId")
	}
	windowMins, err := requiredInt(data, "windowDurationMins", "window_duration_mins")
	if err != nil {
		return rateLimitResult{}, err
	}
	used, err := requiredInt(data, "used", "used_count")
	if err != nil {
		return rateLimitResult{}, err
	}
	limit, err := requiredInt(data, "limit", "max")
	if err != nil {
		return rateLimitResult{}, err
	}
	if windowMins <= 0 {
		return rateLimitResult{}, fmt.Errorf("rateLimits schema invalid windowDurationMins: %d", windowMins)
	}
	if used < 0 {
		return rateLimitResult{}, fmt.Errorf("rateLimits schema invalid used: %d", used)
	}
	if limit < 0 {
		return rateLimitResult{}, fmt.Errorf("rateLimits schema invalid limit: %d", limit)
	}

	window := rateLimitResult{
		limitID:    limitID,
		limitName:  getString(data, "limitName", "limit_name"),
		windowMins: windowMins,
		used:       used,
		limit:      limit,
	}

	usedPercent := getFloat(data, "usedPercent", "used_percent")
	if usedPercent < 0 && window.used >= 0 && window.limit > 0 {
		usedPercent = (float64(window.used) / float64(window.limit)) * 100
	}
	window.usedPct = usedPercent

	if rawReset, ok := data["resetsAt"].(string); ok && rawReset != "" {
		t, err := time.Parse(time.RFC3339, rawReset)
		if err != nil {
			return rateLimitResult{}, fmt.Errorf("rateLimits schema invalid resetsAt: %w", err)
		}
		window.resetsAt = &t
	}

	return window, nil
}

func getString(data map[string]any, keys ...string) string {
	for _, key := range keys {
		if raw, ok := data[key]; ok {
			if value, ok := raw.(string); ok {
				return value
			}
		}
	}
	return ""
}

func getFloat(data map[string]any, keys ...string) float64 {
	for _, key := range keys {
		raw, ok := data[key]
		if !ok {
			continue
		}
		switch value := raw.(type) {
		case float64:
			return value
		case int:
			return float64(value)
		case int64:
			return float64(value)
		case int32:
			return float64(value)
		}
	}
	return -1
}

func requiredInt(data map[string]any, keys ...string) (int64, error) {
	for _, key := range keys {
		raw, ok := data[key]
		if !ok {
			continue
		}
		switch value := raw.(type) {
		case float64:
			converted := int64(value)
			if value != float64(converted) {
				return 0, fmt.Errorf("rateLimits schema invalid integer %s: %v", key, value)
			}
			return converted, nil
		case int:
			return int64(value), nil
		case int64:
			return value, nil
		case int32:
			return int64(value), nil
		default:
			return 0, fmt.Errorf("rateLimits schema invalid integer %s", key)
		}
	}
	return 0, fmt.Errorf("rateLimits schema missing %s", keys[0])
}
