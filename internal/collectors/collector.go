package collectors

import (
	"context"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/model"
)

type Collector interface {
	ID() string
	Capabilities() []string
	Collect(ctx context.Context) (model.ProviderSnapshot, error)
}
