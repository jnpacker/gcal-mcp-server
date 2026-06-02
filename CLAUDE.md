# Agent Instructions for gcal-mcp-server

This document provides context, patterns, and conventions for AI agents working in this repository.

## 🏗️ Architecture & Organization

This is a Model Context Protocol (MCP) server written in Go that integrates with Google Calendar and Google Drive APIs. 

### Core Components
* **`cmd/server/main.go`**: The entry point. Initializes services, registers tools, and starts the MCP server.
* **`internal/mcp/`**: Implements the Model Context Protocol (JSON-RPC over stdin/stdout).
* **`internal/calendar/`**: Contains the core logic for Google Calendar API interactions (`client.go`) and the MCP tool definitions (`tools.go`).
* **`internal/auth/`**: Handles Google OAuth 2.0 authentication and token management.
* **`scripts/`**: Contains scripts for syncing AI command prompts (`sync-commands.sh`, `sync_commands.py`).
* **`calender/`**: (Note the spelling) Contains a Python-based Terminal UI for calendar management (`calendar_tui.py`) and its tests.

## 🚀 Essential Commands

The repository uses a `Makefile` for common operations:

* **`make build`**: Compiles the Go binary to `./bin/gcal-mcp-server`.
* **`make test`**: Runs the Go test suite (`go test ./...`). There are also Python tests in `calender/` that run via `pytest`.
* **`make dev`**: Runs `fmt`, `vet`, `test`, and `build`.
* **`make auth`**: Removes the local `token.json` and runs the server to force a new Google OAuth flow.
* **`make sync-commands`**: Runs the script to synchronize AI prompt files across `.claude`, `.gemini`, and `.cursor` directories.

## ⚠️ Important Patterns & Gotchas

1. **Logging vs. Standard Output (CRITICAL)**
   * **Never write to `stdout` for logging.** Because this is an MCP server, `stdout` is exclusively reserved for the JSON-RPC protocol messages.
   * Any debug information, logs, or error messages *must* be written to `os.Stderr`. Use `server.LogToStderr()` or `fmt.Fprintf(os.Stderr, ...)` when adding logs.

2. **Credential Discovery**
   * The server requires Google OAuth credentials (`credentials.json`) and stores an auth token (`token.json`).
   * It is designed to find these files at the repository root automatically (detecting `go.mod` or `.git`), with the current working directory as a fallback.

3. **AI Command Synchronization**
   * Instead of a single system prompt, this project provides tailored command instructions for different AI platforms (Claude, Gemini, Cursor).
   * These commands live in platform-specific hidden directories (`.claude/commands/`, etc.). 
   * When modifying commands or prompts, update the source of truth and use `make sync-commands` to propagate changes across platforms.

4. **Typo in Directory Name**
   * The Python component is located in `calender/`, not `calendar/`. Be careful with path autocomplete.
