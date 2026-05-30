package codex

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	defaultTimeout = 10 * time.Second
)

type rpcRequest struct {
	JSONRPC string `json:"jsonrpc"`
	ID      int64  `json:"id"`
	Method  string `json:"method"`
	Params  any    `json:"params,omitempty"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      int64           `json:"id"`
	Result  json.RawMessage `json:"result"`
	Error   *rpcError       `json:"error"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    any    `json:"data,omitempty"`
}

type RPCClient interface {
	Call(ctx context.Context, method string, params any, out any) error
	Close() error
}

type AppServerConfig struct {
	Command string
	Args    []string
	Timeout time.Duration
}

type AppServerClient struct {
	cfg     AppServerConfig
	mu      sync.Mutex
	cmd     *exec.Cmd
	stdin   io.WriteCloser
	reader  *bufio.Reader
	encoder *json.Encoder
	nextID  int64
	started bool
}

func NewAppServerClient(cfg AppServerConfig) *AppServerClient {
	return &AppServerClient{
		cfg: AppServerConfig{
			Command: cfg.Command,
			Args:    cfg.Args,
			Timeout: cfg.Timeout,
		},
	}
}

func (c *AppServerClient) ensureStarted(ctx context.Context) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.started {
		return nil
	}

	if c.cfg.Timeout <= 0 {
		c.cfg.Timeout = defaultTimeout
	}

	command := strings.TrimSpace(c.cfg.Command)
	if command == "" {
		command = "codex"
	}

	commandCtx, cancel := context.WithTimeout(ctx, c.cfg.Timeout)
	defer cancel()

	cmd := exec.CommandContext(commandCtx, command, c.cfg.Args...)
	cmd.Stderr = os.Stderr
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return fmt.Errorf("start client stdin: %w", err)
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("start client stdout: %w", err)
	}

	if err := cmd.Start(); err != nil {
		return fmt.Errorf("start appserver: %w", err)
	}

	c.cmd = cmd
	c.stdin = stdin
	c.reader = bufio.NewReader(stdout)
	c.encoder = json.NewEncoder(stdin)
	c.started = true
	return nil
}

func (c *AppServerClient) Call(ctx context.Context, method string, params any, out any) error {
	if method == "" {
		return fmt.Errorf("empty method")
	}
	if err := c.ensureStarted(ctx); err != nil {
		return err
	}

	c.mu.Lock()
	defer c.mu.Unlock()

	id := c.nextID
	c.nextID++
	request := rpcRequest{
		JSONRPC: "2.0",
		ID:      id,
		Method:  method,
		Params:  params,
	}
	if err := c.encoder.Encode(&request); err != nil {
		return fmt.Errorf("write request: %w", err)
	}

	raw, err := c.readMessage()
	if err != nil {
		return err
	}

	var response rpcResponse
	if err := json.Unmarshal(raw, &response); err != nil {
		return fmt.Errorf("parse response: %w", err)
	}
	if response.ID != id {
		return fmt.Errorf("response id mismatch: expected %d got %d", id, response.ID)
	}
	if response.Error != nil {
		return fmt.Errorf("rpc error (%d): %s", response.Error.Code, response.Error.Message)
	}
	if out == nil {
		return nil
	}
	if rm, ok := out.(*json.RawMessage); ok {
		*rm = append((*rm)[0:0], response.Result...)
		return nil
	}
	if len(response.Result) == 0 {
		return nil
	}
	if err := json.Unmarshal(response.Result, out); err != nil {
		return fmt.Errorf("unmarshal result: %w", err)
	}
	return nil
}

func (c *AppServerClient) readMessage() ([]byte, error) {
	for {
		line, err := c.reader.ReadString('\n')
		if err != nil {
			return nil, fmt.Errorf("read response: %w", err)
		}
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		lower := strings.ToLower(trimmed)
		if strings.HasPrefix(lower, "content-length:") {
			parts := strings.SplitN(trimmed, ":", 2)
			if len(parts) != 2 {
				continue
			}
			size, err := strconv.Atoi(strings.TrimSpace(parts[1]))
			if err != nil {
				continue
			}
			payload := make([]byte, size)
			if _, err := io.ReadFull(c.reader, payload); err != nil {
				return nil, fmt.Errorf("read framed body: %w", err)
			}
			c.discardLine()
			return bytes.TrimSpace(payload), nil
		}
		if strings.HasPrefix(trimmed, "{") || strings.HasPrefix(trimmed, "[") {
			return []byte(trimmed), nil
		}
	}
}

func (c *AppServerClient) discardLine() {
	for {
		if b, err := c.reader.Peek(1); err == nil && b[0] == '\n' {
			c.reader.ReadByte()
			continue
		}
		if b, err := c.reader.Peek(2); err == nil && bytes.Equal(b, []byte{'\r', '\n'}) {
			c.reader.ReadByte()
			c.reader.ReadByte()
		}
		break
	}
}

func (c *AppServerClient) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.started {
		return nil
	}
	if c.stdin != nil {
		c.stdin.Close()
	}
	if c.cmd != nil && c.cmd.Process != nil {
		c.cmd.Process.Kill()
		_ = c.cmd.Wait()
	}
	c.started = false
	return nil
}
