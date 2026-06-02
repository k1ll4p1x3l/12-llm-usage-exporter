package codex

import (
	"context"
	"fmt"
)

const (
	policyMethodInitialize  = "initialize"
	policyMethodInitialized = "initialized"
)

type policyClient struct {
	next RPCClient
}

func NewPolicyClient(next RPCClient) RPCClient {
	return &policyClient{next: next}
}

func (c *policyClient) Call(ctx context.Context, method string, params any, out any) error {
	if !allowedCall(method) {
		return fmt.Errorf("codex rpc policy violation: method %q is not allowed", method)
	}
	return c.next.Call(ctx, method, params, out)
}

func (c *policyClient) Notify(ctx context.Context, method string, params any) error {
	if !allowedNotification(method) {
		return fmt.Errorf("codex rpc policy violation: notification %q is not allowed", method)
	}
	return c.next.Notify(ctx, method, params)
}

func (c *policyClient) Close() error {
	return c.next.Close()
}

func allowedCall(method string) bool {
	switch method {
	case policyMethodInitialize, policyMethodAccountRead, policyMethodRateLimitsRead:
		return true
	default:
		return false
	}
}

func allowedNotification(method string) bool {
	return method == policyMethodInitialized
}
