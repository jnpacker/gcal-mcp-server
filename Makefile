.PHONY: build clean test install auth

BINARY_NAME=gcal-mcp-server
BUILD_DIR=./bin

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

sync-commands:
	./scripts/sync-commands.sh

.DEFAULT_GOAL := build