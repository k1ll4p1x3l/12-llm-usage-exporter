package service

import (
	"fmt"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/collectors"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/collectors/codex"
	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/config"
)

func BuildCollectors(cfg config.Config) ([]collectors.Collector, error) {
	instances := make([]collectors.Collector, 0, len(cfg.Providers))

	for _, provider := range cfg.Providers {
		if !provider.Enabled {
			continue
		}
		switch provider.Type {
		case "codex":
			client := codex.NewAppServerClient(codex.AppServerConfig{
				Command: provider.Command,
				Args:    provider.Args,
				Timeout: provider.Timeout,
			})
			instances = append(instances, codex.NewCollector(provider.Name, client))
		default:
			return nil, fmt.Errorf("unsupported provider type: %s", provider.Type)
		}
	}

	if len(instances) == 0 {
		return nil, fmt.Errorf("no enabled providers")
	}
	return instances, nil
}
