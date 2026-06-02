package codex

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"strconv"
	"strings"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/redact"
)

const (
	policyMethodAccountRead    = "account/read"
	policyMethodRateLimitsRead = "account/rateLimits/read"
	percentLimit               = int64(100)
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

	if err := c.client.Call(ctx, policyMethodInitialize, map[string]any{
		"clientInfo": map[string]any{
			"name":    "llm_usage_exporter",
			"title":   "llm-usage-exporter",
			"version": "0.5.0-beta.1",
		},
	}, &struct{}{}); err != nil {
		snapshot.Status = model.ProviderStatusError
		return snapshot, fmt.Errorf("initialize: %w", err)
	}
	if err := c.client.Notify(ctx, policyMethodInitialized, map[string]any{}); err != nil {
		snapshot.Status = model.ProviderStatusError
		return snapshot, fmt.Errorf("initialized: %w", err)
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

	windows, credits, err := c.readRateLimits(ctx)
	if err != nil {
		snapshot.Status = model.ProviderStatusError
		return snapshot, err
	}
	snapshot.UsageWindows = windows
	snapshot.Credits = credits
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

	accountID := firstNonEmptyString(container, "accountId", "account_id", "chatgptAccountId", "chatgpt_account_id", "email", "type")
	planType := getString(container, "planType", "plan_type")
	if accountID == "" {
		return accountResult{}, fmt.Errorf("account/read schema missing account identifier")
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

func (c *collector) readRateLimits(ctx context.Context) ([]model.UsageWindow, *model.Credits, error) {
	raw := json.RawMessage{}
	if err := c.client.Call(ctx, policyMethodRateLimitsRead, map[string]any{}, &raw); err != nil {
		return nil, nil, fmt.Errorf("account/rateLimits/read: %w", err)
	}

	response := map[string]any{}
	if err := json.Unmarshal(raw, &response); err != nil {
		return nil, nil, fmt.Errorf("rateLimits parse: %w", err)
	}

	windows, err := normalizeRateLimitsResponse(response)
	if err != nil {
		return nil, nil, err
	}
	credits := firstCredits(response)
	return windows, credits, nil
}

func normalizeRateLimitsResponse(response map[string]any) ([]model.UsageWindow, error) {
	if byLimitID, ok := response["rateLimitsByLimitId"].(map[string]any); ok && len(byLimitID) > 0 {
		out := make([]model.UsageWindow, 0, len(byLimitID)*2)
		for key, entry := range byLimitID {
			record, ok := entry.(map[string]any)
			if !ok {
				return nil, fmt.Errorf("rateLimits schema mismatch: rateLimitsByLimitId[%s] invalid", key)
			}
			windows, err := normalizeBucket(record, key)
			if err != nil {
				return nil, err
			}
			out = append(out, windows...)
		}
		if len(out) == 0 {
			return nil, fmt.Errorf("rateLimits schema mismatch: no usable rate limit windows")
		}
		return out, nil
	}

	rawRateLimits, ok := response["rateLimits"]
	if !ok {
		return nil, fmt.Errorf("rateLimits schema mismatch: rateLimits missing")
	}
	switch entries := rawRateLimits.(type) {
	case []any:
		return normalizeLegacyRateLimitList(entries)
	case map[string]any:
		return normalizeBucket(entries, getString(entries, "limitId", "limit_id"))
	default:
		return nil, fmt.Errorf("rateLimits schema mismatch: rateLimits invalid")
	}
}

func normalizeLegacyRateLimitList(entries []any) ([]model.UsageWindow, error) {
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
		out = append(out, parsed.toWindow())
	}
	return out, nil
}

func normalizeBucket(bucket map[string]any, fallbackID string) ([]model.UsageWindow, error) {
	limitID := firstNonEmpty(getString(bucket, "limitId", "limit_id"), fallbackID)
	if limitID == "" {
		return nil, fmt.Errorf("rateLimits schema missing limitId")
	}
	limitName := getString(bucket, "limitName", "limit_name")

	out := make([]model.UsageWindow, 0, 2)
	primary, err := normalizePercentWindow(bucket, "primary", limitID, limitName)
	if err != nil {
		return nil, err
	}
	if primary != nil {
		out = append(out, *primary)
	}

	secondary, err := normalizePercentWindow(bucket, "secondary", limitID+".secondary", appendWindowName(limitName, "secondary"))
	if err != nil {
		return nil, err
	}
	if secondary != nil {
		out = append(out, *secondary)
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("rateLimits schema mismatch: bucket %s has no primary or secondary window", limitID)
	}
	return out, nil
}

func normalizePercentWindow(bucket map[string]any, key string, limitID string, limitName string) (*model.UsageWindow, error) {
	raw, ok := bucket[key]
	if !ok || raw == nil {
		return nil, nil
	}
	window, ok := raw.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("rateLimits schema mismatch: %s invalid", key)
	}
	usedPercent := getFloat(window, "usedPercent", "used_percent")
	if usedPercent < 0 {
		return nil, fmt.Errorf("rateLimits schema missing usedPercent")
	}
	windowMins, err := requiredInt(window, "windowDurationMins", "window_duration_mins")
	if err != nil {
		return nil, err
	}
	if windowMins <= 0 {
		return nil, fmt.Errorf("rateLimits schema invalid windowDurationMins: %d", windowMins)
	}
	resetsAt, err := parseResetTime(window["resetsAt"])
	if err != nil {
		return nil, err
	}
	return &model.UsageWindow{
		LimitID:            limitID,
		LimitName:          limitName,
		WindowDurationMins: windowMins,
		Used:               int64(math.Round(usedPercent)),
		Limit:              percentLimit,
		UsedPercent:        usedPercent,
		ResetsAt:           resetsAt,
	}, nil
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

	resetsAt, err := parseResetTime(data["resetsAt"])
	if err != nil {
		return rateLimitResult{}, err
	}
	window.resetsAt = resetsAt

	return window, nil
}

func (r rateLimitResult) toWindow() model.UsageWindow {
	return model.UsageWindow{
		LimitID:            r.limitID,
		LimitName:          r.limitName,
		WindowDurationMins: r.windowMins,
		Used:               r.used,
		Limit:              r.limit,
		UsedPercent:        r.usedPct,
		ResetsAt:           r.resetsAt,
	}
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

func firstNonEmptyString(data map[string]any, keys ...string) string {
	for _, key := range keys {
		if value := strings.TrimSpace(getString(data, key)); value != "" {
			return value
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

func parseResetTime(raw any) (*time.Time, error) {
	if raw == nil {
		return nil, nil
	}
	switch value := raw.(type) {
	case string:
		if strings.TrimSpace(value) == "" {
			return nil, nil
		}
		t, err := time.Parse(time.RFC3339, value)
		if err != nil {
			return nil, fmt.Errorf("rateLimits schema invalid resetsAt: %w", err)
		}
		return &t, nil
	case float64:
		if value <= 0 {
			return nil, nil
		}
		seconds := int64(value)
		if value != float64(seconds) {
			return nil, fmt.Errorf("rateLimits schema invalid resetsAt: %v", value)
		}
		t := time.Unix(seconds, 0).UTC()
		return &t, nil
	case int64:
		if value <= 0 {
			return nil, nil
		}
		t := time.Unix(value, 0).UTC()
		return &t, nil
	case int:
		if value <= 0 {
			return nil, nil
		}
		t := time.Unix(int64(value), 0).UTC()
		return &t, nil
	case json.Number:
		seconds, err := strconv.ParseInt(value.String(), 10, 64)
		if err != nil {
			return nil, fmt.Errorf("rateLimits schema invalid resetsAt: %w", err)
		}
		t := time.Unix(seconds, 0).UTC()
		return &t, nil
	default:
		return nil, fmt.Errorf("rateLimits schema invalid resetsAt")
	}
}

func firstCredits(data map[string]any) *model.Credits {
	if credits := parseCredits(data["credits"]); credits != nil {
		return credits
	}
	if bucket, ok := data["rateLimits"].(map[string]any); ok {
		return parseCredits(bucket["credits"])
	}
	return nil
}

func parseCredits(raw any) *model.Credits {
	data, ok := raw.(map[string]any)
	if !ok {
		return nil
	}
	remaining, err := optionalInt(data, "remaining")
	if err != nil {
		return nil
	}
	total, err := optionalInt(data, "total")
	if err != nil {
		return nil
	}
	if remaining == nil || total == nil {
		return nil
	}
	return &model.Credits{Remaining: *remaining, Total: *total}
}

func optionalInt(data map[string]any, keys ...string) (*int64, error) {
	for _, key := range keys {
		if _, ok := data[key]; ok {
			value, err := requiredInt(data, key)
			if err != nil {
				return nil, err
			}
			return &value, nil
		}
	}
	return nil, nil
}

func appendWindowName(limitName, suffix string) string {
	if strings.TrimSpace(limitName) == "" {
		return suffix
	}
	return strings.TrimSpace(limitName) + " " + suffix
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			return strings.TrimSpace(value)
		}
	}
	return ""
}
