package codex

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"testing"
	"time"
)

func TestAppServerClientCallHelperProcess(t *testing.T) {
	exe, err := os.Executable()
	if err != nil {
		t.Fatalf("os.Executable returned error: %v", err)
	}
	t.Setenv("CODEX_TEST_APPSERVER_HELPER", "1")

	client := NewAppServerClient(AppServerConfig{
		Command:         exe,
		Args:            []string{"-test.run=TestAppServerClientHelperProcess"},
		Timeout:         time.Second,
		MaxMessageBytes: 1024,
	})
	defer client.Close()

	var out struct {
		OK bool `json:"ok"`
	}
	if err := client.Call(context.Background(), "ping", nil, &out); err != nil {
		t.Fatalf("Call returned error: %v", err)
	}
	if !out.OK {
		t.Fatalf("unexpected response: %#v", out)
	}
}

func TestAppServerClientHelperProcess(t *testing.T) {
	if os.Getenv("CODEX_TEST_APPSERVER_HELPER") != "1" {
		return
	}

	var request rpcRequest
	if err := json.NewDecoder(os.Stdin).Decode(&request); err != nil {
		fmt.Fprintf(os.Stderr, "decode request: %v\n", err)
		os.Exit(2)
	}
	payload, err := json.Marshal(rpcResponse{
		ID:     &request.ID,
		Result: json.RawMessage(`{"ok":true}`),
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "marshal response: %v\n", err)
		os.Exit(2)
	}
	fmt.Fprintf(os.Stdout, "Content-Length: %d\r\n\r\n%s", len(payload), payload)
	os.Exit(0)
}

func TestCallSkipsNotificationsBeforeResponse(t *testing.T) {
	t.Parallel()

	id := int64(0)
	notification := `{"method":"account/rateLimits/updated","params":{}}`
	response := fmt.Sprintf(`{"id":%d,"result":{"ok":true}}`, id)
	client := &AppServerClient{
		cfg:     AppServerConfig{MaxMessageBytes: 1024, Timeout: time.Second},
		reader:  bufio.NewReader(strings.NewReader(notification + "\n" + response + "\n")),
		encoder: json.NewEncoder(&strings.Builder{}),
		started: true,
	}

	var out struct {
		OK bool `json:"ok"`
	}
	if err := client.Call(context.Background(), "ping", nil, &out); err != nil {
		t.Fatalf("Call returned error: %v", err)
	}
	if !out.OK {
		t.Fatalf("unexpected output: %#v", out)
	}
}

func TestResolveCommandRejectsMissingPathCommand(t *testing.T) {
	t.Parallel()

	if _, err := ResolveCommand("llm-usage-exporter-command-that-does-not-exist"); err == nil {
		t.Fatal("expected missing command error")
	}
}

func TestResolveCommandKeepsExplicitPath(t *testing.T) {
	t.Parallel()

	got, err := ResolveCommand("./local-codex")
	if err != nil {
		t.Fatalf("explicit path returned error: %v", err)
	}
	if got != "./local-codex" {
		t.Fatalf("unexpected explicit path: %q", got)
	}
}

func TestReadMessageConsumesCRLFFramedHeader(t *testing.T) {
	t.Parallel()

	payload := `{"jsonrpc":"2.0","id":1,"result":{"ok":true}}`
	client := &AppServerClient{
		cfg:    AppServerConfig{MaxMessageBytes: 1024},
		reader: bufio.NewReader(strings.NewReader(fmt.Sprintf("Content-Length: %d\r\n\r\n%s", len(payload), payload))),
	}

	raw, err := client.readMessage()
	if err != nil {
		t.Fatalf("readMessage returned error: %v", err)
	}
	if string(raw) != payload {
		t.Fatalf("unexpected payload: %q", raw)
	}
}

func TestReadMessageConsumesLFFramedHeader(t *testing.T) {
	t.Parallel()

	payload := `{"jsonrpc":"2.0","id":1,"result":null}`
	client := &AppServerClient{
		cfg:    AppServerConfig{MaxMessageBytes: 1024},
		reader: bufio.NewReader(strings.NewReader(fmt.Sprintf("Content-Length: %d\n\n%s", len(payload), payload))),
	}

	raw, err := client.readMessage()
	if err != nil {
		t.Fatalf("readMessage returned error: %v", err)
	}
	if string(raw) != payload {
		t.Fatalf("unexpected payload: %q", raw)
	}
}

func TestReadMessageRejectsOversizedFrame(t *testing.T) {
	t.Parallel()

	client := &AppServerClient{
		cfg:    AppServerConfig{MaxMessageBytes: 3},
		reader: bufio.NewReader(strings.NewReader("Content-Length: 4\r\n\r\n1234")),
	}

	if _, err := client.readMessage(); err == nil {
		t.Fatal("expected oversized frame error")
	}
}

func TestReadMessageRejectsInvalidContentLength(t *testing.T) {
	t.Parallel()

	client := &AppServerClient{
		cfg:    AppServerConfig{MaxMessageBytes: 1024},
		reader: bufio.NewReader(strings.NewReader("Content-Length: nope\r\n\r\n{}")),
	}

	if _, err := client.readMessage(); err == nil {
		t.Fatal("expected invalid content-length error")
	}
}

func TestReadMessageRejectsOversizedUnframedJSON(t *testing.T) {
	t.Parallel()

	client := &AppServerClient{
		cfg:    AppServerConfig{MaxMessageBytes: 8},
		reader: bufio.NewReader(strings.NewReader(`{"too":"long"}` + "\n")),
	}

	if _, err := client.readMessage(); err == nil {
		t.Fatal("expected oversized unframed JSON error")
	}
}
