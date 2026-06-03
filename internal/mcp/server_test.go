// Copyright 2024 Red Hat, Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package mcp

import (
	"encoding/json"
	"fmt"
	"os"
	"testing"
)

// mockHandler is a test double for ToolHandler that records calls and returns preset results.
type mockHandler struct {
	result *CallToolResult
	err    error
	called string
}

func (m *mockHandler) HandleTool(name string, _ map[string]interface{}) (*CallToolResult, error) {
	m.called = name
	return m.result, m.err
}

func newTestServer(h ToolHandler) *Server {
	s := NewServer(h)
	s.RegisterTool(Tool{
		Name:        "test_tool",
		Description: "A test tool",
		InputSchema: ToolSchema{Type: "object", Properties: map[string]interface{}{}},
	})
	return s
}


func TestHandleInitialize(t *testing.T) {
	s := newTestServer(&mockHandler{})
	req := &Request{JSONRPC: "2.0", ID: 1, Method: "initialize"}
	resp := s.handleRequest(req)

	if resp.Error != nil {
		t.Fatalf("expected no error, got %v", resp.Error)
	}
	result, ok := resp.Result.(InitializeResult)
	if !ok {
		t.Fatalf("expected InitializeResult, got %T", resp.Result)
	}
	if result.ProtocolVersion == "" {
		t.Error("protocol version should not be empty")
	}
	if result.ServerInfo.Name != "gcal-mcp-server" {
		t.Errorf("expected server name 'gcal-mcp-server', got %q", result.ServerInfo.Name)
	}
	if result.Capabilities.Tools == nil {
		t.Error("expected tools capability to be present")
	}
}

func TestHandleInitialized(t *testing.T) {
	s := newTestServer(&mockHandler{})
	req := &Request{JSONRPC: "2.0", ID: 2, Method: "initialized"}
	resp := s.handleRequest(req)
	if resp.Error != nil {
		t.Fatalf("unexpected error: %v", resp.Error)
	}
}

func TestHandleListTools(t *testing.T) {
	s := newTestServer(&mockHandler{})
	req := &Request{JSONRPC: "2.0", ID: 3, Method: "tools/list"}
	resp := s.handleRequest(req)

	if resp.Error != nil {
		t.Fatalf("expected no error, got %v", resp.Error)
	}
	result, ok := resp.Result.(ListToolsResult)
	if !ok {
		t.Fatalf("expected ListToolsResult, got %T", resp.Result)
	}
	if len(result.Tools) != 1 {
		t.Errorf("expected 1 tool, got %d", len(result.Tools))
	}
	if result.Tools[0].Name != "test_tool" {
		t.Errorf("expected tool name 'test_tool', got %q", result.Tools[0].Name)
	}
}

func TestHandleCallTool_KnownTool(t *testing.T) {
	handler := &mockHandler{
		result: &CallToolResult{
			Content: []ToolResult{{Type: "text", Text: "hello"}},
		},
	}
	s := newTestServer(handler)

	params, _ := json.Marshal(CallToolParams{Name: "test_tool", Arguments: map[string]interface{}{"key": "value"}})
	req := &Request{JSONRPC: "2.0", ID: 4, Method: "tools/call", Params: params}
	resp := s.handleRequest(req)

	if resp.Error != nil {
		t.Fatalf("expected no error, got %v", resp.Error)
	}
	if handler.called != "test_tool" {
		t.Errorf("expected handler called with 'test_tool', got %q", handler.called)
	}
}

func TestHandleCallTool_UnknownTool(t *testing.T) {
	s := newTestServer(&mockHandler{})

	params, _ := json.Marshal(CallToolParams{Name: "no_such_tool"})
	req := &Request{JSONRPC: "2.0", ID: 5, Method: "tools/call", Params: params}
	resp := s.handleRequest(req)

	if resp.Error == nil {
		t.Fatal("expected error for unknown tool, got nil")
	}
	if resp.Error.Code != -32602 {
		t.Errorf("expected error code -32602, got %d", resp.Error.Code)
	}
}

func TestHandleCallTool_HandlerError(t *testing.T) {
	handler := &mockHandler{err: fmt.Errorf("tool failed")}
	s := newTestServer(handler)

	params, _ := json.Marshal(CallToolParams{Name: "test_tool"})
	req := &Request{JSONRPC: "2.0", ID: 6, Method: "tools/call", Params: params}
	resp := s.handleRequest(req)

	// Handler errors are returned as a CallToolResult with IsError=true, not as a JSON-RPC error.
	if resp.Error != nil {
		t.Fatalf("expected no JSON-RPC error, got %v", resp.Error)
	}
	result, ok := resp.Result.(*CallToolResult)
	if !ok {
		t.Fatalf("expected *CallToolResult, got %T", resp.Result)
	}
	if result.IsError == nil || !*result.IsError {
		t.Error("expected IsError to be true")
	}
}

func TestHandleUnknownMethod(t *testing.T) {
	s := newTestServer(&mockHandler{})
	req := &Request{JSONRPC: "2.0", ID: 7, Method: "not/a/method"}
	resp := s.handleRequest(req)

	if resp.Error == nil {
		t.Fatal("expected error for unknown method")
	}
	if resp.Error.Code != -32601 {
		t.Errorf("expected -32601 (method not found), got %d", resp.Error.Code)
	}
}

func TestHandleShutdown(t *testing.T) {
	s := newTestServer(&mockHandler{})
	req := &Request{JSONRPC: "2.0", ID: 8, Method: "shutdown"}
	resp := s.handleRequest(req)
	if resp.Error != nil {
		t.Fatalf("unexpected error on shutdown: %v", resp.Error)
	}
}

// ----- sendResponse / sendError / LogToStderr -----

func captureStdout(t *testing.T, fn func()) string {
	t.Helper()
	old := os.Stdout
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("failed to create pipe: %v", err)
	}
	os.Stdout = w

	fn()

	if err := w.Close(); err != nil {
		t.Fatalf("failed to close pipe writer: %v", err)
	}
	os.Stdout = old

	buf := make([]byte, 4096)
	n, _ := r.Read(buf)
	return string(buf[:n])
}

func captureStderr(t *testing.T, fn func()) string {
	t.Helper()
	old := os.Stderr
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("failed to create pipe: %v", err)
	}
	os.Stderr = w

	fn()

	if err := w.Close(); err != nil {
		t.Fatalf("failed to close pipe writer: %v", err)
	}
	os.Stderr = old

	buf := make([]byte, 4096)
	n, _ := r.Read(buf)
	return string(buf[:n])
}

func TestSendResponse(t *testing.T) {
	s := newTestServer(&mockHandler{})
	resp := &Response{JSONRPC: "2.0", ID: 1, Result: map[string]string{"ok": "true"}}

	out := captureStdout(t, func() {
		if err := s.sendResponse(resp); err != nil {
			t.Errorf("sendResponse error: %v", err)
		}
	})
	if len(out) == 0 {
		t.Error("sendResponse should write to stdout")
	}
	var got Response
	if err := json.Unmarshal([]byte(out), &got); err != nil {
		t.Errorf("sendResponse output should be valid JSON: %v", err)
	}
}

func TestSendError(t *testing.T) {
	s := newTestServer(&mockHandler{})
	out := captureStdout(t, func() {
		s.sendError(42, -32600, "invalid request", nil)
	})
	if len(out) == 0 {
		t.Error("sendError should write to stdout")
	}
	var got Response
	if err := json.Unmarshal([]byte(out), &got); err != nil {
		t.Errorf("sendError output should be valid JSON: %v", err)
	}
	if got.Error == nil || got.Error.Code != -32600 {
		t.Errorf("expected error code -32600, got %v", got.Error)
	}
}

func TestLogToStderr(t *testing.T) {
	s := newTestServer(&mockHandler{})
	out := captureStderr(t, func() {
		s.LogToStderr("test message %s", "hello")
	})
	if out == "" {
		t.Error("LogToStderr should write to stderr")
	}
	if !contains(out, "test message hello") {
		t.Errorf("expected 'test message hello' in stderr, got %q", out)
	}
}

func contains(s, sub string) bool {
	return len(s) >= len(sub) && (s == sub || len(s) > 0 && containsAt(s, sub))
}

func containsAt(s, sub string) bool {
	for i := 0; i <= len(s)-len(sub); i++ {
		if s[i:i+len(sub)] == sub {
			return true
		}
	}
	return false
}

func TestHandleCallTool_InvalidParams(t *testing.T) {
	s := newTestServer(&mockHandler{})
	// Params that can't unmarshal into CallToolParams
	req := &Request{JSONRPC: "2.0", ID: 9, Method: "tools/call", Params: json.RawMessage(`not json`)}
	resp := s.handleRequest(req)
	if resp.Error == nil {
		t.Fatal("expected error for invalid params")
	}
}

func TestHandleInitialize_InvalidParams(t *testing.T) {
	s := newTestServer(&mockHandler{})
	req := &Request{JSONRPC: "2.0", ID: 10, Method: "initialize", Params: json.RawMessage(`not json`)}
	resp := s.handleRequest(req)
	if resp.Error == nil {
		t.Fatal("expected error for invalid initialize params")
	}
}

func TestNewServer_EmptyTools(t *testing.T) {
	s := NewServer(&mockHandler{})
	if len(s.tools) != 0 {
		t.Errorf("new server should have 0 tools, got %d", len(s.tools))
	}
}

func TestRegisterTool(t *testing.T) {
	s := NewServer(&mockHandler{})
	tool := Tool{Name: "my_tool", Description: "desc"}
	s.RegisterTool(tool)
	if _, ok := s.tools["my_tool"]; !ok {
		t.Error("tool should be registered after RegisterTool")
	}
}

func TestBoolPtr(t *testing.T) {
	p := boolPtr(true)
	if p == nil || !*p {
		t.Error("boolPtr(true) should return pointer to true")
	}
	p = boolPtr(false)
	if p == nil || *p {
		t.Error("boolPtr(false) should return pointer to false")
	}
}
