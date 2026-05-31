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
