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
	"fmt"
	"regexp"
	"time"

	"google.golang.org/api/calendar/v3"
	"google.golang.org/api/googleapi"
)

type Client struct {
	service *calendar.Service
}

func NewClient(service *calendar.Service) *Client {
	return &Client{
		service: service,
	}
}

type EventParams struct {
	CalendarID             string                   `json:"calendar_id"`
	Summary                string                   `json:"summary"`
	Description            string                   `json:"description,omitempty"`
	Location               string                   `json:"location,omitempty"`
	StartTime              time.Time                `json:"start_time"`
	EndTime                time.Time                `json:"end_time"`
	TimeZone               string                   `json:"timezone,omitempty"`
	AllDay                 bool                     `json:"all_day,omitempty"`
	Attendees              []string                 `json:"attendees,omitempty"`
	Recurrence             []string                 `json:"recurrence,omitempty"`
	Visibility             string                   `json:"visibility,omitempty"`
	SendNotifications      bool                     `json:"send_notifications,omitempty"`
	GuestCanModify         bool                     `json:"guest_can_modify,omitempty"`
	GuestCanInviteOthers   bool                     `json:"guest_can_invite_others,omitempty"`
	GuestCanSeeOtherGuests bool                     `json:"guest_can_see_other_guests,omitempty"`
	ConferenceData         *ConferenceDataParams    `json:"conference_data,omitempty"`
	Reminders              *RemindersParams         `json:"reminders,omitempty"`
	ColorID                string                   `json:"color_id,omitempty"`
	EventType              string                   `json:"event_type,omitempty"`
	WorkingLocation        *WorkingLocationParams   `json:"working_location,omitempty"`
	FocusTimeProperties    *FocusTimeProperties     `json:"focus_time_properties,omitempty"`
}

// WorkingLocationParams represents working location information for events
type WorkingLocationParams struct {
	Type  string `json:"type"`  // "home", "office", or "custom"
	Label string `json:"label"` // Custom label for the location
}

// FocusTimeProperties represents focus time configuration for events
type FocusTimeProperties struct {
	AutoDeclineMode string `json:"autoDeclineMode"` // "declineNone", "declineAll", "declineOnlyNew"
	ChatStatus      string `json:"chatStatus"`      // "available", "doNotDisturb"
	DeclineMessage  string `json:"declineMessage"`  // Custom decline message
}

// PatchEventParams represents parameters for patching an event with explicit field tracking
type PatchEventParams struct {
	CalendarID             string                `json:"calendar_id"`
	Summary                *string               `json:"summary,omitempty"`
	Description            *string               `json:"description,omitempty"`
	Location               *string               `json:"location,omitempty"`
	StartTime              *time.Time            `json:"start_time,omitempty"`
	EndTime                *time.Time            `json:"end_time,omitempty"`
	TimeZone               *string               `json:"timezone,omitempty"`
	AllDay                 *bool                 `json:"all_day,omitempty"`
	Attendees              []AttendeeParams      `json:"attendees,omitempty"`
	Recurrence             []string              `json:"recurrence,omitempty"`
	Visibility             *string               `json:"visibility,omitempty"`
	SendNotifications      bool                  `json:"send_notifications,omitempty"`
	GuestCanModify         *bool                 `json:"guest_can_modify,omitempty"`
	GuestCanInviteOthers   *bool                 `json:"guest_can_invite_others,omitempty"`
	GuestCanSeeOtherGuests *bool                 `json:"guest_can_see_other_guests,omitempty"`
	ConferenceData         *ConferenceDataParams `json:"conference_data,omitempty"`
	Reminders              *RemindersParams         `json:"reminders,omitempty"`
	ColorID                *string                  `json:"color_id,omitempty"`
	EventType              *string                  `json:"event_type,omitempty"`
	WorkingLocation        *WorkingLocationParams   `json:"working_location,omitempty"`

	// Track which fields have been explicitly provided
	HasAttendees  bool `json:"-"`
	HasRecurrence bool `json:"-"}`
}

type AttendeeParams struct {
	Email          string `json:"email"`
	ResponseStatus string `json:"response_status,omitempty"`
}

type ConferenceDataParams struct {
	CreateRequest *CreateConferenceRequest `json:"create_request,omitempty"`
}

type CreateConferenceRequest struct {
	RequestID          string              `json:"request_id,omitempty"`
	ConferenceSolution *ConferenceSolution `json:"conference_solution,omitempty"`
}

type ConferenceSolution struct {
	Type string `json:"type"` // "hangoutsMeet", "addOn"
}

type RemindersParams struct {
	UseDefault bool       `json:"use_default,omitempty"`
	Overrides  []Reminder `json:"overrides,omitempty"`
}

type Reminder struct {
	Method  string `json:"method"` // "email", "popup"
	Minutes int64  `json:"minutes"`
}

type AttendeeSearchParams struct {
	Query      string `json:"query"`
	MaxResults int    `json:"max_results,omitempty"`
	Domain     string `json:"domain,omitempty"`
}

type FreeBusyParams struct {
	TimeMin              time.Time `json:"time_min"`
	TimeMax              time.Time `json:"time_max"`
	TimeZone             string    `json:"timezone,omitempty"`
	CalendarIDs          []string  `json:"calendar_ids,omitempty"`
	GroupExpansionMax    int       `json:"group_expansion_max,omitempty"`
	CalendarExpansionMax int       `json:"calendar_expansion_max,omitempty"`
}

type ListEventsParams struct {
	CalendarID   string    `json:"calendar_id"`
	TimeFilter   string    `json:"time_filter"` // "today", "this_week", "next_week", "custom"
	TimeMin      time.Time `json:"time_min,omitempty"`
	TimeMax      time.Time `json:"time_max,omitempty"`
	TimeZone     string    `json:"timezone,omitempty"`
	MaxResults   int64     `json:"max_results,omitempty"`
	ShowDeleted  bool      `json:"show_deleted,omitempty"`
	SingleEvents bool      `json:"single_events,omitempty"`
	OrderBy      string    `json:"order_by,omitempty"`
}

func (c *Client) CreateEvent(params EventParams) (*calendar.Event, error) {
	if params.CalendarID == "" {
		params.CalendarID = "primary"
	}

	event := &calendar.Event{
		Summary:     params.Summary,
		Description: params.Description,
		Location:    params.Location,
	}

	// Set start and end times
	if params.AllDay {
		event.Start = &calendar.EventDateTime{
			Date:     params.StartTime.Format("2006-01-02"),
			TimeZone: params.TimeZone,
		}
		event.End = &calendar.EventDateTime{
			Date:     params.EndTime.Format("2006-01-02"),
			TimeZone: params.TimeZone,
		}
	} else {
		event.Start = &calendar.EventDateTime{
			DateTime: params.StartTime.Format(time.RFC3339),
			TimeZone: params.TimeZone,
		}
		event.End = &calendar.EventDateTime{
			DateTime: params.EndTime.Format(time.RFC3339),
			TimeZone: params.TimeZone,
		}
	}

	// Add attendees
	if len(params.Attendees) > 0 {
		attendees := make([]*calendar.EventAttendee, len(params.Attendees))
		for i, email := range params.Attendees {
			attendees[i] = &calendar.EventAttendee{
				Email: email,
			}
		}
		event.Attendees = attendees
	}

	// Set recurrence
	if len(params.Recurrence) > 0 {
		event.Recurrence = params.Recurrence
	}

	// Set visibility
	if params.Visibility != "" {
		event.Visibility = params.Visibility
	}

	// Set color
	if params.ColorID != "" {
		event.ColorId = params.ColorID
	}

	// Set guest permissions
	event.GuestsCanModify = params.GuestCanModify
	event.GuestsCanInviteOthers = &params.GuestCanInviteOthers
	event.GuestsCanSeeOtherGuests = &params.GuestCanSeeOtherGuests

	// Set conference data
	if params.ConferenceData != nil {
		event.ConferenceData = &calendar.ConferenceData{}
		if params.ConferenceData.CreateRequest != nil {
			event.ConferenceData.CreateRequest = &calendar.CreateConferenceRequest{
				RequestId: params.ConferenceData.CreateRequest.RequestID,
			}
			if params.ConferenceData.CreateRequest.ConferenceSolution != nil {
				event.ConferenceData.CreateRequest.ConferenceSolutionKey = &calendar.ConferenceSolutionKey{
					Type: params.ConferenceData.CreateRequest.ConferenceSolution.Type,
				}
			}
		}
	}

	// Set reminders
	if params.Reminders != nil {
		event.Reminders = &calendar.EventReminders{
			UseDefault: params.Reminders.UseDefault,
		}
		if len(params.Reminders.Overrides) > 0 {
			overrides := make([]*calendar.EventReminder, len(params.Reminders.Overrides))
			for i, reminder := range params.Reminders.Overrides {
				overrides[i] = &calendar.EventReminder{
					Method:  reminder.Method,
					Minutes: reminder.Minutes,
				}
			}
			event.Reminders.Overrides = overrides
		}
	}

	// Set event type
	if params.EventType != "" {
		event.EventType = params.EventType
	}

	// Set extended properties to store eventType, workingLocation, and focusTimeProperties
	if params.EventType != "" || params.WorkingLocation != nil || params.FocusTimeProperties != nil {
		event.ExtendedProperties = &calendar.EventExtendedProperties{
			Private: make(map[string]string),
		}

		if params.EventType != "" {
			event.ExtendedProperties.Private["eventType"] = params.EventType
		}

		if params.WorkingLocation != nil {
			event.ExtendedProperties.Private["workingLocationType"] = params.WorkingLocation.Type
			event.ExtendedProperties.Private["workingLocationLabel"] = params.WorkingLocation.Label
		}

		if params.FocusTimeProperties != nil {
			event.ExtendedProperties.Private["focusTimeAutoDeclineMode"] = params.FocusTimeProperties.AutoDeclineMode
			event.ExtendedProperties.Private["focusTimeChatStatus"] = params.FocusTimeProperties.ChatStatus
			event.ExtendedProperties.Private["focusTimeDeclineMessage"] = params.FocusTimeProperties.DeclineMessage
		}
	}

	// Set focus time properties for Google Calendar API
	if params.EventType == "focusTime" && params.FocusTimeProperties != nil {
		event.FocusTimeProperties = &calendar.EventFocusTimeProperties{
			AutoDeclineMode: params.FocusTimeProperties.AutoDeclineMode,
			ChatStatus:      params.FocusTimeProperties.ChatStatus,
			DeclineMessage:  params.FocusTimeProperties.DeclineMessage,
		}
	}

	call := c.service.Events.Insert(params.CalendarID, event)
	if params.SendNotifications {
		call = call.SendNotifications(true)
	}
	if params.ConferenceData != nil {
		call = call.ConferenceDataVersion(1)
	}

	return call.Do()
}

func (c *Client) PatchEvent(eventID string, params EventParams) (*calendar.Event, error) {
	// Convert EventParams to PatchEventParams for backward compatibility
	patchParams := PatchEventParams{
		CalendarID:        params.CalendarID,
		SendNotifications: params.SendNotifications,
	}

	// Only set fields that are non-zero/non-empty (backward compatibility behavior)
	if params.Summary != "" {
		patchParams.Summary = &params.Summary
	}
	if params.Description != "" {
		patchParams.Description = &params.Description
	}
	if params.Location != "" {
		patchParams.Location = &params.Location
	}
	if !params.StartTime.IsZero() {
		patchParams.StartTime = &params.StartTime
	}
	if !params.EndTime.IsZero() {
		patchParams.EndTime = &params.EndTime
	}
	if params.TimeZone != "" {
		patchParams.TimeZone = &params.TimeZone
	}
	if params.Visibility != "" {
		patchParams.Visibility = &params.Visibility
	}
	if params.ColorID != "" {
		patchParams.ColorID = &params.ColorID
	}
	if len(params.Attendees) > 0 {
		// Convert []string to []AttendeeParams for backward compatibility
		attendeeParams := make([]AttendeeParams, len(params.Attendees))
		for i, email := range params.Attendees {
			attendeeParams[i] = AttendeeParams{
				Email:          email,
				ResponseStatus: "needsAction", // Default for new attendees
			}
		}
		patchParams.Attendees = attendeeParams
		patchParams.HasAttendees = true
	}
	if len(params.Recurrence) > 0 {
		patchParams.Recurrence = params.Recurrence
		patchParams.HasRecurrence = true
	}

	// Guest permissions - always set if any are provided
	if params.GuestCanModify || params.GuestCanInviteOthers || params.GuestCanSeeOtherGuests {
		patchParams.GuestCanModify = &params.GuestCanModify
		patchParams.GuestCanInviteOthers = &params.GuestCanInviteOthers
		patchParams.GuestCanSeeOtherGuests = &params.GuestCanSeeOtherGuests
	}

	patchParams.AllDay = &params.AllDay
	patchParams.ConferenceData = params.ConferenceData
	patchParams.Reminders = params.Reminders

	return c.PatchEventDirect(eventID, patchParams)
}

func (c *Client) PatchEventDirect(eventID string, params PatchEventParams) (*calendar.Event, error) {
	if params.CalendarID == "" {
		params.CalendarID = "primary"
	}

	// Create a patch event with only the fields that are explicitly provided
	patchEvent := &calendar.Event{}

	// Only include fields that have been explicitly provided via pointers
	if params.Summary != nil {
		patchEvent.Summary = *params.Summary
	}
	if params.Description != nil {
		patchEvent.Description = *params.Description
	}
	if params.Location != nil {
		patchEvent.Location = *params.Location
	}

	// Update start/end times if provided
	if params.StartTime != nil {
		allDay := params.AllDay != nil && *params.AllDay
		timezone := ""
		if params.TimeZone != nil {
			timezone = *params.TimeZone
		}

		if allDay {
			patchEvent.Start = &calendar.EventDateTime{
				Date:     params.StartTime.Format("2006-01-02"),
				TimeZone: timezone,
			}
		} else {
			patchEvent.Start = &calendar.EventDateTime{
				DateTime: params.StartTime.Format(time.RFC3339),
				TimeZone: timezone,
			}
		}
	}

	if params.EndTime != nil {
		allDay := params.AllDay != nil && *params.AllDay
		timezone := ""
		if params.TimeZone != nil {
			timezone = *params.TimeZone
		}

		if allDay {
			patchEvent.End = &calendar.EventDateTime{
				Date:     params.EndTime.Format("2006-01-02"),
				TimeZone: timezone,
			}
		} else {
			patchEvent.End = &calendar.EventDateTime{
				DateTime: params.EndTime.Format(time.RFC3339),
				TimeZone: timezone,
			}
		}
	}

	// Update attendees if provided (replace entire attendee list, even if empty)
	if params.HasAttendees {
		attendees := make([]*calendar.EventAttendee, len(params.Attendees))
		for i, attendee := range params.Attendees {
			responseStatus := attendee.ResponseStatus
			if responseStatus == "" {
				responseStatus = "needsAction" // Default status for new attendees
			}
			attendees[i] = &calendar.EventAttendee{
				Email:          attendee.Email,
				ResponseStatus: responseStatus,
			}
		}
		patchEvent.Attendees = attendees
	}

	// Update recurrence if provided (replace entire recurrence list, even if empty)
	if params.HasRecurrence {
		patchEvent.Recurrence = params.Recurrence
	}

	if params.Visibility != nil {
		patchEvent.Visibility = *params.Visibility
	}

	if params.ColorID != nil {
		patchEvent.ColorId = *params.ColorID
	}

	// Set guest permissions only if explicitly provided
	if params.GuestCanModify != nil {
		patchEvent.GuestsCanModify = *params.GuestCanModify
	}
	if params.GuestCanInviteOthers != nil {
		patchEvent.GuestsCanInviteOthers = params.GuestCanInviteOthers
	}
	if params.GuestCanSeeOtherGuests != nil {
		patchEvent.GuestsCanSeeOtherGuests = params.GuestCanSeeOtherGuests
	}

	// Handle conference data
	if params.ConferenceData != nil {
		patchEvent.ConferenceData = &calendar.ConferenceData{}
		if params.ConferenceData.CreateRequest != nil {
			patchEvent.ConferenceData.CreateRequest = &calendar.CreateConferenceRequest{
				RequestId: params.ConferenceData.CreateRequest.RequestID,
			}
			if params.ConferenceData.CreateRequest.ConferenceSolution != nil {
				patchEvent.ConferenceData.CreateRequest.ConferenceSolutionKey = &calendar.ConferenceSolutionKey{
					Type: params.ConferenceData.CreateRequest.ConferenceSolution.Type,
				}
			}
		}
	}

	// Handle reminders
	if params.Reminders != nil {
		patchEvent.Reminders = &calendar.EventReminders{
			UseDefault: params.Reminders.UseDefault,
		}
		if len(params.Reminders.Overrides) > 0 {
			overrides := make([]*calendar.EventReminder, len(params.Reminders.Overrides))
			for i, reminder := range params.Reminders.Overrides {
				overrides[i] = &calendar.EventReminder{
					Method:  reminder.Method,
					Minutes: reminder.Minutes,
				}
			}
			patchEvent.Reminders.Overrides = overrides
		}
	}

	// Handle extended properties for eventType and workingLocation
	if params.EventType != nil || params.WorkingLocation != nil {
		patchEvent.ExtendedProperties = &calendar.EventExtendedProperties{
			Private: make(map[string]string),
		}

		if params.EventType != nil {
			patchEvent.ExtendedProperties.Private["eventType"] = *params.EventType
		}

		if params.WorkingLocation != nil {
			patchEvent.ExtendedProperties.Private["workingLocationType"] = params.WorkingLocation.Type
			patchEvent.ExtendedProperties.Private["workingLocationLabel"] = params.WorkingLocation.Label
		}
	}

	// Use Patch instead of Update
	call := c.service.Events.Patch(params.CalendarID, eventID, patchEvent)
	if params.SendNotifications {
		call = call.SendNotifications(true)
	}

	return call.Do()
}

func (c *Client) DeleteEvent(calendarID, eventID string, sendNotifications bool) error {
	if calendarID == "" {
		calendarID = "primary"
	}

	call := c.service.Events.Delete(calendarID, eventID)
	if sendNotifications {
		call = call.SendNotifications(true)
	}

	return call.Do()
}

func (c *Client) GetEvent(calendarID, eventID string) (*calendar.Event, error) {
	if calendarID == "" {
		calendarID = "primary"
	}

	// Get event with complete attendee information including response status and color
	getCall := c.service.Events.Get(calendarID, eventID).
		Fields(googleapi.Field("id,summary,description,location,start,end,attendees(email,displayName,responseStatus),conferenceData,creator,organizer,colorId"))
	return getCall.Do()
}

func (c *Client) SearchAttendees(params AttendeeSearchParams) ([]string, error) {
	// This is a simplified implementation since Google Calendar API doesn't have
	// a direct attendee search. In practice, you might want to integrate with
	// Google Directory API or maintain a contact list.

	// For now, return the query as a suggestion if it looks like an email
	if isValidEmail(params.Query) {
		return []string{params.Query}, nil
	}

	// In a real implementation, you would search through:
	// - Google Contacts
	// - Directory API (for G Suite domains)
	// - Previously used attendees from calendar events

	return []string{}, fmt.Errorf("attendee search not implemented - please provide full email addresses")
}

func (c *Client) GetFreeBusy(params FreeBusyParams) (*calendar.FreeBusyResponse, error) {
	if params.TimeZone == "" {
		params.TimeZone = "UTC"
	}

	if len(params.CalendarIDs) == 0 {
		params.CalendarIDs = []string{"primary"}
	}

	items := make([]*calendar.FreeBusyRequestItem, len(params.CalendarIDs))
	for i, calID := range params.CalendarIDs {
		items[i] = &calendar.FreeBusyRequestItem{
			Id: calID,
		}
	}

	request := &calendar.FreeBusyRequest{
		TimeMin:              params.TimeMin.Format(time.RFC3339),
		TimeMax:              params.TimeMax.Format(time.RFC3339),
		TimeZone:             params.TimeZone,
		Items:                items,
		GroupExpansionMax:    int64(params.GroupExpansionMax),
		CalendarExpansionMax: int64(params.CalendarExpansionMax),
	}

	return c.service.Freebusy.Query(request).Do()
}

func (c *Client) ListEvents(params ListEventsParams) (*calendar.Events, error) {
	if params.CalendarID == "" {
		params.CalendarID = "primary"
	}

	if params.TimeZone == "" {
		params.TimeZone = "UTC"
	}

	// Calculate time range based on filter
	timeMin, timeMax := calculateTimeRange(params.TimeFilter, params.TimeMin, params.TimeMax, params.TimeZone)

	call := c.service.Events.List(params.CalendarID)

	// Set time range
	call = call.TimeMin(timeMin.Format(time.RFC3339))
	call = call.TimeMax(timeMax.Format(time.RFC3339))

	// Ensure attendee information including response status is included
	call = call.AlwaysIncludeEmail(true)

	// Remove field selection to get all fields including colorId by default
	// call = call.Fields(googleapi.Field("items(id,summary,description,location,start,end,attendees(email,displayName,responseStatus),conferenceData,creator,organizer,colorId),nextPageToken,summary"))

	// Set other parameters
	if params.MaxResults > 0 {
		call = call.MaxResults(params.MaxResults)
	} else {
		call = call.MaxResults(250) // Default limit
	}

	call = call.ShowDeleted(params.ShowDeleted)
	call = call.SingleEvents(true) // Expand recurring events

	if params.OrderBy != "" {
		call = call.OrderBy(params.OrderBy)
	} else {
		call = call.OrderBy("startTime") // Default ordering
	}

	return call.Do()
}

func calculateTimeRange(timeFilter string, customMin, customMax time.Time, timezone string) (time.Time, time.Time) {
	loc, err := time.LoadLocation(timezone)
	if err != nil {
		loc = time.UTC
	}

	now := time.Now().In(loc)

	switch timeFilter {
	case "today":
		startOfDay := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, loc)
		endOfDay := startOfDay.Add(24 * time.Hour)
		return startOfDay, endOfDay

	case "this_week":
		// Calculate Monday to Friday of current week
		weekday := now.Weekday()
		daysFromMonday := int(weekday - time.Monday)
		if weekday == time.Sunday {
			daysFromMonday = 6 // Sunday is 6 days from Monday
		}

		startOfWeek := time.Date(now.Year(), now.Month(), now.Day()-daysFromMonday, 0, 0, 0, 0, loc)
		endOfWeek := startOfWeek.Add(5 * 24 * time.Hour) // Monday to Friday
		return startOfWeek, endOfWeek

	case "next_week":
		// Calculate Monday to Friday of next week
		weekday := now.Weekday()
		daysFromMonday := int(weekday - time.Monday)
		if weekday == time.Sunday {
			daysFromMonday = 6
		}

		startOfNextWeek := time.Date(now.Year(), now.Month(), now.Day()-daysFromMonday+7, 0, 0, 0, 0, loc)
		endOfNextWeek := startOfNextWeek.Add(5 * 24 * time.Hour)
		return startOfNextWeek, endOfNextWeek

	case "custom":
		if !customMin.IsZero() && !customMax.IsZero() {
			return customMin, customMax
		}
		fallthrough

	default:
		// Default to today
		startOfDay := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, loc)
		endOfDay := startOfDay.Add(24 * time.Hour)
		return startOfDay, endOfDay
	}
}

// Simple email regex for validation
var emailRegex = regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)

func isValidEmail(email string) bool {
	// Simple email validation
	return len(email) > 0 &&
		len(email) <= 254 &&
		emailRegex.MatchString(email)
}

// getUserEmail gets the authenticated user's email address
func (c *Client) getUserEmail() (string, error) {
	// Get the primary calendar to extract the user's email
	cal, err := c.service.Calendars.Get("primary").Do()
	if err != nil {
		return "", fmt.Errorf("failed to get primary calendar: %v", err)
	}

	if cal.Id == "" {
		return "", fmt.Errorf("unable to determine user email from primary calendar")
	}

	return cal.Id, nil
}

// GetCalendarColors gets the color definitions for calendars and events
func (c *Client) GetCalendarColors() (*calendar.Colors, error) {
	return c.service.Colors.Get().Do()
}
