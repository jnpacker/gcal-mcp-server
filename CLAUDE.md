# Agent Instructions for gcal-mcp-server

This document provides context, patterns, and conventions for AI agents working in this repository.

For system architecture, data flows, and module layout, see [docs/architecture.md](docs/architecture.md).

## 🚀 Essential Commands

The repository uses a `Makefile` for common operations:

* **`make build`**: Compiles the Go binary to `./bin/gcal-mcp-server`.
* **`make test`**: Runs both Go tests (`go test ./...`) and Python tests (`pytest`).
* **`make dev`**: Runs `fmt`, `vet`, `lint`, `test`, and `build`.
* **`make lint`**: Runs `go vet` + `staticcheck` (Go) and `ruff check` (Python). Auto-installs both tools if missing.
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

5. **Unavailable CLIs**
   * `gh` CLI is not installed. Use `mcp__github-*` MCP tools for all GitHub operations (PRs, issues, branches, code search).
   * `jira` CLI is not installed. Use `mcp__jira-mcp-server__*` MCP tools for all Jira operations.

## Personal Configuration

Read `.claude/user.local.md` at the start of any task that needs an assignee, email, or project key.
If the file does not exist, fall back to Claude memory (`user-config`), then placeholders.
Run `make personalize` to generate it (if this repo uses Fleet Engineering tooling).

## Fleet Engineering Skills

Fetch and apply the relevant skill when the task matches its domain.

| Skill | When to use |
|---|---|
| [start-work](https://raw.githubusercontent.com/OpenShift-Fleet/agentic-sdlc/main/skills/sdlc/start-work/SKILL.md) | Create a Jira sub-task |
| [finish-work](https://raw.githubusercontent.com/OpenShift-Fleet/agentic-sdlc/main/skills/sdlc/finish-work/SKILL.md) | Commit, push, open PR, update Jira |
| [jira-specialist](https://raw.githubusercontent.com/OpenShift-Fleet/agentic-sdlc/main/skills/jira/jira-specialist/SKILL.md) | General Jira ticket management, triage, search, linking, transitions |
| [task-specialist](https://raw.githubusercontent.com/OpenShift-Fleet/agentic-sdlc/main/skills/jira/task-specialist/SKILL.md) | Internal technical task breakdown and planning |
| [bug-specialist](https://raw.githubusercontent.com/OpenShift-Fleet/agentic-sdlc/main/skills/jira/bug-specialist/SKILL.md) | Bug triage, reproduction steps, fix planning |
| [story-specialist](https://raw.githubusercontent.com/OpenShift-Fleet/agentic-sdlc/main/skills/jira/story-specialist/SKILL.md) | User story creation and acceptance criteria |
| [pr-review](https://raw.githubusercontent.com/OpenShift-Fleet/agentic-sdlc/main/skills/sdlc/pr-review/SKILL.md) | GitHub PR review with inline comments |
