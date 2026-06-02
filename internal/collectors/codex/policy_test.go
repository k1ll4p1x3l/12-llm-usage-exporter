package codex

import (
	"context"
	"testing"
)

type recordingRPCClient struct {
	calls         []string
	notifications []string
}

func (c *recordingRPCClient) Call(_ context.Context, method string, _ any, _ any) error {
	c.calls = append(c.calls, method)
	return nil
}

func (c *recordingRPCClient) Notify(_ context.Context, method string, _ any) error {
	c.notifications = append(c.notifications, method)
	return nil
}

func (c *recordingRPCClient) Close() error { return nil }

func TestPolicyClientAllowsReadOnlyMethods(t *testing.T) {
	t.Parallel()

	inner := &recordingRPCClient{}
	client := NewPolicyClient(inner)
	if err := client.Call(context.Background(), policyMethodInitialize, nil, nil); err != nil {
		t.Fatalf("initialize rejected: %v", err)
	}
	if err := client.Notify(context.Background(), policyMethodInitialized, nil); err != nil {
		t.Fatalf("initialized rejected: %v", err)
	}
	if err := client.Call(context.Background(), policyMethodAccountRead, nil, nil); err != nil {
		t.Fatalf("account/read rejected: %v", err)
	}
	if err := client.Call(context.Background(), policyMethodRateLimitsRead, nil, nil); err != nil {
		t.Fatalf("account/rateLimits/read rejected: %v", err)
	}
	if len(inner.calls) != 3 || len(inner.notifications) != 1 {
		t.Fatalf("unexpected forwarding: calls=%v notifications=%v", inner.calls, inner.notifications)
	}
}

func TestPolicyClientRejectsForbiddenMethodsBeforeTransport(t *testing.T) {
	t.Parallel()

	inner := &recordingRPCClient{}
	client := NewPolicyClient(inner)
	if err := client.Call(context.Background(), "account/logout", nil, nil); err == nil {
		t.Fatal("expected forbidden method error")
	}
	if err := client.Notify(context.Background(), "account/updated", nil); err == nil {
		t.Fatal("expected forbidden notification error")
	}
	if len(inner.calls) != 0 || len(inner.notifications) != 0 {
		t.Fatalf("forbidden methods reached transport: %#v %#v", inner.calls, inner.notifications)
	}
}
