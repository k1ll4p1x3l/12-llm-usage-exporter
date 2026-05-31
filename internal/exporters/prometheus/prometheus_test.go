package prometheus

import (
	"io"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
)

func TestApplyExposesProviderMetrics(t *testing.T) {
	t.Parallel()

	resetAt := time.Unix(1800000000, 0).UTC()
	exporter := New(true)
	exporter.Apply(model.Snapshot{
		Providers: []model.ProviderSnapshot{
			{
				ID:     "codex",
				Status: model.ProviderStatusOK,
				UsageWindows: []model.UsageWindow{
					{
						LimitID:     "rpm",
						LimitName:   "requests",
						Used:        5,
						Limit:       10,
						UsedPercent: 50,
						ResetsAt:    &resetAt,
					},
				},
			},
		},
	})

	request := httptest.NewRequest("GET", "/metrics", nil)
	recorder := httptest.NewRecorder()
	exporter.Handler().ServeHTTP(recorder, request)

	body, err := io.ReadAll(recorder.Result().Body)
	if err != nil {
		t.Fatalf("read metrics: %v", err)
	}
	got := string(body)
	for _, want := range []string{
		`llm_usage_provider_health{provider="codex"} 1`,
		`llm_usage_window_used{limit_id="rpm",limit_name="requests",provider="codex"} 5`,
		`llm_usage_window_limit{limit_id="rpm",limit_name="requests",provider="codex"} 10`,
		`llm_usage_window_used_ratio{limit_id="rpm",limit_name="requests",provider="codex"} 0.5`,
		`llm_usage_window_reset_timestamp_seconds{limit_id="rpm",limit_name="requests",provider="codex"} 1.8e+09`,
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("metrics missing %q in:\n%s", want, got)
		}
	}
}

func TestHandlerDisabledReturnsNotFound(t *testing.T) {
	t.Parallel()

	exporter := New(false)
	request := httptest.NewRequest("GET", "/metrics", nil)
	recorder := httptest.NewRecorder()
	exporter.Handler().ServeHTTP(recorder, request)

	if recorder.Code != 404 {
		t.Fatalf("expected 404, got %d", recorder.Code)
	}
}
