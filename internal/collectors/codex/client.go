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
	defaultTimeout         = 10 * time.Second
	defaultMaxMessageBytes = 1024 * 1024
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
	Command         string
	Args            []string
	Timeout         time.Duration
	MaxMessageBytes int
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
			Command:         cfg.Command,
			Args:            cfg.Args,
			Timeout:         cfg.Timeout,
			MaxMessageBytes: cfg.MaxMessageBytes,
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
	if c.cfg.MaxMessageBytes <= 0 {
		c.cfg.MaxMessageBytes = defaultMaxMessageBytes
	}

	command := strings.TrimSpace(c.cfg.Command)
	if command == "" {
		command = "codex"
	}

	if err := ctx.Err(); err != nil {
		return fmt.Errorf("start appserver: %w", err)
	}

	cmd := exec.Command(command, c.cfg.Args...)
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

	callCtx, cancel := c.contextWithTimeout(ctx)
	defer cancel()

	if err := c.ensureStarted(callCtx); err != nil {
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

	raw, err := c.readMessageWithContext(callCtx)
	if err != nil {
		return err
	}

	var response rpcResponse
	if err := json.Unmarshal(raw, &response); err != nil {
		return fmt.Errorf("parse response: %w", err)
	}
	if response.JSONRPC != "2.0" {
		return fmt.Errorf("invalid jsonrpc version: %q", response.JSONRPC)
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

func (c *AppServerClient) contextWithTimeout(ctx context.Context) (context.Context, context.CancelFunc) {
	if _, ok := ctx.Deadline(); ok {
		return ctx, func() {}
	}
	return context.WithTimeout(ctx, c.timeout())
}

func (c *AppServerClient) timeout() time.Duration {
	if c.cfg.Timeout <= 0 {
		return defaultTimeout
	}
	return c.cfg.Timeout
}

func (c *AppServerClient) readMessageWithContext(ctx context.Context) ([]byte, error) {
	result := make(chan struct {
		payload []byte
		err     error
	}, 1)
	go func() {
		payload, err := c.readMessage()
		result <- struct {
			payload []byte
			err     error
		}{payload: payload, err: err}
	}()

	select {
	case <-ctx.Done():
		c.stopLocked()
		return nil, fmt.Errorf("read response: %w", ctx.Err())
	case read := <-result:
		return read.payload, read.err
	}
}

func (c *AppServerClient) readMessage() ([]byte, error) {
	reader := c.reader
	if reader == nil {
		return nil, fmt.Errorf("read response: client is not started")
	}
	for {
		line, err := readLineLimited(reader, c.maxMessageBytes())
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
				return nil, fmt.Errorf("invalid content-length %q: %w", strings.TrimSpace(parts[1]), err)
			}
			if size < 0 || size > c.maxMessageBytes() {
				return nil, fmt.Errorf("framed body size %d exceeds limit %d", size, c.maxMessageBytes())
			}
			if err := discardHeader(reader, c.maxMessageBytes()); err != nil {
				return nil, err
			}
			payload := make([]byte, size)
			if _, err := io.ReadFull(reader, payload); err != nil {
				return nil, fmt.Errorf("read framed body: %w", err)
			}
			return bytes.TrimSpace(payload), nil
		}
		if strings.HasPrefix(trimmed, "{") || strings.HasPrefix(trimmed, "[") {
			if len(trimmed) > c.maxMessageBytes() {
				return nil, fmt.Errorf("unframed body size %d exceeds limit %d", len(trimmed), c.maxMessageBytes())
			}
			return []byte(trimmed), nil
		}
	}
}

func readLineLimited(reader *bufio.Reader, maxBytes int) (string, error) {
	var line []byte
	for {
		fragment, err := reader.ReadSlice('\n')
		line = append(line, fragment...)
		if len(line) > maxBytes {
			return "", fmt.Errorf("response line size %d exceeds limit %d", len(line), maxBytes)
		}
		if err == nil {
			return string(line), nil
		}
		if err != bufio.ErrBufferFull {
			return "", err
		}
	}
}

func (c *AppServerClient) maxMessageBytes() int {
	if c.cfg.MaxMessageBytes <= 0 {
		return defaultMaxMessageBytes
	}
	return c.cfg.MaxMessageBytes
}

func discardHeader(reader *bufio.Reader, maxBytes int) error {
	for {
		line, err := readLineLimited(reader, maxBytes)
		if err != nil {
			return fmt.Errorf("read framed header: %w", err)
		}
		if strings.TrimSpace(line) == "" {
			return nil
		}
	}
}

func (c *AppServerClient) Close() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.started {
		return nil
	}
	c.stopLocked()
	return nil
}

func (c *AppServerClient) stopLocked() {
	if c.stdin != nil {
		_ = c.stdin.Close()
	}
	if c.cmd != nil && c.cmd.Process != nil {
		_ = c.cmd.Process.Kill()
		_ = c.cmd.Wait()
	}
	c.started = false
	c.stdin = nil
	c.reader = nil
	c.encoder = nil
	c.cmd = nil
}
