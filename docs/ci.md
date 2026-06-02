# CI (GitHub Actions)

CI runs automatically on every pull request to `main` and every push to `main`.

Workflow file: `.github/workflows/ci.yml`

## Jobs

| Job name | Makefile equivalent | What it runs |
|---|---|---|
| **Lint Go** | `make lint-go` | `go vet ./...` + `staticcheck ./...` |
| **Lint Python** | `make lint-python` | `ruff check calender/` |
| **Test Go (MCP)** | `make test-go` | `go test -cover ./internal/...` |
| **Test Python (gcal TUI)** | `make test-python` | `pytest calender/ -v` |

All four jobs run in parallel — wall clock time equals the slowest job, not the sum.

## Job details

### Lint Go

```yaml
- uses: actions/setup-go@v5
  with:
    go-version-file: go.mod   # reads the version from go.mod
    cache: true               # caches the Go module cache
- run: go install honnef.co/go/tools/cmd/staticcheck@latest
- run: go vet ./...
- run: staticcheck ./...
```

Uses the exact Go version declared in `go.mod`. Module downloads are cached between runs.

### Lint Python

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: pip
- run: pip install ruff
- run: ruff check calender/
```

Ruff config lives in `ruff.toml` at the repo root.

### Test Go (MCP)

```yaml
- uses: actions/setup-go@v5
  with:
    go-version-file: go.mod
    cache: true
- run: go test -cover ./internal/...
```

Scoped to `./internal/...` to avoid the `cmd/server` main package, which requires credential files to compile tests against the Google API.

### Test Python (gcal TUI)

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: pip
- run: pip install -r calender/requirements.txt pytest pytest-asyncio
- run: pytest calender/ -v
```

No credentials or display required — tests mock the curses screen and MCP client.

## Debugging CI failures locally

Every CI command maps 1:1 to a Makefile target. Reproduce any failure locally:

```bash
make lint-go       # debug lint-go failures
make lint-python   # debug lint-python failures
make test-go       # debug test-go failures
make test-python   # debug test-python failures
```

### Common issues

**`staticcheck: command not found`**
Install it: `go install honnef.co/go/tools/cmd/staticcheck@latest`

**`ruff: command not found`**
Install it: `pip install ruff` (or `make lint-python` auto-installs it)

**`must call initscr() first` in Python tests**
You're running the TUI code outside the curses mock context. Make sure you're using `make_tui()` from `test_tui_ui.py` or patching `curses.curs_set` and friends.

**Go version mismatch (`go1.24 lower than targeted go1.25`)**
This error appears when `golangci-lint` (built with Go 1.24) runs against a module targeting Go 1.25. The CI workflow uses `staticcheck` instead, which supports the current Go version.

## See also

- [development.md](development.md) — local Makefile targets reference
- [testing.md](testing.md) — test suite design and constraints
