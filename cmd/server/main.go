// Copyright 2024 Red Hat, Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// This code was developed with AI assistance.

package main

import (
	"log"

	"gcal-mcp-server/internal/auth"
	"gcal-mcp-server/internal/calendar"
	"gcal-mcp-server/internal/mcp"
)

func main() {
	// Setup Google Calendar service
	calendarService, err := auth.GetCalendarService()
	if err != nil {
		log.Fatalf("Unable to retrieve Calendar client: %v", err)
	}

	// Create calendar client and tools
	calendarClient := calendar.NewClient(calendarService)
	calendarTools := calendar.NewCalendarTools(calendarClient)

	// Create MCP server
	server := mcp.NewServer(calendarTools)

	// Register all tools
	for _, tool := range calendarTools.GetTools() {
		server.RegisterTool(tool)
	}

	// Log server startup to stderr
	server.LogToStderr("Google Calendar MCP Server starting...")
	server.LogToStderr("Available tools: create_event, edit_event, delete_event, search_attendees, get_attendee_freebusy, list_events, detect_overlaps")

	// Run the server
	if err := server.Run(); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
