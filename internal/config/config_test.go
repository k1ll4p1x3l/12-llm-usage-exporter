package config_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/k1ll4p1x3l/12-llm-usage-exporter/internal/config"
)

func TestLoadJSON(t *testing.T) {
	t.Parallel()

	raw := map[string]any{
		"poll_interval": "30s",
		"json_output": map[string]any{
			"enabled": true,
			"path":    "/tmp/test-snapshot.json",
			"pretty":  false,
		},
		"prometheus": map[string]any{
			"enabled":        true,
			"listen_address": "127.0.0.1:1234",
		},
		"providers": []map[string]any{
			{
				"name":    "codex",
				"type":    "codex",
				"enabled": true,
				"command": "codex",
				"timeout": "15s",
			},
		},
	}

	payload, err := json.Marshal(raw)
	if err != nil {
		t.Fatalf("marshal config: %v", err)
	}

	tmp := t.TempDir()
	cfgPath := filepath.Join(tmp, "config.json")
	if err := os.WriteFile(cfgPath, payload, 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}

	cfg, err := config.Load(cfgPath)
	if err != nil {
		t.Fatalf("load config: %v", err)
	}
	if cfg.PollInterval.String() != "30s" {
		t.Fatalf("unexpected poll interval: %v", cfg.PollInterval)
	}
	if cfg.Prometheus.ListenAddress != "127.0.0.1:1234" {
		t.Fatalf("unexpected prometheus address: %q", cfg.Prometheus.ListenAddress)
	}
	if len(cfg.Providers) != 1 || cfg.Providers[0].Name != "codex" {
		t.Fatalf("unexpected providers: %#v", cfg.Providers)
	}
	if cfg.Providers[0].Timeout != 15*time.Second {
		t.Fatalf("unexpected provider timeout: %v", cfg.Providers[0].Timeout)
	}
}

func TestInvalidConfig(t *testing.T) {
	t.Parallel()

	tmp := t.TempDir()
	cfgPath := filepath.Join(tmp, "config.json")
	if err := os.WriteFile(cfgPath, []byte(`{"poll_interval":"0"}`), 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}
	if _, err := config.Load(cfgPath); err == nil {
		t.Fatal("expected load error")
	}
}

func TestEnvOverridePollInterval(t *testing.T) {
	tmp := t.TempDir()
	cfgPath := filepath.Join(tmp, "config.json")
	if err := os.WriteFile(cfgPath, []byte(`{"poll_interval":"5s"}`), 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}

	t.Setenv("LLM_USAGE_EXPORTER_POLL_INTERVAL", "2m")
	cfg, err := config.Load(cfgPath)
	if err != nil {
		t.Fatalf("load config: %v", err)
	}
	if cfg.PollInterval != (2 * time.Minute) {
		t.Fatalf("unexpected poll interval from env: %v", cfg.PollInterval)
	}
}

func TestEnvOverrideInvalidPollInterval(t *testing.T) {
	cfgPath := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(cfgPath, []byte(`{"poll_interval":"30s"}`), 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}

	t.Setenv("LLM_USAGE_EXPORTER_POLL_INTERVAL", "abc")
	if _, err := config.Load(cfgPath); err == nil {
		t.Fatal("expected invalid env override error")
	}
}

func TestParseDurationForExtendedUnits(t *testing.T) {
	cfgPath := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(cfgPath, []byte(`{}`), 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}

	t.Setenv("LLM_USAGE_EXPORTER_POLL_INTERVAL", "1d")
	cfg, err := config.Load(cfgPath)
	if err != nil {
		t.Fatalf("load config: %v", err)
	}
	if cfg.PollInterval != 24*time.Hour {
		t.Fatalf("unexpected poll interval for d: %v", cfg.PollInterval)
	}
}

func TestInvalidDurationLiteral(t *testing.T) {
	cfgPath := filepath.Join(t.TempDir(), "config.json")
	if err := os.WriteFile(cfgPath, []byte(`{}`), 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}

	t.Setenv("LLM_USAGE_EXPORTER_POLL_INTERVAL", "30z")
	_, err := config.Load(cfgPath)
	if err == nil {
		t.Fatal("expected invalid duration env error")
	}
	if !strings.Contains(err.Error(), "invalid LLM_USAGE_EXPORTER_POLL_INTERVAL") {
		t.Fatalf("unexpected error: %v", err)
	}
}

func TestValidateRejectsUnsupportedProviderType(t *testing.T) {
	t.Parallel()

	cfg := config.Default()
	cfg.Providers[0].Type = "unknown"
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected unsupported provider error")
	}
}

func TestValidateRejectsDisabledOnlyProviders(t *testing.T) {
	t.Parallel()

	cfg := config.Default()
	cfg.Providers[0].Enabled = false
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected no enabled providers error")
	}
}

func TestValidateRejectsEnabledJSONWithoutPath(t *testing.T) {
	t.Parallel()

	cfg := config.Default()
	cfg.JSONOutput.Path = ""
	if err := cfg.Validate(); err == nil {
		t.Fatal("expected empty json path error")
	}
}
