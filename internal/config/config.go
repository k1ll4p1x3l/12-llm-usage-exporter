package config

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/platform"
	"github.com/pelletier/go-toml/v2"
	"gopkg.in/yaml.v3"
)

const (
	DefaultPollIntervalSeconds = 60
	DefaultJSONPath            = "/tmp/llm-usage-exporter/usage.snapshot.json"
	DefaultListenAddress       = "127.0.0.1:9738"
)

type Config struct {
	PollInterval time.Duration    `json:"poll_interval" yaml:"poll_interval" toml:"poll_interval"`
	JSONOutput   JSONOutputConfig `json:"json_output" yaml:"json_output" toml:"json_output"`
	Prometheus   PrometheusConfig `json:"prometheus" yaml:"prometheus" toml:"prometheus"`
	Providers    []ProviderConfig `json:"providers" yaml:"providers" toml:"providers"`
}

type JSONOutputConfig struct {
	Enabled bool   `json:"enabled" yaml:"enabled" toml:"enabled"`
	Path    string `json:"path" yaml:"path" toml:"path"`
	Pretty  bool   `json:"pretty" yaml:"pretty" toml:"pretty"`
}

type PrometheusConfig struct {
	Enabled       bool   `json:"enabled" yaml:"enabled" toml:"enabled"`
	ListenAddress string `json:"listen_address" yaml:"listen_address" toml:"listen_address"`
}

type JSONOutputRawConfig struct {
	Enabled *bool   `json:"enabled" yaml:"enabled" toml:"enabled"`
	Path    *string `json:"path" yaml:"path" toml:"path"`
	Pretty  *bool   `json:"pretty" yaml:"pretty" toml:"pretty"`
}

type PrometheusRawConfig struct {
	Enabled       *bool   `json:"enabled" yaml:"enabled" toml:"enabled"`
	ListenAddress *string `json:"listen_address" yaml:"listen_address" toml:"listen_address"`
}

type ProviderConfig struct {
	Name    string        `json:"name" yaml:"name" toml:"name"`
	Type    string        `json:"type" yaml:"type" toml:"type"`
	Enabled bool          `json:"enabled" yaml:"enabled" toml:"enabled"`
	Command string        `json:"command" yaml:"command" toml:"command"`
	Args    []string      `json:"args" yaml:"args" toml:"args"`
	Timeout time.Duration `json:"timeout" yaml:"timeout" toml:"timeout"`
}

type rawProviderConfig struct {
	Name    string   `json:"name" yaml:"name" toml:"name"`
	Type    string   `json:"type" yaml:"type" toml:"type"`
	Enabled bool     `json:"enabled" yaml:"enabled" toml:"enabled"`
	Command string   `json:"command" yaml:"command" toml:"command"`
	Args    []string `json:"args" yaml:"args" toml:"args"`
	Timeout *string  `json:"timeout" yaml:"timeout" toml:"timeout"`
}

type rawConfig struct {
	PollInterval *string              `json:"poll_interval" yaml:"poll_interval" toml:"poll_interval"`
	JSONOutput   *JSONOutputRawConfig `json:"json_output" yaml:"json_output" toml:"json_output"`
	Prometheus   *PrometheusRawConfig `json:"prometheus" yaml:"prometheus" toml:"prometheus"`
	Providers    []rawProviderConfig  `json:"providers" yaml:"providers" toml:"providers"`
}

func Default() Config {
	cfg := Config{
		PollInterval: time.Duration(DefaultPollIntervalSeconds) * time.Second,
		JSONOutput: JSONOutputConfig{
			Enabled: true,
			Path:    DefaultJSONPath,
			Pretty:  true,
		},
		Prometheus: PrometheusConfig{
			Enabled:       false,
			ListenAddress: DefaultListenAddress,
		},
		Providers: []ProviderConfig{
			{
				Name:    "codex",
				Type:    "codex",
				Enabled: true,
				Command: "codex",
				Args:    []string{"app-server"},
				Timeout: 10 * time.Second,
			},
		},
	}
	if paths, err := platform.DefaultPaths(); err == nil {
		cfg.JSONOutput.Path = paths.StatePath
	}
	return cfg
}

func StarterConfig() Config {
	cfg := Default()
	cfg.Prometheus.Enabled = true
	return cfg
}

func StarterYAML(cfg Config) []byte {
	provider := ProviderConfig{}
	if len(cfg.Providers) > 0 {
		provider = cfg.Providers[0]
	}
	if provider.Name == "" {
		provider.Name = "codex"
	}
	if provider.Type == "" {
		provider.Type = "codex"
	}
	if provider.Command == "" {
		provider.Command = "codex"
	}
	if len(provider.Args) == 0 {
		provider.Args = []string{"app-server"}
	}
	if provider.Timeout == 0 {
		provider.Timeout = 10 * time.Second
	}

	return []byte(fmt.Sprintf(`poll_interval: %s
json_output:
  enabled: %t
  path: %q
  pretty: %t
prometheus:
  enabled: %t
  listen_address: %q
providers:
  - name: %q
    type: %q
    enabled: %t
    command: %q
    timeout: %s
    args:
%s`, cfg.PollInterval, cfg.JSONOutput.Enabled, cfg.JSONOutput.Path, cfg.JSONOutput.Pretty,
		cfg.Prometheus.Enabled, cfg.Prometheus.ListenAddress, provider.Name, provider.Type,
		provider.Enabled, provider.Command, provider.Timeout, formatArgs(provider.Args)))
}

func formatArgs(args []string) string {
	if len(args) == 0 {
		return "      []\n"
	}
	var b strings.Builder
	for _, arg := range args {
		b.WriteString(fmt.Sprintf("      - %q\n", arg))
	}
	return b.String()
}

func Load(path string) (Config, error) {
	cfg := Default()
	if path == "" {
		if err := applyEnvOverrides(&cfg); err != nil {
			return Config{}, err
		}
		return cfg, cfg.Validate()
	}

	raw, err := os.ReadFile(path)
	if err != nil {
		return Config{}, fmt.Errorf("read config: %w", err)
	}

	rawCfg := rawConfig{}
	ext := strings.ToLower(filepath.Ext(path))
	switch ext {
	case ".toml":
		if err := toml.Unmarshal(raw, &rawCfg); err != nil {
			return Config{}, fmt.Errorf("parse toml config: %w", err)
		}
	case ".yaml", ".yml":
		if err := yaml.Unmarshal(raw, &rawCfg); err != nil {
			return Config{}, fmt.Errorf("parse yaml config: %w", err)
		}
	default:
		if err := json.Unmarshal(raw, &rawCfg); err != nil {
			return Config{}, fmt.Errorf("parse json config: %w", err)
		}
	}

	if rawCfg.PollInterval != nil {
		parsed, err := parseDuration(*rawCfg.PollInterval)
		if err != nil {
			return Config{}, err
		}
		cfg.PollInterval = parsed
	}
	if rawCfg.JSONOutput != nil {
		if rawCfg.JSONOutput.Enabled != nil {
			cfg.JSONOutput.Enabled = *rawCfg.JSONOutput.Enabled
		}
		if rawCfg.JSONOutput.Path != nil {
			cfg.JSONOutput.Path = *rawCfg.JSONOutput.Path
		}
		if rawCfg.JSONOutput.Pretty != nil {
			cfg.JSONOutput.Pretty = *rawCfg.JSONOutput.Pretty
		}
	}
	if rawCfg.Prometheus != nil {
		if rawCfg.Prometheus.Enabled != nil {
			cfg.Prometheus.Enabled = *rawCfg.Prometheus.Enabled
		}
		if rawCfg.Prometheus.ListenAddress != nil {
			cfg.Prometheus.ListenAddress = *rawCfg.Prometheus.ListenAddress
		}
	}
	if len(rawCfg.Providers) > 0 {
		providers, err := normalizeProviders(rawCfg.Providers)
		if err != nil {
			return Config{}, err
		}
		cfg.Providers = providers
	}

	if err := applyEnvOverrides(&cfg); err != nil {
		return Config{}, err
	}
	return cfg, cfg.Validate()
}

func (cfg *Config) Validate() error {
	if cfg.PollInterval < 10*time.Second {
		return fmt.Errorf("poll_interval too low: %s", cfg.PollInterval)
	}
	if cfg.JSONOutput.Enabled && strings.TrimSpace(cfg.JSONOutput.Path) == "" {
		return fmt.Errorf("json_output enabled but path is empty")
	}
	if len(cfg.Providers) == 0 {
		return fmt.Errorf("at least one provider is required")
	}
	enabledProviders := 0
	for i, p := range cfg.Providers {
		if p.Type == "" {
			return fmt.Errorf("provider[%d] has missing type", i)
		}
		if p.Name == "" {
			return fmt.Errorf("provider[%d] has missing name", i)
		}
		if p.Type != "codex" {
			return fmt.Errorf("provider[%d] has unsupported type: %s", i, p.Type)
		}
		if p.Enabled {
			enabledProviders++
		}
		if p.Enabled && p.Timeout < 0 {
			return fmt.Errorf("provider[%d] timeout must not be negative", i)
		}
	}
	if enabledProviders == 0 {
		return fmt.Errorf("at least one provider must be enabled")
	}
	if cfg.Prometheus.Enabled && cfg.Prometheus.ListenAddress == "" {
		return fmt.Errorf("prometheus enabled but listen_address is empty")
	}
	return nil
}

func normalizeProviders(rawProviders []rawProviderConfig) ([]ProviderConfig, error) {
	providers := make([]ProviderConfig, 0, len(rawProviders))
	for i, raw := range rawProviders {
		provider := ProviderConfig{
			Name:    raw.Name,
			Type:    raw.Type,
			Enabled: raw.Enabled,
			Command: raw.Command,
			Args:    raw.Args,
		}
		if raw.Timeout != nil {
			timeout, err := parseDuration(*raw.Timeout)
			if err != nil {
				return nil, fmt.Errorf("provider[%d] invalid timeout: %w", i, err)
			}
			provider.Timeout = timeout
		}
		providers = append(providers, provider)
	}
	return providers, nil
}

func parseDuration(raw string) (time.Duration, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return 0, fmt.Errorf("empty duration")
	}

	if n, err := strconv.Atoi(raw); err == nil {
		return time.Duration(n) * time.Second, nil
	}

	if len(raw) < 2 {
		return 0, fmt.Errorf("invalid duration: %q", raw)
	}

	unit := raw[len(raw)-1]
	numberPart := raw[:len(raw)-1]
	switch unit {
	case 'd', 'w':
		multiplier := 1
		if unit == 'w' {
			multiplier = 7
		}
		seconds, err := strconv.Atoi(numberPart)
		if err != nil {
			return 0, fmt.Errorf("invalid duration: %w", err)
		}
		return time.Duration(seconds*multiplier*24) * time.Hour, nil
	}

	d, err := time.ParseDuration(raw)
	if err != nil {
		return 0, fmt.Errorf("invalid duration %q: %w", raw, err)
	}
	return d, nil
}

func applyEnvOverrides(cfg *Config) error {
	if val := os.Getenv("LLM_USAGE_EXPORTER_POLL_INTERVAL"); val != "" {
		d, err := parseDuration(val)
		if err != nil {
			return fmt.Errorf("invalid LLM_USAGE_EXPORTER_POLL_INTERVAL: %w", err)
		}
		cfg.PollInterval = d
	}
	if val := os.Getenv("LLM_USAGE_EXPORTER_JSON_ENABLED"); val != "" {
		enabled, err := strconv.ParseBool(val)
		if err != nil {
			return fmt.Errorf("invalid LLM_USAGE_EXPORTER_JSON_ENABLED: %w", err)
		}
		cfg.JSONOutput.Enabled = enabled
	}
	if val := os.Getenv("LLM_USAGE_EXPORTER_JSON_PATH"); val != "" {
		cfg.JSONOutput.Path = val
	}
	if val := os.Getenv("LLM_USAGE_EXPORTER_JSON_PRETTY"); val != "" {
		pretty, err := strconv.ParseBool(val)
		if err != nil {
			return fmt.Errorf("invalid LLM_USAGE_EXPORTER_JSON_PRETTY: %w", err)
		}
		cfg.JSONOutput.Pretty = pretty
	}
	if val := os.Getenv("LLM_USAGE_EXPORTER_METRICS_ENABLED"); val != "" {
		enabled, err := strconv.ParseBool(val)
		if err != nil {
			return fmt.Errorf("invalid LLM_USAGE_EXPORTER_METRICS_ENABLED: %w", err)
		}
		cfg.Prometheus.Enabled = enabled
	}
	if val := os.Getenv("LLM_USAGE_EXPORTER_METRICS_LISTEN_ADDRESS"); val != "" {
		cfg.Prometheus.ListenAddress = val
	}
	return nil
}
