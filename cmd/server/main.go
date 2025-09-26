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
	server.LogToStderr("Available tools: create_event, edit_event, delete_event, search_attendees, get_attendee_freebusy, list_events")

	// Run the server
	if err := server.Run(); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}