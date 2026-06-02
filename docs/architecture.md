# Architecture

## Overview

`gcal-mcp-server` is a [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server written in Go. It bridges AI assistants (Claude, Gemini, Cursor) with the Google Calendar and Google Drive APIs, exposing calendar operations as MCP tools.

It also ships a separate Python terminal UI (`calender/calendar_tui.py`) for interactive calendar management directly in the terminal.

```
AI Assistant (Claude / Gemini / Cursor)
        │ JSON-RPC over stdin/stdout
        ▼
┌─────────────────────────────────────┐
│         gcal-mcp-server (Go)        │
│                                     │
│  cmd/server/main.go  (entry point)  │
│         │                           │
│  internal/mcp/       (MCP protocol) │
│  internal/calendar/  (API client)   │
│  internal/auth/      (OAuth)        │
└──────────────┬──────────────────────┘
               │ HTTPS
               ▼
    Google Calendar API
    Google Drive API
```

## Go MCP Server

### `cmd/server/main.go`

Entry point. Wires up:
1. `auth.GetCalendarService()` and `auth.GetDriveService()` — authenticated API clients
2. `calendar.NewClient(...)` — wraps the API clients
3. `calendar.NewCalendarTools(client)` — implements `mcp.ToolHandler`
4. `mcp.NewServer(tools)` — JSON-RPC server
5. Registers all tools, then calls `server.Run()` which reads from `os.Stdin`

**Critical constraint:** stdout is exclusively for JSON-RPC. All logging must go to `os.Stderr`. Never write to stdout from any non-protocol path.

### `internal/mcp/`

Implements the MCP JSON-RPC protocol (version `2024-11-05`).

- **`server.go`**: `Server` struct reads lines from stdin, dispatches methods (`initialize`, `tools/list`, `tools/call`, `shutdown`, `exit`), writes responses to stdout.
- **`types.go`**: All MCP wire types — `Request`, `Response`, `Tool`, `CallToolResult`, etc.

The `ToolHandler` interface decouples the protocol layer from the calendar logic:

```go
type ToolHandler interface {
    HandleTool(name string, arguments map[string]interface{}) (*CallToolResult, error)
}
```

### `internal/calendar/`

- **`client.go`**: `Client` struct wrapping `*calendar.Service` and `*drive.Service`. Provides all calendar operations: `CreateEvent`, `PatchEvent`, `DeleteEvent`, `GetEvent`, `ListEvents`, `GetFreeBusy`, `DetectOverlaps`, `SearchAttendees`, `GetDocument`, `GetMeetingContext`, `SetWorkingLocation`.
- **`tools.go`**: `CalendarTools` implements `mcp.ToolHandler`. Each MCP tool call is parsed from `map[string]interface{}` arguments, delegated to a `Client` method, and formatted as a `CallToolResult`.

### `internal/auth/`

- **`oauth.go`**: Handles Google OAuth 2.0. Discovers credentials by walking up the directory tree from the compiled binary's location, looking for `go.mod` or `.git`. Falls back to the current working directory. On first run, opens a local HTTP server on `:8080` for the OAuth callback.

Token refresh is automatic. Tokens within 5 minutes of expiry are refreshed before use.

## Python gcal TUI

Located in `calender/` (note the spelling — not `calendar/`).

- **`calendar_tui.py`**: A raw `curses` terminal UI. Not a Textual app. Uses an `asyncio` event loop for non-blocking MCP tool calls while the `curses` screen renders synchronously.
  - `MCPClient`: async client that spawns the MCP server binary as a subprocess and communicates via stdio.
  - `CalendarEvent`: data model for a single event, with rendering helpers (`get_time_str`, `get_response_char`, `is_currently_active`, etc.).
  - `CalendarTUI`: main application class. Owns the event loop, key handling (`handle_navigation`), display mode switching, available-slot insertion, and all `curses` rendering.

The TUI and the MCP server are two independent processes — the TUI launches the server as a subprocess; the server does not know about the TUI.

## Data flow: listing events

```
User presses 'r' in TUI
  → CalendarTUI.fetch_events()
    → MCPClient.call_tool("list_events", {...})
      → stdin/stdout pipe to gcal-mcp-server binary
        → CalendarTools.HandleTool("list_events", args)
          → Client.ListEvents(params)
            → Google Calendar API
          ← []calendar.Event
        ← CallToolResult{Content: [{Type:"text", Text: JSON}]}
      ← dict parsed from JSON
    ← list of CalendarEvent objects
  → TUI re-renders
```

## Credential discovery

```
findRepositoryRoot()  (walks up from binary location)
  → finds go.mod or .git
  → returns repo root
getCredentialPaths()
  → credentials.json at repo root  (or CWD as fallback)
  → token.json at repo root        (or CWD as fallback)
```

## See also

- [development.md](development.md) — how to build and run locally
- [testing.md](testing.md) — how to run the test suite
- [ci.md](ci.md) — GitHub Actions CI overview
