# Development Guide

## Prerequisites

| Tool | Minimum version | Install |
|---|---|---|
| Go | 1.25 | https://go.dev/dl/ |
| Python | 3.12 | https://python.org |
| staticcheck | latest | `go install honnef.co/go/tools/cmd/staticcheck@latest` |
| ruff | latest | `pip install ruff` |

## Clone and build

```bash
git clone git@github.com:jnpacker/gcal-mcp-server.git
cd gcal-mcp-server
make build          # compiles to ./bin/gcal-mcp-server
```

## Google OAuth credentials

The server requires a `credentials.json` file from your Google Cloud project.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an OAuth 2.0 Client ID (Desktop application)
3. Download the JSON and place it at the repository root:
   ```bash
   cp ~/Downloads/client_secret_*.json ./credentials.json
   ```

On first run, the server opens a local HTTP server on `:8080` and prints an OAuth URL to stderr. Visit the URL, authorize, and the server saves `token.json` at the repo root.

To force re-authentication:
```bash
make auth    # removes token.json and starts the server
```

## Running the server

The server reads JSON-RPC from stdin and writes responses to stdout. Run it via an MCP client (Claude, Gemini, Cursor), or test it manually:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}}' \
  | ./bin/gcal-mcp-server
```

All server logs go to stderr:
```bash
./bin/gcal-mcp-server 2>server.log
```

## Running the Python TUI

```bash
cd calender
pip install -r requirements.txt
python3 calendar_tui.py --help
```

The TUI launches the MCP server binary as a subprocess. Make sure you've run `make build` first.

## Makefile targets

| Target | What it does |
|---|---|
| `make build` | Compile Go binary to `./bin/gcal-mcp-server` |
| `make test-go` | Run Go tests with coverage (`./internal/...`) |
| `make test-python` | Run Python tests with pytest |
| `make test` | Run both test suites |
| `make lint-go` | `go vet` + `staticcheck` (auto-installs staticcheck) |
| `make lint-python` | `ruff check calender/` (auto-installs ruff via pip) |
| `make lint` | Run both linters |
| `make dev` | `fmt` + `vet` + `lint` + `test` + `build` |
| `make fmt` | `go fmt ./...` |
| `make vet` | `go vet ./...` |
| `make mod-tidy` | `go mod tidy` |
| `make deps` | `mod-tidy` + `go mod download` |
| `make auth` | Remove `token.json` and start server for re-auth |
| `make sync-commands` | Sync AI command files across platforms |

## Adding a new MCP tool

1. Add a method to `Client` in `internal/calendar/client.go`
2. Register the tool in `internal/calendar/tools.go`:
   - Add a `Tool` definition (name, description, input schema)
   - Add a case in `HandleTool` that parses arguments and calls your new method
3. Register the tool in `cmd/server/main.go` via `server.RegisterTool(...)`
4. Write tests in `internal/calendar/client_test.go`

## Project layout

```
gcal-mcp-server/
├── .github/workflows/ci.yml   # GitHub Actions CI
├── .golangci.yml              # Go lint config
├── ruff.toml                  # Python lint config
├── Makefile
├── cmd/server/main.go         # Entry point
├── internal/
│   ├── auth/oauth.go          # Google OAuth
│   ├── calendar/
│   │   ├── client.go          # Calendar API client
│   │   ├── client_test.go
│   │   └── tools.go           # MCP tool definitions
│   └── mcp/
│       ├── server.go          # JSON-RPC server
│       ├── server_test.go
│       └── types.go           # MCP wire types
├── calender/                  # Note: intentional spelling
│   ├── calendar_tui.py        # Python curses TUI
│   ├── test_tui_ui.py         # UI tests (mocked curses)
│   ├── test_calendar_tui.py   # Integration tests
│   ├── test_filter.py
│   ├── requirements.txt
│   └── pytest.ini
└── docs/
    ├── architecture.md        # This repo's design
    ├── development.md         # (this file)
    ├── testing.md
    └── ci.md
```

## See also

- [architecture.md](architecture.md) — how the pieces fit together
- [testing.md](testing.md) — running and writing tests
- [ci.md](ci.md) — CI pipeline
