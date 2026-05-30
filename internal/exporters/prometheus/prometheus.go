package prometheus

import (
	"net/http"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type Exporter struct {
	Enabled  bool
	registry *prometheus.Registry
	used     *prometheus.GaugeVec
	limit    *prometheus.GaugeVec
	ratio    *prometheus.GaugeVec
	resetAt  *prometheus.GaugeVec
	health   *prometheus.GaugeVec
}

func New(enabled bool) *Exporter {
	e := &Exporter{
		Enabled:  enabled,
		registry: prometheus.NewRegistry(),
		used: prometheus.NewGaugeVec(prometheus.GaugeOpts{
			Name: "llm_usage_window_used",
			Help: "Current used units for provider usage windows.",
		}, []string{"provider", "limit_id", "limit_name"}),
		limit: prometheus.NewGaugeVec(prometheus.GaugeOpts{
			Name: "llm_usage_window_limit",
			Help: "Limit size for provider usage windows.",
		}, []string{"provider", "limit_id", "limit_name"}),
		ratio: prometheus.NewGaugeVec(prometheus.GaugeOpts{
			Name: "llm_usage_window_used_ratio",
			Help: "Ratio of used units to limit for provider usage windows.",
		}, []string{"provider", "limit_id", "limit_name"}),
		resetAt: prometheus.NewGaugeVec(prometheus.GaugeOpts{
			Name: "llm_usage_window_reset_timestamp_seconds",
			Help: "Unix timestamp when the usage window will reset.",
		}, []string{"provider", "limit_id", "limit_name"}),
		health: prometheus.NewGaugeVec(prometheus.GaugeOpts{
			Name: "llm_usage_provider_health",
			Help: "Provider health marker: 1 for healthy, 0 for degraded/error.",
		}, []string{"provider"}),
	}
	if e.Enabled {
		e.registry.MustRegister(e.used, e.limit, e.ratio, e.resetAt, e.health)
	}
	return e
}

func (e *Exporter) Apply(snapshot model.Snapshot) {
	if !e.Enabled {
		return
	}
	e.used.Reset()
	e.limit.Reset()
	e.ratio.Reset()
	e.resetAt.Reset()
	e.health.Reset()

	for _, provider := range snapshot.Providers {
		if provider.Status == model.ProviderStatusOK {
			e.health.WithLabelValues(provider.ID).Set(1)
		} else {
			e.health.WithLabelValues(provider.ID).Set(0)
		}
		for _, window := range provider.UsageWindows {
			labels := []string{provider.ID, window.LimitID, window.LimitName}
			e.used.WithLabelValues(labels...).Set(float64(window.Used))
			e.limit.WithLabelValues(labels...).Set(float64(window.Limit))
			e.ratio.WithLabelValues(labels...).Set(normalizePercent(window.UsedPercent))
			if window.ResetsAt != nil {
				e.resetAt.WithLabelValues(labels...).Set(float64(window.ResetsAt.Unix()))
			}
		}
	}
}

func normalizePercent(value float64) float64 {
	if value < 0 {
		return 0
	}
	if value > 100 {
		return 1
	}
	return value / 100
}

func (e *Exporter) Handler() http.Handler {
	if !e.Enabled {
		return http.NotFoundHandler()
	}
	return promhttp.HandlerFor(e.registry, promhttp.HandlerOpts{})
}
