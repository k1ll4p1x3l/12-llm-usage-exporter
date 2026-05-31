package service

import (
	"context"
	"errors"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/collectors"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/config"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
)

type fakeCollector struct {
	id       string
	snapshot model.ProviderSnapshot
	err      error
}

func (f fakeCollector) ID() string             { return f.id }
func (f fakeCollector) Capabilities() []string { return []string{"test"} }
func (f fakeCollector) Collect(context.Context) (model.ProviderSnapshot, error) {
	return f.snapshot, f.err
}

type sequenceCollector struct {
	id        string
	snapshots []model.ProviderSnapshot
	errs      []error
	index     int
}

func (s *sequenceCollector) ID() string             { return s.id }
func (s *sequenceCollector) Capabilities() []string { return []string{"test"} }
func (s *sequenceCollector) Collect(context.Context) (model.ProviderSnapshot, error) {
	i := s.index
	if i >= len(s.errs) {
		i = len(s.errs) - 1
	}
	s.index++
	if err := s.errs[i]; err != nil {
		return model.ProviderSnapshot{}, err
	}
	return s.snapshots[i], nil
}

func baseConfig() config.Config {
	return config.Config{
		PollInterval: 30 * time.Second,
		JSONOutput: config.JSONOutputConfig{
			Enabled: false,
		},
		Prometheus: config.PrometheusConfig{
			Enabled: false,
		},
	}
}

func TestSchedulerTickAllHealthy(t *testing.T) {
	t.Parallel()

	cfg := baseConfig()
	collectorList := []collectors.Collector{
		fakeCollector{
			id: "codex-main",
			snapshot: model.ProviderSnapshot{
				ID:     "codex-main",
				Status: model.ProviderStatusOK,
			},
		},
	}

	runner := NewRunner(cfg, collectorList)
	snapshot, err := runner.RunOnce(context.Background())
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if snapshot.Health.Status != model.HealthStatusHealthy {
		t.Fatalf("expected healthy snapshot, got %q", snapshot.Health.Status)
	}
	if len(snapshot.Providers) != 1 || snapshot.Providers[0].Status != model.ProviderStatusOK {
		t.Fatalf("unexpected providers: %#v", snapshot.Providers)
	}
	if snapshot.Health.LastSuccessfulAt == nil {
		t.Fatal("expected last_successful_at set")
	}
}

func TestSchedulerTickDegradedAndUnavailable(t *testing.T) {
	t.Parallel()

	cfg := baseConfig()
	collectorList := []collectors.Collector{
		fakeCollector{
			id: "ok",
			snapshot: model.ProviderSnapshot{
				ID:     "ok",
				Status: model.ProviderStatusOK,
			},
		},
		fakeCollector{
			id:  "fail",
			err: errors.New("collection failed"),
		},
	}

	runner := NewRunner(cfg, collectorList)
	snapshot, err := runner.RunOnce(context.Background())
	if err != nil {
		t.Fatalf("unexpected runner error: %v", err)
	}
	if snapshot.Health.Status != model.HealthStatusDegraded {
		t.Fatalf("expected degraded status, got %q", snapshot.Health.Status)
	}
	if len(snapshot.Providers) != 2 {
		t.Fatalf("expected 2 provider snapshots, got %d", len(snapshot.Providers))
	}
	if got := snapshot.Providers[1].Status; got != model.ProviderStatusError {
		t.Fatalf("expected provider error status, got %q", got)
	}
	if snapshot.Providers[1].ProviderType == "" {
		t.Fatal("expected provider_type on error snapshot")
	}
	if snapshot.Providers[1].UsageWindows == nil {
		t.Fatal("expected empty usage_windows array on error snapshot")
	}
	if snapshot.Health.Message == "" {
		t.Fatal("expected health message with provider error")
	}

	collectorsAllDown := []collectors.Collector{
		fakeCollector{id: "a", err: fmt.Errorf("a down")},
		fakeCollector{id: "b", err: fmt.Errorf("b down")},
	}
	runner = NewRunner(cfg, collectorsAllDown)
	_, err = runner.RunOnce(context.Background())
	if err == nil || err.Error() != "all providers failed" {
		t.Fatalf("expected all providers failed error, got %v", err)
	}
}

func TestSchedulerKeepsLastSuccessfulAtAfterFailure(t *testing.T) {
	t.Parallel()

	cfg := baseConfig()
	collector := &sequenceCollector{
		id: "codex",
		snapshots: []model.ProviderSnapshot{
			{ID: "codex", Status: model.ProviderStatusOK},
			{},
		},
		errs: []error{nil, errors.New("provider down")},
	}

	runner := NewRunner(cfg, []collectors.Collector{collector})
	first, err := runner.RunOnce(context.Background())
	if err != nil {
		t.Fatalf("unexpected first tick error: %v", err)
	}
	if first.Health.LastSuccessfulAt == nil {
		t.Fatal("expected first tick last_successful_at")
	}

	second, err := runner.RunOnce(context.Background())
	if err == nil {
		t.Fatal("expected all providers failed error")
	}
	if second.Health.LastSuccessfulAt == nil {
		t.Fatal("expected last_successful_at to survive failure")
	}
	if !second.Health.LastSuccessfulAt.Equal(*first.Health.LastSuccessfulAt) {
		t.Fatalf("unexpected last_successful_at: %v != %v", second.Health.LastSuccessfulAt, first.Health.LastSuccessfulAt)
	}
}

func TestSchedulerRedactsProviderErrors(t *testing.T) {
	t.Parallel()

	cfg := baseConfig()
	collectorList := []collectors.Collector{
		fakeCollector{id: "fail", err: errors.New("token=abc123 password: hunter2 .codex/auth.json")},
	}

	runner := NewRunner(cfg, collectorList)
	snapshot, err := runner.RunOnce(context.Background())
	if err == nil {
		t.Fatal("expected all providers failed error")
	}
	for _, forbidden := range []string{"abc123", "hunter2", ".codex/auth.json"} {
		if strings.Contains(snapshot.Health.Message, forbidden) {
			t.Fatalf("health message still contains %q: %q", forbidden, snapshot.Health.Message)
		}
		if strings.Contains(snapshot.Providers[0].Error, forbidden) {
			t.Fatalf("provider error still contains %q: %q", forbidden, snapshot.Providers[0].Error)
		}
	}
}
