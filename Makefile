.PHONY: build clean test install

BINARY_NAME=gcal-mcp-server
BUILD_DIR=./bin

build:
	@mkdir -p $(BUILD_DIR)
	go build -o $(BUILD_DIR)/$(BINARY_NAME) cmd/server/main.go

install: build
	cp $(BUILD_DIR)/$(BINARY_NAME) /usr/local/bin/

clean:
	rm -rf $(BUILD_DIR)
	go clean

test:
	go test ./...

fmt:
	go fmt ./...

vet:
	go vet ./...

mod-tidy:
	go mod tidy

deps: mod-tidy
	go mod download

dev: fmt vet test build

prompt:
	cp gcal-assistant-prompt.md CLAUDE.md
	cp gcal-assistant-prompt.md GEMINI.md

.DEFAULT_GOAL := build