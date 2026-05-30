package service

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/collectors"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/config"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/exporters/jsonfile"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/exporters/prometheus"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
)

type Runner struct {
	cfg        config.Config
	collectors []collectors.Collector
	prometheus *prometheus.Exporter
}

func NewRunner(cfg config.Config, collectors []collectors.Collector) *Runner {
	return &Runner{
		cfg:        cfg,
		collectors: collectors,
		prometheus: prometheus.New(cfg.Prometheus.Enabled),
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
	var lastSuccess time.Time

	for _, c := range r.collectors {
		providerSnapshot, err := c.Collect(ctx)
		if err != nil {
			failures = append(failures, fmt.Errorf("%s: %w", c.ID(), err))
			snapshot.Providers = append(snapshot.Providers, model.ProviderSnapshot{
				ID:          c.ID(),
				Source:      "error",
				Status:      model.ProviderStatusError,
				Error:       err.Error(),
				CollectedAt: generatedAt,
			})
		} else {
			lastSuccess = generatedAt
			snapshot.Providers = append(snapshot.Providers, providerSnapshot)
		}
	}

	switch {
	case len(failures) == 0:
		snapshot.Health.Status = model.HealthStatusHealthy
	case len(failures) == len(r.collectors):
		snapshot.Health.Status = model.HealthStatusUnavailable
		snapshot.Health.Message = joinErrors(failures)
	default:
		snapshot.Health.Status = model.HealthStatusDegraded
		snapshot.Health.Message = joinErrors(failures)
	}

	if !lastSuccess.IsZero() {
		snapshot.Health.LastSuccessfulAt = &lastSuccess
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
