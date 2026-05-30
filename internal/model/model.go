package model

import "time"

// SchemaVersion reports the currently used snapshot schema.
const SchemaVersion = "usage.snapshot.v1alpha1"

const (
	ProviderStatusOK        = "ok"
	ProviderStatusError     = "error"
	HealthStatusHealthy     = "healthy"
	HealthStatusDegraded    = "degraded"
	HealthStatusUnavailable = "unavailable"
)

type Snapshot struct {
	SchemaVersion string             `json:"schema_version"`
	Agent         string             `json:"agent"`
	GeneratedAt   time.Time          `json:"generated_at"`
	Source        string             `json:"source"`
	Health        Health             `json:"health"`
	Providers     []ProviderSnapshot `json:"providers"`
}

type Health struct {
	Status           string     `json:"status"`
	Message          string     `json:"message,omitempty"`
	LastSuccessfulAt *time.Time `json:"last_successful_at,omitempty"`
	CollectedAt      time.Time  `json:"collected_at"`
}

type ProviderSnapshot struct {
	ID           string        `json:"id"`
	Source       string        `json:"source"`
	ProviderType string        `json:"provider_type"`
	Status       string        `json:"status"`
	Error        string        `json:"error,omitempty"`
	CollectedAt  time.Time     `json:"collected_at"`
	Account      *AccountInfo  `json:"account,omitempty"`
	UsageWindows []UsageWindow `json:"usage_windows"`
	Credits      *Credits      `json:"credits,omitempty"`
}

type AccountInfo struct {
	ProviderAccountID string `json:"provider_account_id"`
	PlanType          string `json:"plan_type,omitempty"`
}

type UsageWindow struct {
	LimitID            string     `json:"limit_id"`
	LimitName          string     `json:"limit_name"`
	WindowDurationMins int64      `json:"window_duration_mins"`
	Used               int64      `json:"used"`
	Limit              int64      `json:"limit"`
	UsedPercent        float64    `json:"used_percent"`
	ResetsAt           *time.Time `json:"resets_at,omitempty"`
}

type Credits struct {
	Remaining int64 `json:"remaining"`
	Total     int64 `json:"total"`
}
