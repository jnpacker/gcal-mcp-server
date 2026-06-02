# Testing

## Quick start

```bash
make test          # Go + Python tests
make test-go       # Go tests only (with coverage)
make test-python   # Python tests only
```

## Go tests

```bash
go test -cover ./internal/...
```

Tests live alongside the code they test (`*_test.go` in each package):

| File | What it tests |
|---|---|
| `internal/mcp/server_test.go` | JSON-RPC dispatch, tool registration, stdout/stderr output |
| `internal/calendar/client_test.go` | `calculateTimeRange`, `eventsOverlap`, `parseEventTimes`, `DetectOverlaps`, `SearchAttendees`, `isValidEmail`, `parseFileID` |
| `internal/auth/oauth_test.go` | `isTokenValid`, `findRepositoryRoot`, `getCredentialPaths`, `generateStateToken` |

### Design constraints

All Go tests run offline — no Google credentials required:

- MCP tests use a `mockHandler` that implements `ToolHandler` without hitting the calendar API
- Calendar tests exercise pure utility functions (`calculateTimeRange`, `eventsOverlap`, etc.) that take plain inputs
- `DetectOverlaps` and `SearchAttendees` take plain `[]*calendar.Event` inputs and don't call the network
- Auth tests cover token validity logic and filesystem path discovery; the OAuth web flow is not tested (it requires a browser)

Methods like `CreateEvent`, `ListEvents`, and `GetDocument` are not unit-tested because they require a live `*calendar.Service`. Full end-to-end coverage requires real credentials and is outside the scope of the automated test suite.

### Coverage

```
internal/mcp      ~69%   (all dispatch paths covered; Run() requires stdin)
internal/calendar  ~8%   (utility functions; API methods need service injection)
internal/auth     ~15%   (token logic, path discovery; OAuth flow needs network)
```

To see a per-function breakdown:

```bash
go test -coverprofile=cov.out ./internal/...
go tool cover -func=cov.out
```

To view as HTML:

```bash
go tool cover -html=cov.out
```

## Python tests

```bash
pytest calender/ -v
```

Tests are in `calender/`:

| File | What it tests |
|---|---|
| `test_tui_ui.py` | `CalendarTUI` business logic and navigation with mocked curses |
| `test_calendar_tui.py` | `CalendarEvent` data model, MCP integration scenarios |
| `test_filter.py` | Day filter parsing |

### Design constraints

The TUI uses raw `curses` (not Textual), so the Textual `App.run_test()` harness does not apply. Tests in `test_tui_ui.py` instead:

1. **Mock `curses.stdscr`** — a `MagicMock` that reports a fixed terminal size and records all `addstr`/`addch` calls
2. **Mock `curses` setup calls** — `curses.start_color`, `curses.curs_set`, `curses.init_pair`, etc. are patched to avoid the `must call initscr() first` error
3. **Mock `MCPClient`** — all tool calls return empty dicts; no subprocess or network is required

This allows testing:
- `CalendarEvent` creation and data model correctness
- `get_filtered_events` across all three display modes
- `handle_navigation` (KEY_UP / KEY_DOWN) with scroll offset management
- Edge cases: empty event list, text wrapping, loading state, recommendation validity

### Async tests

`pytest.ini` sets `asyncio_mode = auto`, so async test functions are collected and run automatically with `pytest-asyncio`.

### Running a subset

```bash
pytest calender/test_tui_ui.py -v -k "navigation"   # navigation tests only
pytest calender/test_tui_ui.py::TestCalendarEvent    # one class
pytest calender/ -q                                   # quiet mode
```

## See also

- [architecture.md](architecture.md) — why the code is structured the way it is
- [development.md](development.md) — how to build and run locally
- [ci.md](ci.md) — how CI runs these tests automatically
