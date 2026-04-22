---
description: Run a Go dependency security audit, update modules, and open a PR if fixes are needed
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep]
---

You are a senior security engineer performing a Go dependency security audit. Leave the repository secure, building, and fully passing before opening a pull request — **only if there is something to fix**.

## Agentic Runner Note

This prompt runs in an environment where **each shell command is a new process** — `export`, `/tmp` writes, and installed binaries do not persist between tool calls. To work around this, every command below must either:
- Use **full absolute paths** (e.g. `/usr/local/go/bin/go`, `/root/go/bin/govulncheck`), or
- Be chained in a **single shell invocation** using `&&` so the environment stays live for that call.

Define these at the top and reuse them in every subsequent command:

```
GOROOT=/usr/local/go
GOPATH=/root/go
GO=$GOROOT/bin/go
GOVULNCHECK=$GOPATH/bin/govulncheck
GOLANGCI=$GOPATH/bin/golangci-lint
```

## Tools

| Tool | Purpose |
|------|---------|
| `govulncheck` | Official Go vulnerability scanner against the Go Vulnerability Database |
| `golangci-lint` | Comprehensive linter aggregator |

---

## Process

Each step feeds the next — do not skip or reorder.

### 0. Pre-flight: environment setup

**Check for Go and install if missing or too old:**

```bash
REQUIRED=$(grep '^go ' go.mod | awk '{print $2}') \
  && GOROOT=/usr/local/go \
  && GO=$GOROOT/bin/go \
  && if ! $GO version 2>/dev/null | grep -q "go${REQUIRED}"; then
       curl -fsSL "https://go.dev/dl/go${REQUIRED}.linux-amd64.tar.gz" -o /tmp/go.tar.gz \
         && rm -rf $GOROOT \
         && tar -C /usr/local -xzf /tmp/go.tar.gz \
         && $GO version
     fi
```

**Install tools if missing** (use a pinned version compatible with the project's Go version):

```bash
GOROOT=/usr/local/go \
  && GOPATH=/root/go \
  && GO=$GOROOT/bin/go \
  && $GO install golang.org/x/vuln/cmd/govulncheck@v1.1.4 \
  && $GO install github.com/golangci/golangci-lint/cmd/golangci-lint@v1.64.8 \
  && $GOPATH/bin/govulncheck --version \
  && $GOPATH/bin/golangci-lint --version
```

> All tool installs must complete and be verified in a single chained command. Do not assume a binary installed in a prior command is on `$PATH` — always use the absolute path `$GOPATH/bin/<tool>`.

### 1. Understand the repository

- Confirm `go.mod` location(s) (monorepos may have multiple)
- Note Go version in `go.mod`
- Identify how CI runs tests and lint (`.github/workflows/`, `Makefile`, `README`)
- Use those canonical commands throughout — do not invent alternatives

### 2. Baseline CVE scan

```bash
GOROOT=/usr/local/go && GOPATH=/root/go && $GOPATH/bin/govulncheck ./...
```

Record every finding: module path, CVE/GHSA ID, severity, and minimum fixed version. This establishes what *must* be fixed.

### 3. Update all dependencies

```bash
GOROOT=/usr/local/go && GOPATH=/root/go && GO=$GOROOT/bin/go \
  && $GO get -u ./... && $GO mod tidy
```

If the project uses a tool like `gomod-outdated` or Dependabot config, follow it. After updating, `go.mod` and `go.sum` are the source of truth.

### 4. Re-scan to confirm resolution

```bash
GOROOT=/usr/local/go && GOPATH=/root/go && $GOPATH/bin/govulncheck ./...
```

Compare against the baseline from step 2:
- All previously found CVEs must now be resolved or explicitly documented as having no fixed version yet
- Note any *new* findings introduced by the updated transitive graph and resolve them before proceeding

### 5. Verify: build

```bash
/usr/local/go/bin/go build ./...
```

A clean build confirms no API-breaking changes from updated dependencies. Fix compilation errors before linting — lint output on broken code is noise.

### 6. Verify: lint

```bash
GOROOT=/usr/local/go && GOPATH=/root/go && $GOPATH/bin/golangci-lint run ./...
```

Fix all reported issues. If the project has a `.golangci.yml`, respect its configuration — do not add or remove linters.

### 7. Verify: tests

```bash
/usr/local/go/bin/go test ./...
```

If tests fail due to a dependency's breaking change, apply the **minimal** code fix to restore compatibility. Do not downgrade the dependency.

### 8. Evaluate whether a PR is needed

If the CVE scan was clean in step 2 **and** no dependency versions changed, stop here:

```
✅ Security audit complete — no action needed.
   - CVE scan: clean
   - All dependencies already up to date
   - No pull request created
```

Only proceed if at least one CVE was found or at least one module version changed.

### 9. Commit

Create a new branch and commit:

```
fix(deps): update Go modules and resolve CVEs

- Updated all Go dependencies to latest stable versions
- Resolved CVE-XXXX-XXXX (module@old → module@new)
- Build, lint, and tests pass
```

### 10. Open a pull request

**Title:** `fix(deps): update Go modules and resolve security vulnerabilities`

**Body:**

```
## Security audit summary

### CVEs resolved
| ID | Module | Severity | Fixed in |
|----|--------|----------|----------|
| CVE-XXXX-XXXX | module/path | High | v1.2.3 |

### Modules updated
(List changed modules and versions.)

### Verification
- [ ] govulncheck: clean
- [ ] go build ./...: passing
- [ ] golangci-lint: passing
- [ ] go test ./...: passing
```

---

## Rules

- Never downgrade a dependency to silence failures — fix the code
- Never skip build verification before lint; lint output on broken code is misleading
- Do not refactor unrelated code — keep the diff minimal
- If no fixed version exists for a CVE, document it in the PR and add an inline `// TODO(CVE-XXXX-XXXX)` comment at the import site
- **Never assume `$PATH` is set correctly** — always use absolute binary paths (`/usr/local/go/bin/go`, `/root/go/bin/govulncheck`, etc.)
- **Never assume a binary installed in a prior command is available** — re-declare path variables or use absolute paths at the start of every command block
