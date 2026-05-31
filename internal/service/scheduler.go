package service

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/collectors"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/config"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/exporters/jsonfile"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/exporters/prometheus"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/redact"
)

type Runner struct {
	cfg              config.Config
	collectors       []collectors.Collector
	prometheus       *prometheus.Exporter
	providerTypes    map[string]string
	mu               sync.Mutex
	lastSuccessfulAt *time.Time
}

func NewRunner(cfg config.Config, collectors []collectors.Collector) *Runner {
	return &Runner{
		cfg:           cfg,
		collectors:    collectors,
		prometheus:    prometheus.New(cfg.Prometheus.Enabled),
		providerTypes: providerTypesByID(cfg),
	}
}

func (r *Runner) PrometheusHandler() *prometheus.Exporter {
	return r.prometheus
}

func (r *Runner) RunOnce(ctx context.Context) (model.Snapshot, error) {
	return r.tick(ctx)
}

func (r *Runner) Run(ctx context.Context) error {
	ticker := time.NewTicker(r.cfg.PollInterval)
	defer ticker.Stop()

	if _, err := r.tick(ctx); err != nil {
		// continue serving and keep emitting degraded health snapshots
	}

	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			_, _ = r.tick(ctx)
		}
	}
}

func (r *Runner) tick(ctx context.Context) (model.Snapshot, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	generatedAt := time.Now().UTC()
	snapshot := model.Snapshot{
		SchemaVersion: model.SchemaVersion,
		Agent:         "llm-usage-exporter",
		GeneratedAt:   generatedAt,
		Source:        "local-collectors",
		Health:        model.Health{Status: model.HealthStatusHealthy, CollectedAt: generatedAt},
		Providers:     make([]model.ProviderSnapshot, 0, len(r.collectors)),
	}

	var failures []error
	var lastSuccess *time.Time

	for _, c := range r.collectors {
		providerSnapshot, err := c.Collect(ctx)
		if err != nil {
			failures = append(failures, fmt.Errorf("%s: %w", c.ID(), err))
			snapshot.Providers = append(snapshot.Providers, model.ProviderSnapshot{
				ID:           c.ID(),
				Source:       "error",
				ProviderType: r.providerType(c.ID()),
				Status:       model.ProviderStatusError,
				Error:        redact.Message(err.Error()),
				CollectedAt:  generatedAt,
				UsageWindows: []model.UsageWindow{},
			})
		} else {
			successAt := generatedAt
			lastSuccess = &successAt
			snapshot.Providers = append(snapshot.Providers, r.normalizeProviderSnapshot(c.ID(), providerSnapshot, generatedAt))
		}
	}

	switch {
	case len(failures) == 0:
		snapshot.Health.Status = model.HealthStatusHealthy
	case len(failures) == len(r.collectors):
		snapshot.Health.Status = model.HealthStatusUnavailable
		snapshot.Health.Message = redact.Message(joinErrors(failures))
	default:
		snapshot.Health.Status = model.HealthStatusDegraded
		snapshot.Health.Message = redact.Message(joinErrors(failures))
	}

	if lastSuccess != nil {
		r.lastSuccessfulAt = lastSuccess
	}
	if r.lastSuccessfulAt != nil {
		snapshot.Health.LastSuccessfulAt = r.lastSuccessfulAt
	}

	if r.cfg.JSONOutput.Enabled {
		if err := jsonfile.WriteSnapshot(r.cfg.JSONOutput.Path, snapshot, r.cfg.JSONOutput.Pretty); err != nil {
			return snapshot, fmt.Errorf("write json snapshot: %w", err)
		}
	}

	if r.cfg.Prometheus.Enabled {
		r.prometheus.Apply(snapshot)
	}

	if len(failures) == len(r.collectors) {
		return snapshot, fmt.Errorf("all providers failed")
	}
	return snapshot, nil
}

func joinErrors(errs []error) string {
	msg := make([]string, 0, len(errs))
	for _, err := range errs {
		msg = append(msg, err.Error())
	}
	return strings.Join(msg, "; ")
}

func providerTypesByID(cfg config.Config) map[string]string {
	out := make(map[string]string, len(cfg.Providers))
	for _, provider := range cfg.Providers {
		out[provider.Name] = provider.Type
	}
	return out
}

func (r *Runner) providerType(id string) string {
	if providerType := strings.TrimSpace(r.providerTypes[id]); providerType != "" {
		return providerType
	}
	return "unknown"
}

func (r *Runner) normalizeProviderSnapshot(id string, snapshot model.ProviderSnapshot, collectedAt time.Time) model.ProviderSnapshot {
	if snapshot.ID == "" {
		snapshot.ID = id
	}
	if snapshot.Source == "" {
		snapshot.Source = "collector"
	}
	if snapshot.ProviderType == "" {
		snapshot.ProviderType = r.providerType(id)
	}
	if snapshot.CollectedAt.IsZero() {
		snapshot.CollectedAt = collectedAt
	}
	if snapshot.UsageWindows == nil {
		snapshot.UsageWindows = []model.UsageWindow{}
	}
	return snapshot
}
