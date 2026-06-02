package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func TestRunSnapshotReturnsCollectorError(t *testing.T) {
	exe, err := os.Executable()
	if err != nil {
		t.Fatalf("os.Executable returned error: %v", err)
	}
	t.Setenv("LLM_USAGE_EXPORTER_TEST_APPSERVER", "1")

	configPath := filepath.Join(t.TempDir(), "config.yaml")
	configData := fmt.Sprintf(`
poll_interval: 30s
json_output:
  enabled: false
prometheus:
  enabled: false
providers:
  - name: codex
    type: codex
    enabled: true
    command: %q
    args:
      - -test.run=TestRunSnapshotAppserverHelperProcess
    timeout: 1s
`, exe)
	if err := os.WriteFile(configPath, []byte(configData), 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}

	if err := runSnapshot([]string{"-config", configPath}); err == nil {
		t.Fatal("expected snapshot to return all-provider failure")
	}
}

func TestRunInitWritesConfigAndRejectsOverwrite(t *testing.T) {
	configPath := filepath.Join(t.TempDir(), "config.yaml")

	if err := runInit([]string{"--config", configPath}); err != nil {
		t.Fatalf("runInit returned error: %v", err)
	}
	if _, err := os.Stat(configPath); err != nil {
		t.Fatalf("expected config file: %v", err)
	}
	if err := runInit([]string{"--config", configPath}); err == nil {
		t.Fatal("expected overwrite rejection")
	}
	if err := runInit([]string{"--config", configPath, "--force"}); err != nil {
		t.Fatalf("runInit --force returned error: %v", err)
	}
}

func TestRunDoctorWithHelperAppserver(t *testing.T) {
	exe, err := os.Executable()
	if err != nil {
		t.Fatalf("os.Executable returned error: %v", err)
	}
	t.Setenv("LLM_USAGE_EXPORTER_DOCTOR_APPSERVER", "1")

	configPath := filepath.Join(t.TempDir(), "config.yaml")
	configData := fmt.Sprintf(`
poll_interval: 30s
json_output:
  enabled: false
prometheus:
  enabled: false
providers:
  - name: codex
    type: codex
    enabled: true
    command: %q
    args:
      - -test.run=TestRunDoctorAppserverHelperProcess
    timeout: 2s
`, exe)
	if err := os.WriteFile(configPath, []byte(configData), 0o600); err != nil {
		t.Fatalf("write config: %v", err)
	}

	if err := runDoctor([]string{"--config", configPath, "--json"}); err != nil {
		t.Fatalf("runDoctor returned error: %v", err)
	}
}

func TestRunSnapshotAppserverHelperProcess(t *testing.T) {
	if os.Getenv("LLM_USAGE_EXPORTER_TEST_APPSERVER") != "1" {
		return
	}

	var request struct {
		JSONRPC string `json:"jsonrpc"`
		ID      int64  `json:"id"`
	}
	if err := json.NewDecoder(os.Stdin).Decode(&request); err != nil {
		fmt.Fprintf(os.Stderr, "decode request: %v\n", err)
		os.Exit(2)
	}

	payload, err := json.Marshal(map[string]any{
		"jsonrpc": "2.0",
		"id":      request.ID,
		"error": map[string]any{
			"code":    -32000,
			"message": "forced failure",
		},
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "marshal response: %v\n", err)
		os.Exit(2)
	}
	fmt.Fprintf(os.Stdout, "Content-Length: %d\r\n\r\n%s", len(payload), payload)
	os.Exit(0)
}

func TestRunDoctorAppserverHelperProcess(t *testing.T) {
	if os.Getenv("LLM_USAGE_EXPORTER_DOCTOR_APPSERVER") != "1" {
		return
	}

	decoder := json.NewDecoder(os.Stdin)
	for {
		var request struct {
			ID     *int64          `json:"id"`
			Method string          `json:"method"`
			Params json.RawMessage `json:"params"`
		}
		if err := decoder.Decode(&request); err != nil {
			fmt.Fprintf(os.Stderr, "decode request: %v\n", err)
			os.Exit(2)
		}
		if request.ID == nil {
			continue
		}

		var result any
		switch request.Method {
		case "initialize":
			result = map[string]any{"platformFamily": "linux", "platformOs": "linux"}
		case "account/read":
			result = map[string]any{"account": map[string]any{"email": "user@example.com", "planType": "pro"}}
		case "account/rateLimits/read":
			result = map[string]any{
				"rateLimitsByLimitId": map[string]any{
					"codex": map[string]any{
						"limitId":   "codex",
						"limitName": "Codex",
						"primary": map[string]any{
							"usedPercent":        25,
							"windowDurationMins": 15,
							"resetsAt":           1730947200,
						},
					},
				},
			}
		default:
			payload, _ := json.Marshal(map[string]any{
				"id": request.ID,
				"error": map[string]any{
					"code":    -32601,
					"message": "unknown method",
				},
			})
			fmt.Fprintf(os.Stdout, "Content-Length: %d\r\n\r\n%s", len(payload), payload)
			continue
		}
		payload, err := json.Marshal(map[string]any{
			"id":     request.ID,
			"result": result,
		})
		if err != nil {
			fmt.Fprintf(os.Stderr, "marshal response: %v\n", err)
			os.Exit(2)
		}
		fmt.Fprintf(os.Stdout, "Content-Length: %d\r\n\r\n%s", len(payload), payload)
	}
}
