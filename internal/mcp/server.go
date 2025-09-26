package mcp

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"os"
)

type Server struct {
	tools   map[string]Tool
	handler ToolHandler
}

type ToolHandler interface {
	HandleTool(name string, arguments map[string]interface{}) (*CallToolResult, error)
}

func NewServer(handler ToolHandler) *Server {
	return &Server{
		tools:   make(map[string]Tool),
		handler: handler,
	}
}

func (s *Server) RegisterTool(tool Tool) {
	s.tools[tool.Name] = tool
}

func (s *Server) Run() error {
	scanner := bufio.NewScanner(os.Stdin)

	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}

		var req Request
		if err := json.Unmarshal(line, &req); err != nil {
			s.sendError(req.ID, -32700, "Parse error", nil)
			continue
		}

		response := s.handleRequest(&req)
		if err := s.sendResponse(response); err != nil {
			log.Printf("Failed to send response: %v", err)
		}
	}

	return scanner.Err()
}

func (s *Server) handleRequest(req *Request) *Response {
	switch req.Method {
	case "initialize":
		return s.handleInitialize(req)
	case "initialized":
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  map[string]interface{}{},
		}
	case "tools/list":
		return s.handleListTools(req)
	case "tools/call":
		return s.handleCallTool(req)
	case "shutdown":
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Result:  map[string]interface{}{},
		}
	case "exit":
		os.Exit(0)
		return nil
	default:
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error: &Error{
				Code:    -32601,
				Message: "Method not found",
			},
		}
	}
}

func (s *Server) handleInitialize(req *Request) *Response {
	var params InitializeParams
	if req.Params != nil {
		if err := json.Unmarshal(req.Params, &params); err != nil {
			return &Response{
				JSONRPC: "2.0",
				ID:      req.ID,
				Error: &Error{
					Code:    -32602,
					Message: "Invalid params",
					Data:    err.Error(),
				},
			}
		}
	}

	result := InitializeResult{
		ProtocolVersion: "2024-11-05",
		Capabilities: ServerCapabilities{
			Tools: &ToolsCapability{
				ListChanged: boolPtr(false),
			},
		},
		ServerInfo: ServerInfo{
			Name:    "gcal-mcp-server",
			Version: "1.0.0",
		},
	}

	return &Response{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result:  result,
	}
}

func (s *Server) handleListTools(req *Request) *Response {
	tools := make([]Tool, 0, len(s.tools))
	for _, tool := range s.tools {
		tools = append(tools, tool)
	}

	result := ListToolsResult{
		Tools: tools,
	}

	return &Response{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result:  result,
	}
}

func (s *Server) handleCallTool(req *Request) *Response {
	var params CallToolParams
	if err := json.Unmarshal(req.Params, &params); err != nil {
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error: &Error{
				Code:    -32602,
				Message: "Invalid params",
				Data:    err.Error(),
			},
		}
	}

	if _, exists := s.tools[params.Name]; !exists {
		return &Response{
			JSONRPC: "2.0",
			ID:      req.ID,
			Error: &Error{
				Code:    -32602,
				Message: fmt.Sprintf("Unknown tool: %s", params.Name),
			},
		}
	}

	result, err := s.handler.HandleTool(params.Name, params.Arguments)
	if err != nil {
		isError := true
		result = &CallToolResult{
			Content: []ToolResult{{
				Type: "text",
				Text: fmt.Sprintf("Error: %v", err),
			}},
			IsError: &isError,
		}
	}

	return &Response{
		JSONRPC: "2.0",
		ID:      req.ID,
		Result:  result,
	}
}

func (s *Server) sendResponse(response *Response) error {
	data, err := json.Marshal(response)
	if err != nil {
		return err
	}

	_, err = fmt.Fprintln(os.Stdout, string(data))
	return err
}

func (s *Server) sendError(id interface{}, code int, message string, data interface{}) {
	response := &Response{
		JSONRPC: "2.0",
		ID:      id,
		Error: &Error{
			Code:    code,
			Message: message,
			Data:    data,
		},
	}
	s.sendResponse(response)
}

func boolPtr(b bool) *bool {
	return &b
}

func (s *Server) LogToStderr(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
}