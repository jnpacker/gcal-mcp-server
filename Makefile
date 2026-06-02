.PHONY: build clean test test-go test-python lint lint-go lint-python install auth fmt vet mod-tidy deps dev sync-commands

BINARY_NAME=gcal-mcp-server
BUILD_DIR=./bin

STATICCHECK := $(HOME)/go/bin/staticcheck

auth:
	rm -f token.json
	go run cmd/server/main.go

build:
	@mkdir -p $(BUILD_DIR)
	go build -o $(BUILD_DIR)/$(BINARY_NAME) cmd/server/main.go

install: build
	cp $(BUILD_DIR)/$(BINARY_NAME) /usr/local/bin/

clean:
	rm -rf $(BUILD_DIR)
	go clean

## Go tests
test-go:
	go test ./...

## Python TUI tests
test-python:
	cd calender && pip install -q -r requirements.txt && pytest . -v

## Run all tests
test: test-go test-python

## Go linting — go vet + staticcheck (installs staticcheck automatically if missing)
lint-go:
	go vet ./...
	@if [ ! -f "$(STATICCHECK)" ]; then \
		echo "Installing staticcheck..."; \
		go install honnef.co/go/tools/cmd/staticcheck@latest; \
	fi
	$(STATICCHECK) ./...

## Python linting — installs ruff automatically if missing
lint-python:
	@if ! python3 -c "import subprocess; subprocess.run(['ruff','--version'],capture_output=True,check=True)" 2>/dev/null; then \
		echo "Installing ruff..."; \
		pip install -q ruff; \
	fi
	python3 -m ruff check calender/

## Run all linters
lint: lint-go lint-python

fmt:
	go fmt ./...

vet:
	go vet ./...

mod-tidy:
	go mod tidy

deps: mod-tidy
	go mod download

dev: fmt vet lint test build

sync-commands:
	./scripts/sync-commands.sh

.DEFAULT_GOAL := build