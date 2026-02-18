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

package calendar

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"gcal-mcp-server/internal/mcp"

	"google.golang.org/api/calendar/v3"
)

type CalendarTools struct {
	client *Client
}

func NewCalendarTools(client *Client) *CalendarTools {
	return &CalendarTools{
		client: client,
	}
}

func (ct *CalendarTools) GetTools() []mcp.Tool {
	return []mcp.Tool{
		{
			Name:        "create_event",
			Description: "Create a new calendar event with comprehensive options. Supports all-day events, recurring events, conference data, reminders, and guest permissions.",
			InputSchema: mcp.ToolSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"calendar_id": map[string]interface{}{
						"type":        "string",
						"description": "Calendar ID (defaults to 'primary' for user's main calendar)",
						"default":     "primary",
					},
					"summary": map[string]interface{}{
						"type":        "string",
						"description": "Event title/summary (REQUIRED)",
					},
					"description": map[string]interface{}{
						"type":        "string",
						"description": "Event description/details (RECOMMENDED)",
					},
					"location": map[string]interface{}{
						"type":        "string",
						"description": "Event location (RECOMMENDED for in-person events)",
					},
					"start_time": map[string]interface{}{
						"type":        "string",
						"description": "Event start time in RFC3339 format (REQUIRED). Example: '2024-01-15T10:00:00-08:00'",
					},
					"end_time": map[string]interface{}{
						"type":        "string",
						"description": "Event end time in RFC3339 format (REQUIRED). Example: '2024-01-15T11:00:00-08:00'",
					},
					"timezone": map[string]interface{}{
						"type":        "string",
						"description": "Time zone for the event (defaults to system timezone). Example: 'America/New_York'",
						"default":     "UTC",
					},
					"all_day": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether this is an all-day event (defaults to false)",
						"default":     false,
					},
					"attendees": map[string]interface{}{
						"type": "array",
						"items": map[string]interface{}{
							"type": "string",
						},
						"description": "List of attendee email addresses (RECOMMENDED for meetings)",
					},
					"recurrence": map[string]interface{}{
						"type": "array",
						"items": map[string]interface{}{
							"type": "string",
						},
						"description": "Recurrence rules in RRULE format. Example: ['RRULE:FREQ=DAILY;COUNT=10'] for daily for 10 days",
					},
					"visibility": map[string]interface{}{
						"type":        "string",
						"description": "Event visibility: 'default', 'public', 'private', 'confidential'",
						"enum":        []string{"default", "public", "private", "confidential"},
						"default":     "default",
					},
					"send_notifications": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether to send email notifications to attendees (defaults to true)",
						"default":     true,
					},
					"guest_can_modify": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether guests can modify the event (defaults to false)",
						"default":     false,
					},
					"guest_can_invite_others": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether guests can invite other people (defaults to true)",
						"default":     true,
					},
					"guest_can_see_other_guests": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether guests can see other guests (defaults to true)",
						"default":     true,
					},
					"create_meet_link": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether to create a Google Meet link for the event (defaults to false)",
						"default":     false,
					},
					"reminders": map[string]interface{}{
						"type": "object",
						"properties": map[string]interface{}{
							"use_default": map[string]interface{}{
								"type":        "boolean",
								"description": "Use default calendar reminders",
								"default":     true,
							},
							"overrides": map[string]interface{}{
								"type": "array",
								"items": map[string]interface{}{
									"type": "object",
									"properties": map[string]interface{}{
										"method": map[string]interface{}{
											"type":        "string",
											"enum":        []string{"email", "popup"},
											"description": "Reminder method",
										},
										"minutes": map[string]interface{}{
											"type":        "integer",
											"description": "Minutes before event to send reminder",
										},
									},
									"required": []string{"method", "minutes"},
								},
								"description": "Custom reminder overrides",
							},
						},
						"description": "Event reminder settings",
					},
					"colorId": map[string]interface{}{
						"type":        "string",
						"description": "Event color ID (string). Use standard IDs like '1', '2', '3', etc. for different colors",
					},
					"eventType": map[string]interface{}{
						"type":        "string",
						"description": "Event type: 'default' (normal event), 'focusTime' (dedicated work blocks), 'workingLocation' (location indicators)",
						"enum":        []string{"default", "focusTime", "workingLocation"},
						"default":     "default",
					},
					"workingLocation": map[string]interface{}{
						"type": "object",
						"properties": map[string]interface{}{
							"type": map[string]interface{}{
								"type":        "string",
								"description": "Working location type: 'homeOffice', 'officeLocation', or 'customLocation'",
								"enum":        []string{"homeOffice", "officeLocation", "customLocation"},
							},
							"label": map[string]interface{}{
								"type":        "string",
								"description": "Custom label for the working location",
							},
						},
						"description": "Working location settings (only used when eventType is 'workingLocation')",
					},
					"focusTimeProperties": map[string]interface{}{
						"type": "object",
						"properties": map[string]interface{}{
							"autoDeclineMode": map[string]interface{}{
								"type":        "string",
								"description": "Auto-decline mode for focus time: 'declineNone', 'declineAllConflictingInvitations', 'declineOnlyNewConflictingInvitations' (default)",
								"enum":        []string{"declineNone", "declineAllConflictingInvitations", "declineOnlyNewConflictingInvitations"},
								"default":     "declineOnlyNewConflictingInvitations",
							},
							"chatStatus": map[string]interface{}{
								"type":        "string",
								"description": "Chat status during focus time: 'available' or 'doNotDisturb' (default)",
								"enum":        []string{"available", "doNotDisturb"},
								"default":     "doNotDisturb",
							},
							"declineMessage": map[string]interface{}{
								"type":        "string",
								"description": "Custom message for declined meetings (optional, default message will be used if not provided)",
							},
						},
						"description": "Focus time properties (only used when eventType is 'focusTime')",
					},
				},
				Required: []string{"summary", "start_time", "end_time"},
			},
		},
		{
			Name:        "edit_event",
			Description: "Edit an existing calendar event. All parameters are optional - only provided parameters will be updated. Supports RSVP responses (accept, decline, tentative) for meeting invitations.",
			InputSchema: mcp.ToolSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"calendar_id": map[string]interface{}{
						"type":        "string",
						"description": "Calendar ID (defaults to 'primary')",
						"default":     "primary",
					},
					"event_id": map[string]interface{}{
						"type":        "string",
						"description": "Event ID to edit (REQUIRED)",
					},
					"summary": map[string]interface{}{
						"type":        "string",
						"description": "New event title/summary",
					},
					"description": map[string]interface{}{
						"type":        "string",
						"description": "New event description/details",
					},
					"location": map[string]interface{}{
						"type":        "string",
						"description": "New event location",
					},
					"start_time": map[string]interface{}{
						"type":        "string",
						"description": "New start time in RFC3339 format",
					},
					"end_time": map[string]interface{}{
						"type":        "string",
						"description": "New end time in RFC3339 format",
					},
					"timezone": map[string]interface{}{
						"type":        "string",
						"description": "Time zone for the event",
					},
					"all_day": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether this is an all-day event",
					},
					"attendees": map[string]interface{}{
						"type": "array",
						"items": map[string]interface{}{
							"oneOf": []map[string]interface{}{
								{
									"type":        "string",
									"description": "Attendee email address (backward compatibility)",
								},
								{
									"type": "object",
									"properties": map[string]interface{}{
										"email": map[string]interface{}{
											"type":        "string",
											"description": "Attendee email address",
										},
										"response_status": map[string]interface{}{
											"type":        "string",
											"description": "RSVP response status: 'accepted', 'declined', 'tentative', 'needsAction'",
											"enum":        []string{"accepted", "declined", "tentative", "needsAction"},
											"default":     "needsAction",
										},
									},
									"required": []string{"email"},
								},
							},
						},
						"description": "New list of attendees (replaces existing). Can be email strings or objects with email and response_status",
					},
					"send_notifications": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether to send email notifications to attendees",
						"default":     true,
					},
					"colorId": map[string]interface{}{
						"type":        "string",
						"description": "Event color ID (string). Use standard IDs like '1', '2', '3', etc. for different colors",
					},
					"eventType": map[string]interface{}{
						"type":        "string",
						"description": "Event type: 'default' (normal event), 'focusTime' (dedicated work blocks), 'workingLocation' (location indicators)",
						"enum":        []string{"default", "focusTime", "workingLocation"},
					},
					"workingLocation": map[string]interface{}{
						"type": "object",
						"properties": map[string]interface{}{
							"type": map[string]interface{}{
								"type":        "string",
								"description": "Working location type: 'homeOffice', 'officeLocation', or 'customLocation'",
								"enum":        []string{"homeOffice", "officeLocation", "customLocation"},
							},
							"label": map[string]interface{}{
								"type":        "string",
								"description": "Custom label for the working location",
							},
						},
						"description": "Working location settings (only used when eventType is 'workingLocation')",
					},
				},
				Required: []string{"event_id"},
			},
		},
		{
			Name:        "delete_event",
			Description: "Delete a calendar event permanently.",
			InputSchema: mcp.ToolSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"calendar_id": map[string]interface{}{
						"type":        "string",
						"description": "Calendar ID (defaults to 'primary')",
						"default":     "primary",
					},
					"event_id": map[string]interface{}{
						"type":        "string",
						"description": "Event ID to delete (REQUIRED)",
					},
					"send_notifications": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether to send cancellation notifications to attendees",
						"default":     true,
					},
				},
				Required: []string{"event_id"},
			},
		},
		{
			Name:        "get_calendar_colors",
			Description: "Get available calendar and event colors with their IDs and names/labels.",
			InputSchema: mcp.ToolSchema{
				Type:       "object",
				Properties: map[string]interface{}{},
				Required:   []string{},
			},
		},
		{
			Name:        "search_attendees",
			Description: "Search for potential attendees. Note: This is a simplified implementation that validates email format.",
			InputSchema: mcp.ToolSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"query": map[string]interface{}{
						"type":        "string",
						"description": "Search query (email address or name) (REQUIRED)",
					},
					"max_results": map[string]interface{}{
						"type":        "integer",
						"description": "Maximum number of results to return",
						"default":     10,
					},
					"domain": map[string]interface{}{
						"type":        "string",
						"description": "Limit search to specific domain (e.g., 'company.com')",
					},
				},
				Required: []string{"query"},
			},
		},
		{
			Name:        "get_attendee_freebusy",
			Description: "Check free/busy status for attendees during a specific time period.",
			InputSchema: mcp.ToolSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"attendee_emails": map[string]interface{}{
						"type": "array",
						"items": map[string]interface{}{
							"type": "string",
						},
						"description": "List of attendee email addresses to check (REQUIRED)",
					},
					"time_min": map[string]interface{}{
						"type":        "string",
						"description": "Start time for free/busy query in RFC3339 format (REQUIRED)",
					},
					"time_max": map[string]interface{}{
						"type":        "string",
						"description": "End time for free/busy query in RFC3339 format (REQUIRED)",
					},
					"timezone": map[string]interface{}{
						"type":        "string",
						"description": "Time zone for the query (defaults to UTC)",
						"default":     "UTC",
					},
				},
				Required: []string{"attendee_emails", "time_min", "time_max"},
			},
		},
		{
			Name:        "list_events",
			Description: "List calendar events with comprehensive filtering options. Supports predefined time filters (today, this_week, next_week) and custom time ranges.",
			InputSchema: mcp.ToolSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"calendar_id": map[string]interface{}{
						"type":        "string",
						"description": "Calendar ID (defaults to 'primary' for user's main calendar)",
						"default":     "primary",
					},
					"time_filter": map[string]interface{}{
						"type":        "string",
						"description": "Time filter for events. Options: 'today', 'this_week' (Mon-Fri), 'next_week' (Mon-Fri), 'custom' (requires time_min and time_max)",
						"enum":        []string{"today", "this_week", "next_week", "custom"},
						"default":     "today",
					},
					"time_min": map[string]interface{}{
						"type":        "string",
						"description": "Start time for custom time range in RFC3339 format (required if time_filter is 'custom')",
					},
					"time_max": map[string]interface{}{
						"type":        "string",
						"description": "End time for custom time range in RFC3339 format (required if time_filter is 'custom')",
					},
					"timezone": map[string]interface{}{
						"type":        "string",
						"description": "Time zone for the query (defaults to UTC). Example: 'America/New_York'",
						"default":     "UTC",
					},
					"max_results": map[string]interface{}{
						"type":        "integer",
						"description": "Maximum number of events to return (defaults to 250)",
						"default":     250,
					},
					"show_deleted": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether to include deleted events (defaults to false)",
						"default":     false,
					},
					"order_by": map[string]interface{}{
						"type":        "string",
						"description": "Order of events. Options: 'startTime', 'updated' (defaults to 'startTime')",
						"enum":        []string{"startTime", "updated"},
						"default":     "startTime",
					},
					"show_declined": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether to include events that you have declined (defaults to false)",
						"default":     false,
					},
					"detect_overlaps": map[string]interface{}{
						"type":        "boolean",
						"description": "Whether to detect and mark overlapping events with has_overlap field (defaults to true)",
						"default":     true,
					},
					"output_format": map[string]interface{}{
						"type":        "string",
						"description": "Output format: 'text' for formatted display, 'json' for raw JSON data (defaults to 'text')",
						"enum":        []string{"text", "json"},
						"default":     "text",
					},
				},
				Required: []string{},
			},
		},
	}
}

func (ct *CalendarTools) HandleTool(name string, arguments map[string]interface{}) (*mcp.CallToolResult, error) {
	switch name {
	case "create_event":
		return ct.handleCreateEvent(arguments)
	case "edit_event":
		return ct.handleEditEvent(arguments)
	case "delete_event":
		return ct.handleDeleteEvent(arguments)
	case "get_calendar_colors":
		return ct.handleGetCalendarColors(arguments)
	case "search_attendees":
		return ct.handleSearchAttendees(arguments)
	case "get_attendee_freebusy":
		return ct.handleGetAttendeeFreeBusy(arguments)
	case "list_events":
		return ct.handleListEvents(arguments)
	default:
		return nil, fmt.Errorf("unknown tool: %s", name)
	}
}

func (ct *CalendarTools) handleCreateEvent(arguments map[string]interface{}) (*mcp.CallToolResult, error) {
	params, err := ct.parseEventParams(arguments)
	if err != nil {
		return nil, fmt.Errorf("invalid parameters: %v", err)
	}

	// Handle conference data creation
	if createMeet, ok := arguments["create_meet_link"].(bool); ok && createMeet {
		params.ConferenceData = &ConferenceDataParams{
			CreateRequest: &CreateConferenceRequest{
				RequestID: fmt.Sprintf("meet-%d", time.Now().Unix()),
				ConferenceSolution: &ConferenceSolution{
					Type: "hangoutsMeet",
				},
			},
		}
	}

	event, err := ct.client.CreateEvent(params)
	if err != nil {
		return nil, fmt.Errorf("failed to create event: %v", err)
	}

	result := ct.formatEventResult(event)

	return &mcp.CallToolResult{
		Content: []mcp.ToolResult{{
			Type: "text",
			Text: result,
		}},
	}, nil
}

func (ct *CalendarTools) handleEditEvent(arguments map[string]interface{}) (*mcp.CallToolResult, error) {
	eventID, ok := arguments["event_id"].(string)
	if !ok || eventID == "" {
		return nil, fmt.Errorf("event_id is required")
	}

	calendarID := getStringOrDefault(arguments, "calendar_id", "primary")

	// First, fetch the event to get its title for better error messages
	existingEvent, err := ct.client.GetEvent(calendarID, eventID)
	if err != nil {
		return nil, fmt.Errorf("failed to get event details: %v", err)
	}

	eventTitle := existingEvent.Summary
	if eventTitle == "" {
		eventTitle = "(No Title)"
	}

	params, err := ct.parsePatchEventParams(arguments)
	if err != nil {
		return nil, fmt.Errorf("invalid parameters for event '%s': %v", eventTitle, err)
	}

	event, err := ct.client.PatchEventDirect(eventID, params)
	if err != nil {
		return nil, fmt.Errorf("failed to patch event '%s': %v", eventTitle, err)
	}

	result := ct.formatEventResult(event)

	return &mcp.CallToolResult{
		Content: []mcp.ToolResult{{
			Type: "text",
			Text: result,
		}},
	}, nil
}

func (ct *CalendarTools) handleDeleteEvent(arguments map[string]interface{}) (*mcp.CallToolResult, error) {
	eventID, ok := arguments["event_id"].(string)
	if !ok || eventID == "" {
		return nil, fmt.Errorf("event_id is required")
	}

	calendarID := getStringOrDefault(arguments, "calendar_id", "primary")
	sendNotifications := getBoolOrDefault(arguments, "send_notifications", true)

	// First, fetch the event to get its title for better messages
	existingEvent, err := ct.client.GetEvent(calendarID, eventID)
	if err != nil {
		return nil, fmt.Errorf("failed to get event details: %v", err)
	}

	eventTitle := existingEvent.Summary
	if eventTitle == "" {
		eventTitle = "(No Title)"
	}

	err = ct.client.DeleteEvent(calendarID, eventID, sendNotifications)
	if err != nil {
		return nil, fmt.Errorf("failed to delete event '%s': %v", eventTitle, err)
	}

	result := fmt.Sprintf("✅ Event '%s' deleted successfully", eventTitle)
	if sendNotifications {
		result += " (cancellation notifications sent to attendees)"
	}

	return &mcp.CallToolResult{
		Content: []mcp.ToolResult{{
			Type: "text",
			Text: result,
		}},
	}, nil
}

func (ct *CalendarTools) handleGetCalendarColors(arguments map[string]interface{}) (*mcp.CallToolResult, error) {
	colors, err := ct.client.GetCalendarColors()
	if err != nil {
		return nil, fmt.Errorf("failed to get calendar colors: %v", err)
	}

	result := ct.formatColorsResult(colors)

	return &mcp.CallToolResult{
		Content: []mcp.ToolResult{{
			Type: "text",
			Text: result,
		}},
	}, nil
}

func (ct *CalendarTools) handleSearchAttendees(arguments map[string]interface{}) (*mcp.CallToolResult, error) {
	query, ok := arguments["query"].(string)
	if !ok || query == "" {
		return nil, fmt.Errorf("query is required")
	}

	params := AttendeeSearchParams{
		Query:      query,
		MaxResults: getIntOrDefault(arguments, "max_results", 10),
		Domain:     getStringOrDefault(arguments, "domain", ""),
	}

	attendees, err := ct.client.SearchAttendees(params)
	if err != nil {
		return nil, fmt.Errorf("failed to search attendees: %v", err)
	}

	var result strings.Builder
	result.WriteString(fmt.Sprintf("🔍 Attendee search results for '%s':\n\n", query))

	if len(attendees) == 0 {
		result.WriteString("No attendees found. Please provide full email addresses.")
	} else {
		for i, email := range attendees {
			result.WriteString(fmt.Sprintf("%d. %s\n", i+1, email))
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.ToolResult{{
			Type: "text",
			Text: result.String(),
		}},
	}, nil
}

func (ct *CalendarTools) handleGetAttendeeFreeBusy(arguments map[string]interface{}) (*mcp.CallToolResult, error) {
	attendeesInterface, ok := arguments["attendee_emails"]
	if !ok {
		return nil, fmt.Errorf("attendee_emails is required")
	}

	attendeesSlice, ok := attendeesInterface.([]interface{})
	if !ok {
		return nil, fmt.Errorf("attendee_emails must be an array")
	}

	attendees := make([]string, len(attendeesSlice))
	for i, v := range attendeesSlice {
		if email, ok := v.(string); ok {
			attendees[i] = email
		} else {
			return nil, fmt.Errorf("all attendee emails must be strings")
		}
	}

	timeMinStr, ok := arguments["time_min"].(string)
	if !ok || timeMinStr == "" {
		return nil, fmt.Errorf("time_min is required")
	}

	timeMaxStr, ok := arguments["time_max"].(string)
	if !ok || timeMaxStr == "" {
		return nil, fmt.Errorf("time_max is required")
	}

	timeMin, err := time.Parse(time.RFC3339, timeMinStr)
	if err != nil {
		return nil, fmt.Errorf("invalid time_min format: %v", err)
	}

	timeMax, err := time.Parse(time.RFC3339, timeMaxStr)
	if err != nil {
		return nil, fmt.Errorf("invalid time_max format: %v", err)
	}

	params := FreeBusyParams{
		TimeMin:     timeMin,
		TimeMax:     timeMax,
		TimeZone:    getStringOrDefault(arguments, "timezone", "UTC"),
		CalendarIDs: attendees,
	}

	response, err := ct.client.GetFreeBusy(params)
	if err != nil {
		return nil, fmt.Errorf("failed to get free/busy information: %v", err)
	}

	result := ct.formatFreeBusyResult(response, attendees, timeMin, timeMax)

	return &mcp.CallToolResult{
		Content: []mcp.ToolResult{{
			Type: "text",
			Text: result,
		}},
	}, nil
}

func (ct *CalendarTools) parseEventParams(arguments map[string]interface{}) (EventParams, error) {
	eventType := getStringOrDefault(arguments, "eventType", "default")
	visibility := getStringOrDefault(arguments, "visibility", "default")

	// Working location events MUST have public visibility
	if eventType == "workingLocation" {
		visibility = "public"
	}

	params := EventParams{
		CalendarID:             getStringOrDefault(arguments, "calendar_id", "primary"),
		Summary:                getStringOrDefault(arguments, "summary", ""),
		Description:            getStringOrDefault(arguments, "description", ""),
		Location:               getStringOrDefault(arguments, "location", ""),
		TimeZone:               getStringOrDefault(arguments, "timezone", "UTC"),
		AllDay:                 getBoolOrDefault(arguments, "all_day", false),
		Visibility:             visibility,
		SendNotifications:      getBoolOrDefault(arguments, "send_notifications", true),
		GuestCanModify:         getBoolOrDefault(arguments, "guest_can_modify", false),
		GuestCanInviteOthers:   getBoolOrDefault(arguments, "guest_can_invite_others", true),
		GuestCanSeeOtherGuests: getBoolOrDefault(arguments, "guest_can_see_other_guests", true),
		ColorID:                getStringOrDefault(arguments, "colorId", ""),
		EventType:              eventType,
	}

	// Parse workingLocation if provided
	if workingLocationInterface, ok := arguments["workingLocation"]; ok {
		if workingLocationMap, ok := workingLocationInterface.(map[string]interface{}); ok {
			params.WorkingLocation = &WorkingLocationParams{
				Type:  getStringOrDefault(workingLocationMap, "type", ""),
				Label: getStringOrDefault(workingLocationMap, "label", ""),
			}
		}
	}

	// Parse focusTimeProperties if provided
	if focusTimeInterface, ok := arguments["focusTimeProperties"]; ok {
		if focusTimeMap, ok := focusTimeInterface.(map[string]interface{}); ok {
			// Set defaults
			autoDeclineMode := getStringOrDefault(focusTimeMap, "autoDeclineMode", "declineOnlyNewConflictingInvitations")
			chatStatus := getStringOrDefault(focusTimeMap, "chatStatus", "doNotDisturb")
			declineMessage := getStringOrDefault(focusTimeMap, "declineMessage", "")

			// Create default decline message if not provided
			if declineMessage == "" {
				declineMessage = "I'm currently in focus time and unable to attend meetings. Please reach out if this is urgent."
			}

			params.FocusTimeProperties = &FocusTimeProperties{
				AutoDeclineMode: autoDeclineMode,
				ChatStatus:      chatStatus,
				DeclineMessage:  declineMessage,
			}
		}
	}

	// Parse start and end times
	if startTimeStr, ok := arguments["start_time"].(string); ok && startTimeStr != "" {
		startTime, err := time.Parse(time.RFC3339, startTimeStr)
		if err != nil {
			return params, fmt.Errorf("invalid start_time format: %v", err)
		}
		params.StartTime = startTime
	}

	if endTimeStr, ok := arguments["end_time"].(string); ok && endTimeStr != "" {
		endTime, err := time.Parse(time.RFC3339, endTimeStr)
		if err != nil {
			return params, fmt.Errorf("invalid end_time format: %v", err)
		}
		params.EndTime = endTime
	}

	// Parse attendees
	if attendeesInterface, ok := arguments["attendees"]; ok {
		if attendeesSlice, ok := attendeesInterface.([]interface{}); ok {
			attendees := make([]string, len(attendeesSlice))
			for i, v := range attendeesSlice {
				if email, ok := v.(string); ok {
					attendees[i] = email
				}
			}
			params.Attendees = attendees
		}
	}

	// Parse recurrence
	if recurrenceInterface, ok := arguments["recurrence"]; ok {
		if recurrenceSlice, ok := recurrenceInterface.([]interface{}); ok {
			recurrence := make([]string, len(recurrenceSlice))
			for i, v := range recurrenceSlice {
				if rule, ok := v.(string); ok {
					recurrence[i] = rule
				}
			}
			params.Recurrence = recurrence
		}
	}

	// Parse reminders
	if remindersInterface, ok := arguments["reminders"]; ok {
		if remindersMap, ok := remindersInterface.(map[string]interface{}); ok {
			reminders := &RemindersParams{
				UseDefault: getBoolOrDefault(remindersMap, "use_default", true),
			}

			if overridesInterface, ok := remindersMap["overrides"]; ok {
				if overridesSlice, ok := overridesInterface.([]interface{}); ok {
					overrides := make([]Reminder, len(overridesSlice))
					for i, v := range overridesSlice {
						if reminderMap, ok := v.(map[string]interface{}); ok {
							overrides[i] = Reminder{
								Method:  getStringOrDefault(reminderMap, "method", "popup"),
								Minutes: int64(getIntOrDefault(reminderMap, "minutes", 15)),
							}
						}
					}
					reminders.Overrides = overrides
				}
			}

			params.Reminders = reminders
		}
	}

	return params, nil
}

func (ct *CalendarTools) parsePatchEventParams(arguments map[string]interface{}) (PatchEventParams, error) {
	params := PatchEventParams{
		CalendarID:        getStringOrDefault(arguments, "calendar_id", "primary"),
		SendNotifications: getBoolOrDefault(arguments, "send_notifications", true),
	}

	// Only set pointer fields if they are explicitly provided in the arguments
	if summary, ok := arguments["summary"].(string); ok {
		params.Summary = &summary
	}
	if description, ok := arguments["description"].(string); ok {
		params.Description = &description
	}
	if location, ok := arguments["location"].(string); ok {
		params.Location = &location
	}
	if timezone, ok := arguments["timezone"].(string); ok {
		params.TimeZone = &timezone
	}
	if visibility, ok := arguments["visibility"].(string); ok {
		params.Visibility = &visibility
	}
	if allDay, ok := arguments["all_day"].(bool); ok {
		params.AllDay = &allDay
	}
	if colorID, ok := arguments["colorId"].(string); ok {
		params.ColorID = &colorID
	}
	if eventType, ok := arguments["eventType"].(string); ok {
		params.EventType = &eventType

		// Working location events MUST have public visibility
		if eventType == "workingLocation" {
			publicVisibility := "public"
			params.Visibility = &publicVisibility
		}
	}

	// Parse workingLocation if provided
	if workingLocationInterface, ok := arguments["workingLocation"]; ok {
		if workingLocationMap, ok := workingLocationInterface.(map[string]interface{}); ok {
			workingLocation := &WorkingLocationParams{
				Type:  getStringOrDefault(workingLocationMap, "type", ""),
				Label: getStringOrDefault(workingLocationMap, "label", ""),
			}
			params.WorkingLocation = workingLocation
		}
	}

	// Guest permissions - set only if explicitly provided
	if guestCanModify, ok := arguments["guest_can_modify"].(bool); ok {
		params.GuestCanModify = &guestCanModify
	}
	if guestCanInviteOthers, ok := arguments["guest_can_invite_others"].(bool); ok {
		params.GuestCanInviteOthers = &guestCanInviteOthers
	}
	if guestCanSeeOtherGuests, ok := arguments["guest_can_see_other_guests"].(bool); ok {
		params.GuestCanSeeOtherGuests = &guestCanSeeOtherGuests
	}

	// Parse start and end times
	if startTimeStr, ok := arguments["start_time"].(string); ok && startTimeStr != "" {
		startTime, err := time.Parse(time.RFC3339, startTimeStr)
		if err != nil {
			return params, fmt.Errorf("invalid start_time format: %v", err)
		}
		params.StartTime = &startTime
	}

	if endTimeStr, ok := arguments["end_time"].(string); ok && endTimeStr != "" {
		endTime, err := time.Parse(time.RFC3339, endTimeStr)
		if err != nil {
			return params, fmt.Errorf("invalid end_time format: %v", err)
		}
		params.EndTime = &endTime
	}

	// Parse attendees - set HasAttendees flag if attendees key exists (even if empty)
	if attendeesInterface, exists := arguments["attendees"]; exists {
		params.HasAttendees = true
		if attendeesSlice, ok := attendeesInterface.([]interface{}); ok {
			attendees := make([]AttendeeParams, len(attendeesSlice))
			for i, v := range attendeesSlice {
				if email, ok := v.(string); ok {
					// Backward compatibility: simple email string
					attendees[i] = AttendeeParams{
						Email:          email,
						ResponseStatus: "needsAction",
					}
				} else if attendeeMap, ok := v.(map[string]interface{}); ok {
					// New format: attendee object with email and response_status
					attendees[i] = AttendeeParams{
						Email:          getStringOrDefault(attendeeMap, "email", ""),
						ResponseStatus: getStringOrDefault(attendeeMap, "response_status", "needsAction"),
					}
				}
			}
			params.Attendees = attendees
		}
	}

	// Parse recurrence - set HasRecurrence flag if recurrence key exists (even if empty)
	if recurrenceInterface, exists := arguments["recurrence"]; exists {
		params.HasRecurrence = true
		if recurrenceSlice, ok := recurrenceInterface.([]interface{}); ok {
			recurrence := make([]string, len(recurrenceSlice))
			for i, v := range recurrenceSlice {
				if rule, ok := v.(string); ok {
					recurrence[i] = rule
				}
			}
			params.Recurrence = recurrence
		}
	}

	// Parse reminders
	if remindersInterface, ok := arguments["reminders"]; ok {
		if remindersMap, ok := remindersInterface.(map[string]interface{}); ok {
			reminders := &RemindersParams{
				UseDefault: getBoolOrDefault(remindersMap, "use_default", true),
			}

			if overridesInterface, ok := remindersMap["overrides"]; ok {
				if overridesSlice, ok := overridesInterface.([]interface{}); ok {
					overrides := make([]Reminder, len(overridesSlice))
					for i, v := range overridesSlice {
						if reminderMap, ok := v.(map[string]interface{}); ok {
							overrides[i] = Reminder{
								Method:  getStringOrDefault(reminderMap, "method", "popup"),
								Minutes: int64(getIntOrDefault(reminderMap, "minutes", 15)),
							}
						}
					}
					reminders.Overrides = overrides
				}
			}

			params.Reminders = reminders
		}
	}

	return params, nil
}

func (ct *CalendarTools) formatEventResult(event interface{}) string {
	eventJSON, _ := json.MarshalIndent(event, "", "  ")
	return fmt.Sprintf("✅ Event operation completed successfully:\n\n%s", string(eventJSON))
}

func (ct *CalendarTools) formatFreeBusyResult(response interface{}, attendees []string, timeMin, timeMax time.Time) string {
	var result strings.Builder
	result.WriteString(fmt.Sprintf("📅 Free/Busy information from %s to %s:\n\n",
		timeMin.Format("2006-01-02 15:04:05 MST"),
		timeMax.Format("2006-01-02 15:04:05 MST")))

	responseJSON, _ := json.MarshalIndent(response, "", "  ")
	result.WriteString(string(responseJSON))

	return result.String()
}

func (ct *CalendarTools) formatColorsResult(colors interface{}) string {
	var result strings.Builder
	result.WriteString("🎨 Available Calendar Colors:\n\n")

	colorsJSON, _ := json.MarshalIndent(colors, "", "  ")
	result.WriteString(string(colorsJSON))

	return result.String()
}

// Helper functions
func getStringOrDefault(args map[string]interface{}, key, defaultValue string) string {
	if val, ok := args[key].(string); ok {
		return val
	}
	return defaultValue
}

func getBoolOrDefault(args map[string]interface{}, key string, defaultValue bool) bool {
	if val, ok := args[key].(bool); ok {
		return val
	}
	return defaultValue
}

func getIntOrDefault(args map[string]interface{}, key string, defaultValue int) int {
	if val, ok := args[key].(float64); ok {
		return int(val)
	}
	if val, ok := args[key].(int); ok {
		return val
	}
	return defaultValue
}

func (ct *CalendarTools) handleListEvents(arguments map[string]interface{}) (*mcp.CallToolResult, error) {
	params := ListEventsParams{
		CalendarID:     getStringOrDefault(arguments, "calendar_id", "primary"),
		TimeFilter:     getStringOrDefault(arguments, "time_filter", "today"),
		TimeZone:       getStringOrDefault(arguments, "timezone", "UTC"),
		MaxResults:     int64(getIntOrDefault(arguments, "max_results", 250)),
		ShowDeleted:    getBoolOrDefault(arguments, "show_deleted", false),
		SingleEvents:   true,
		OrderBy:        getStringOrDefault(arguments, "order_by", "startTime"),
		ShowDeclined:   getBoolOrDefault(arguments, "show_declined", false),
		DetectOverlaps: getBoolOrDefault(arguments, "detect_overlaps", true),
	}

	outputFormat := getStringOrDefault(arguments, "output_format", "text")

	// Parse custom time range if provided
	if params.TimeFilter == "custom" {
		timeMinStr, ok := arguments["time_min"].(string)
		if !ok || timeMinStr == "" {
			return nil, fmt.Errorf("time_min is required when time_filter is 'custom'")
		}

		timeMaxStr, ok := arguments["time_max"].(string)
		if !ok || timeMaxStr == "" {
			return nil, fmt.Errorf("time_max is required when time_filter is 'custom'")
		}

		timeMin, err := time.Parse(time.RFC3339, timeMinStr)
		if err != nil {
			return nil, fmt.Errorf("invalid time_min format: %v", err)
		}

		timeMax, err := time.Parse(time.RFC3339, timeMaxStr)
		if err != nil {
			return nil, fmt.Errorf("invalid time_max format: %v", err)
		}

		params.TimeMin = timeMin
		params.TimeMax = timeMax
	}

	events, err := ct.client.ListEvents(params)
	if err != nil {
		return nil, fmt.Errorf("failed to list events: %v", err)
	}

	var result string

	if outputFormat == "json" {
		// Return JSON format with overlap detection
		jsonResult := ct.formatEventsJSON(events, params)
		jsonBytes, err := json.Marshal(jsonResult)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal events to JSON: %v", err)
		}
		result = string(jsonBytes)
	} else {
		// Return formatted text
		result = ct.formatEventsResult(events, params)
	}

	return &mcp.CallToolResult{
		Content: []mcp.ToolResult{{
			Type: "text",
			Text: result,
		}},
	}, nil
}

func (ct *CalendarTools) formatEventsJSON(events *calendar.Events, params ListEventsParams) map[string]interface{} {
	// Detect overlaps if requested
	var overlaps map[string]bool
	var overlappingPairs map[string][]string

	if params.DetectOverlaps {
		overlaps = ct.client.DetectOverlaps(events.Items, params.ShowDeclined)
		// Build overlapping pairs map
		overlappingPairs = make(map[string][]string)
		for i, event1 := range events.Items {
			if overlaps[event1.Id] {
				// Parse event1 times
				var start1, end1 time.Time
				if event1.Start.DateTime != "" {
					start1, _ = time.Parse(time.RFC3339, event1.Start.DateTime)
					end1, _ = time.Parse(time.RFC3339, event1.End.DateTime)
				}

				var overlappingIds []string
				for j, event2 := range events.Items {
					if i != j {
						// Parse event2 times
						var start2, end2 time.Time
						if event2.Start.DateTime != "" {
							start2, _ = time.Parse(time.RFC3339, event2.Start.DateTime)
							end2, _ = time.Parse(time.RFC3339, event2.End.DateTime)
						}

						if !start1.IsZero() && !start2.IsZero() && eventsOverlap(start1, end1, start2, end2) {
							overlappingIds = append(overlappingIds, event2.Id)
						}
					}
				}
				if len(overlappingIds) > 0 {
					overlappingPairs[event1.Id] = overlappingIds
				}
			}
		}
	}

	// Build JSON result
	result := make(map[string]interface{})
	result["time_filter"] = params.TimeFilter
	result["total_count"] = len(events.Items)

	// Convert events to JSON-friendly format
	eventsJSON := make([]map[string]interface{}, 0, len(events.Items))
	for _, event := range events.Items {
		eventJSON := make(map[string]interface{})
		eventJSON["id"] = event.Id
		eventJSON["summary"] = event.Summary
		eventJSON["description"] = event.Description
		eventJSON["location"] = event.Location
		eventJSON["status"] = event.Status
		eventJSON["eventType"] = event.EventType

		// Start/End times
		eventJSON["start"] = map[string]interface{}{
			"dateTime": event.Start.DateTime,
			"date":     event.Start.Date,
			"timeZone": event.Start.TimeZone,
		}
		eventJSON["end"] = map[string]interface{}{
			"dateTime": event.End.DateTime,
			"date":     event.End.Date,
			"timeZone": event.End.TimeZone,
		}

		// Attendees
		if len(event.Attendees) > 0 {
			attendeesJSON := make([]map[string]interface{}, 0, len(event.Attendees))
			for _, attendee := range event.Attendees {
				attendeeJSON := make(map[string]interface{})
				attendeeJSON["email"] = attendee.Email
				attendeeJSON["displayName"] = attendee.DisplayName
				attendeeJSON["responseStatus"] = attendee.ResponseStatus
				attendeeJSON["self"] = attendee.Self
				attendeeJSON["organizer"] = attendee.Organizer
				attendeesJSON = append(attendeesJSON, attendeeJSON)
			}
			eventJSON["attendees"] = attendeesJSON
		}

		// Overlap information
		if overlaps != nil {
			eventJSON["has_overlap"] = overlaps[event.Id]
			if overlappingIds, exists := overlappingPairs[event.Id]; exists {
				eventJSON["overlapping_event_ids"] = overlappingIds
			}
		}

		// Color
		if event.ColorId != "" {
			eventJSON["colorId"] = event.ColorId
		}

		// Hangout/Meet link
		if event.HangoutLink != "" {
			eventJSON["hangoutLink"] = event.HangoutLink
		}

		// Focus time properties
		if event.FocusTimeProperties != nil {
			focusProps := make(map[string]interface{})
			focusProps["autoDeclineMode"] = event.FocusTimeProperties.AutoDeclineMode
			focusProps["chatStatus"] = event.FocusTimeProperties.ChatStatus
			eventJSON["focusTimeProperties"] = focusProps
		}

		// Working location properties
		if event.WorkingLocationProperties != nil {
			workingLocProps := make(map[string]interface{})
			workingLocProps["type"] = event.WorkingLocationProperties.Type
			if event.WorkingLocationProperties.CustomLocation != nil {
				workingLocProps["customLocation"] = event.WorkingLocationProperties.CustomLocation.Label
			}
			if event.WorkingLocationProperties.HomeOffice != nil {
				workingLocProps["homeOffice"] = true
			}
			if event.WorkingLocationProperties.OfficeLocation != nil {
				workingLocProps["officeLocation"] = event.WorkingLocationProperties.OfficeLocation.Label
			}
			eventJSON["workingLocationProperties"] = workingLocProps
		}

		eventsJSON = append(eventsJSON, eventJSON)
	}

	result["events"] = eventsJSON

	return result
}

func (ct *CalendarTools) formatEventsResult(events *calendar.Events, params ListEventsParams) string {
	var result strings.Builder

	// Create a descriptive header based on the time filter
	switch params.TimeFilter {
	case "today":
		result.WriteString("📅 Events for Today:\n\n")
	case "this_week":
		result.WriteString("📅 Events for This Week (Monday-Friday):\n\n")
	case "next_week":
		result.WriteString("📅 Events for Next Week (Monday-Friday):\n\n")
	case "custom":
		result.WriteString(fmt.Sprintf("📅 Events from %s to %s:\n\n",
			params.TimeMin.Format("2006-01-02 15:04"),
			params.TimeMax.Format("2006-01-02 15:04")))
	default:
		result.WriteString("📅 Calendar Events:\n\n")
	}

	if len(events.Items) == 0 {
		result.WriteString("No events found for the specified time period.")
		return result.String()
	}

	// Detect overlaps if requested
	var overlaps map[string]bool
	if params.DetectOverlaps {
		overlaps = ct.client.DetectOverlaps(events.Items, params.ShowDeclined)
	}

	// Group events by date
	eventsByDate := make(map[string][]*calendar.Event)
	for _, event := range events.Items {
		var eventDate string
		if event.Start.Date != "" {
			// All-day event
			eventDate = event.Start.Date
		} else if event.Start.DateTime != "" {
			// Regular event
			startTime, err := time.Parse(time.RFC3339, event.Start.DateTime)
			if err == nil {
				eventDate = startTime.Format("2006-01-02")
			} else {
				eventDate = "Unknown"
			}
		} else {
			eventDate = "Unknown"
		}

		eventsByDate[eventDate] = append(eventsByDate[eventDate], event)
	}

	// Sort dates
	var dates []string
	for date := range eventsByDate {
		dates = append(dates, date)
	}
	// Sort dates (simple string sort works for YYYY-MM-DD format)
	for i := 0; i < len(dates); i++ {
		for j := i + 1; j < len(dates); j++ {
			if dates[i] > dates[j] {
				dates[i], dates[j] = dates[j], dates[i]
			}
		}
	}

	// Display events grouped by date
	for i, date := range dates {
		if i > 0 {
			result.WriteString("\n")
		}

		// Format date header
		if parsedDate, err := time.Parse("2006-01-02", date); err == nil {
			result.WriteString(fmt.Sprintf("## %s\n", parsedDate.Format("Monday, January 2, 2006")))
		} else {
			result.WriteString(fmt.Sprintf("## %s\n", date))
		}

		for _, event := range eventsByDate[date] {
			hasOverlap := false
			if overlaps != nil {
				hasOverlap = overlaps[event.Id]
			}
			ct.formatSingleEvent(&result, event, hasOverlap)
		}
	}

	result.WriteString(fmt.Sprintf("\n📊 Total: %d events", len(events.Items)))

	return result.String()
}

func (ct *CalendarTools) formatSingleEvent(result *strings.Builder, event *calendar.Event, hasOverlap bool) {
	// Event title
	title := event.Summary
	if title == "" {
		title = "(No Title)"
	}
	result.WriteString(fmt.Sprintf("### %s\n", title))

	// Time information
	if event.Start.Date != "" {
		// All-day event
		result.WriteString("🕐 **All Day**\n")
	} else if event.Start.DateTime != "" {
		// Regular event with time
		startTime, err := time.Parse(time.RFC3339, event.Start.DateTime)
		if err == nil {
			endTime, endErr := time.Parse(time.RFC3339, event.End.DateTime)
			if endErr == nil {
				// Same day event
				if startTime.Format("2006-01-02") == endTime.Format("2006-01-02") {
					result.WriteString(fmt.Sprintf("🕐 **%s - %s**\n",
						startTime.Format("3:04 PM"),
						endTime.Format("3:04 PM")))
				} else {
					// Multi-day event
					result.WriteString(fmt.Sprintf("🕐 **%s - %s**\n",
						startTime.Format("Jan 2, 3:04 PM"),
						endTime.Format("Jan 2, 3:04 PM")))
				}
			} else {
				result.WriteString(fmt.Sprintf("🕐 **%s**\n", startTime.Format("3:04 PM")))
			}
		}
	}

	// Location
	if event.Location != "" {
		result.WriteString(fmt.Sprintf("📍 **Location:** %s\n", event.Location))
	}

	// Attendees
	if len(event.Attendees) > 0 {
		result.WriteString("👥 **Attendees:** ")
		attendeeStrings := make([]string, 0, len(event.Attendees))
		for _, attendee := range event.Attendees {
			name := attendee.DisplayName
			if name == "" {
				name = attendee.Email
			}

			// Add response status if available
			statusIcon := ""
			switch attendee.ResponseStatus {
			case "accepted":
				statusIcon = " ✅"
			case "declined":
				statusIcon = " ❌"
			case "tentative":
				statusIcon = " ⏳"
			case "needsAction":
				statusIcon = " ❓"
			default:
				statusIcon = ""
			}

			attendeeStrings = append(attendeeStrings, name+statusIcon)
		}
		result.WriteString(strings.Join(attendeeStrings, ", "))
		result.WriteString("\n")
	}

	// Description (truncated)
	if event.Description != "" {
		description := event.Description
		if len(description) > 200 {
			description = description[:200] + "..."
		}
		result.WriteString(fmt.Sprintf("📝 **Description:** %s\n", description))
	}

	// Conference/meeting link
	if event.ConferenceData != nil && len(event.ConferenceData.EntryPoints) > 0 {
		for _, entry := range event.ConferenceData.EntryPoints {
			if entry.EntryPointType == "video" {
				result.WriteString(fmt.Sprintf("🔗 **Meeting Link:** %s\n", entry.Uri))
				break
			}
		}
	}

	// Event type information from extended properties
	if event.ExtendedProperties != nil && event.ExtendedProperties.Private != nil {
		if eventType, exists := event.ExtendedProperties.Private["eventType"]; exists && eventType != "" {
			var typeIcon string
			switch eventType {
			case "focusTime":
				typeIcon = "🧠"
			case "workingLocation":
				typeIcon = "📍"
			default:
				typeIcon = "📋"
			}
			result.WriteString(fmt.Sprintf("%s **Event Type:** %s\n", typeIcon, eventType))
		}

		// Working location information from extended properties
		if workingType, typeExists := event.ExtendedProperties.Private["workingLocationType"]; typeExists && workingType != "" {
			if workingLabel, labelExists := event.ExtendedProperties.Private["workingLocationLabel"]; labelExists && workingLabel != "" {
				result.WriteString(fmt.Sprintf("🏢 **Working Location:** %s (%s)\n", workingLabel, workingType))
			} else {
				result.WriteString(fmt.Sprintf("🏢 **Working Location Type:** %s\n", workingType))
			}
		}

		// Focus time properties information from extended properties
		if autoDeclineMode, exists := event.ExtendedProperties.Private["focusTimeAutoDeclineMode"]; exists && autoDeclineMode != "" {
			result.WriteString(fmt.Sprintf("🛡️ **Auto-decline Mode:** %s\n", autoDeclineMode))
		}
		if chatStatus, exists := event.ExtendedProperties.Private["focusTimeChatStatus"]; exists && chatStatus != "" {
			statusIcon := "💬"
			if chatStatus == "doNotDisturb" {
				statusIcon = "🔕"
			}
			result.WriteString(fmt.Sprintf("%s **Chat Status:** %s\n", statusIcon, chatStatus))
		}
		if declineMessage, exists := event.ExtendedProperties.Private["focusTimeDeclineMessage"]; exists && declineMessage != "" {
			result.WriteString(fmt.Sprintf("📝 **Decline Message:** %s\n", declineMessage))
		}
	}

	// Also check focus time properties from Google Calendar API fields
	if event.FocusTimeProperties != nil {
		if event.FocusTimeProperties.AutoDeclineMode != "" {
			result.WriteString(fmt.Sprintf("🛡️ **Auto-decline Mode:** %s\n", event.FocusTimeProperties.AutoDeclineMode))
		}
		if event.FocusTimeProperties.ChatStatus != "" {
			statusIcon := "💬"
			if event.FocusTimeProperties.ChatStatus == "doNotDisturb" {
				statusIcon = "🔕"
			}
			result.WriteString(fmt.Sprintf("%s **Chat Status:** %s\n", statusIcon, event.FocusTimeProperties.ChatStatus))
		}
		if event.FocusTimeProperties.DeclineMessage != "" {
			result.WriteString(fmt.Sprintf("📝 **Decline Message:** %s\n", event.FocusTimeProperties.DeclineMessage))
		}
	}

	// Color information - always show to debug what's being returned
	result.WriteString(fmt.Sprintf("🎨 **Color ID:** '%s' (length: %d)\n", event.ColorId, len(event.ColorId)))

	// Event ID for reference
	result.WriteString(fmt.Sprintf("🆔 **Event ID:** %s\n", event.Id))

	// Overlap status
	overlapIcon := "✅"
	if hasOverlap {
		overlapIcon = "⚠️"
	}
	result.WriteString(fmt.Sprintf("%s **Has Overlap:** %t\n", overlapIcon, hasOverlap))

	result.WriteString("\n")
}
