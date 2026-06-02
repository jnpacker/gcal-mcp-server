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

package calendar

import (
	"testing"
	"time"

	"google.golang.org/api/calendar/v3"
)

// ----- isValidEmail -----

func TestIsValidEmail(t *testing.T) {
	cases := []struct {
		input string
		valid bool
	}{
		{"user@example.com", true},
		{"user.name+tag@sub.domain.org", true},
		{"a@b.io", true},
		{"", false},
		{"notanemail", false},
		{"missing@", false},
		{"@nodomain.com", false},
		{"spaces in@email.com", false},
	}
	for _, tc := range cases {
		got := isValidEmail(tc.input)
		if got != tc.valid {
			t.Errorf("isValidEmail(%q) = %v, want %v", tc.input, got, tc.valid)
		}
	}
}

// ----- stripRecurringInstanceSuffix -----

func TestStripRecurringInstanceSuffix(t *testing.T) {
	cases := []struct {
		input string
		want  string
	}{
		{"abc123_20260310", "abc123"},
		{"abc123_20260310T120000Z", "abc123"},
		{"abc123", "abc123"},                           // no suffix
		{"abc_def_20260310", "abc_def"},                // underscore in base ID
		{"abc_20260310T000000Z", "abc"},                // datetime suffix
	}
	for _, tc := range cases {
		got := stripRecurringInstanceSuffix(tc.input)
		if got != tc.want {
			t.Errorf("stripRecurringInstanceSuffix(%q) = %q, want %q", tc.input, got, tc.want)
		}
	}
}

// ----- eventsOverlap -----

func TestEventsOverlap(t *testing.T) {
	base := time.Date(2026, 1, 1, 9, 0, 0, 0, time.UTC)
	cases := []struct {
		name   string
		s1, e1 time.Time
		s2, e2 time.Time
		want   bool
	}{
		{
			"overlapping events",
			base, base.Add(2 * time.Hour),
			base.Add(time.Hour), base.Add(3 * time.Hour),
			true,
		},
		{
			"contained event",
			base, base.Add(4 * time.Hour),
			base.Add(time.Hour), base.Add(2 * time.Hour),
			true,
		},
		{
			"sequential events (touching)",
			base, base.Add(time.Hour),
			base.Add(time.Hour), base.Add(2 * time.Hour),
			false,
		},
		{
			"non-overlapping events",
			base, base.Add(time.Hour),
			base.Add(2 * time.Hour), base.Add(3 * time.Hour),
			false,
		},
		{
			"same event times",
			base, base.Add(time.Hour),
			base, base.Add(time.Hour),
			true,
		},
	}
	for _, tc := range cases {
		got := eventsOverlap(tc.s1, tc.e1, tc.s2, tc.e2)
		if got != tc.want {
			t.Errorf("%s: eventsOverlap = %v, want %v", tc.name, got, tc.want)
		}
	}
}

// ----- calculateTimeRange -----

func TestCalculateTimeRange_Today(t *testing.T) {
	start, end := calculateTimeRange("today", time.Time{}, time.Time{}, "UTC")
	now := time.Now().UTC()

	if start.Day() != now.Day() {
		t.Errorf("today start day = %d, want %d", start.Day(), now.Day())
	}
	if !end.After(start) {
		t.Error("end should be after start")
	}
	if end.Sub(start) != 24*time.Hour {
		t.Errorf("today range should be 24h, got %v", end.Sub(start))
	}
}

func TestCalculateTimeRange_ThisWeek(t *testing.T) {
	start, end := calculateTimeRange("this_week", time.Time{}, time.Time{}, "UTC")
	if end.Sub(start) != 5*24*time.Hour {
		t.Errorf("this_week range should be 5 days, got %v", end.Sub(start))
	}
	// start should be Monday
	if start.Weekday() != time.Monday {
		t.Errorf("this_week start should be Monday, got %v", start.Weekday())
	}
}

func TestCalculateTimeRange_NextWeek(t *testing.T) {
	start, end := calculateTimeRange("next_week", time.Time{}, time.Time{}, "UTC")
	if end.Sub(start) != 5*24*time.Hour {
		t.Errorf("next_week range should be 5 days, got %v", end.Sub(start))
	}
	if start.Weekday() != time.Monday {
		t.Errorf("next_week start should be Monday, got %v", start.Weekday())
	}
	// next week's Monday should be after this week's Monday
	thisStart, _ := calculateTimeRange("this_week", time.Time{}, time.Time{}, "UTC")
	if !start.After(thisStart) {
		t.Error("next_week start should be after this_week start")
	}
}

func TestCalculateTimeRange_Custom(t *testing.T) {
	min := time.Date(2026, 3, 1, 0, 0, 0, 0, time.UTC)
	max := time.Date(2026, 3, 31, 0, 0, 0, 0, time.UTC)

	start, end := calculateTimeRange("custom", min, max, "UTC")
	if !start.Equal(min) {
		t.Errorf("custom start = %v, want %v", start, min)
	}
	if !end.Equal(max) {
		t.Errorf("custom end = %v, want %v", end, max)
	}
}

func TestCalculateTimeRange_CustomEmpty_FallsBackToToday(t *testing.T) {
	// Custom with zero times falls back to today
	start, end := calculateTimeRange("custom", time.Time{}, time.Time{}, "UTC")
	if end.Sub(start) != 24*time.Hour {
		t.Errorf("empty custom should fall back to 24h today range, got %v", end.Sub(start))
	}
}

func TestCalculateTimeRange_InvalidTimezone(t *testing.T) {
	// Should not panic with invalid timezone — falls back to UTC
	start, end := calculateTimeRange("today", time.Time{}, time.Time{}, "Not/A/Zone")
	if !end.After(start) {
		t.Error("end should be after start even with invalid timezone")
	}
}

// ----- parseEventTimes -----

func TestParseEventTimes_TimedEvent(t *testing.T) {
	event := &calendar.Event{
		Start: &calendar.EventDateTime{DateTime: "2026-03-10T09:00:00Z"},
		End:   &calendar.EventDateTime{DateTime: "2026-03-10T10:00:00Z"},
	}
	start, end, allDay, err := parseEventTimes(event)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if allDay {
		t.Error("expected timed event, not all-day")
	}
	if end.Sub(start) != time.Hour {
		t.Errorf("expected 1h duration, got %v", end.Sub(start))
	}
}

func TestParseEventTimes_AllDayEvent(t *testing.T) {
	event := &calendar.Event{
		Start: &calendar.EventDateTime{Date: "2026-03-10"},
		End:   &calendar.EventDateTime{Date: "2026-03-11"},
	}
	_, _, allDay, err := parseEventTimes(event)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !allDay {
		t.Error("expected all-day event")
	}
}

func TestParseEventTimes_MissingTimes(t *testing.T) {
	event := &calendar.Event{}
	_, _, _, err := parseEventTimes(event)
	if err == nil {
		t.Error("expected error for event with missing start/end")
	}
}

func TestParseEventTimes_InvalidDateTime(t *testing.T) {
	event := &calendar.Event{
		Start: &calendar.EventDateTime{DateTime: "not-a-date"},
		End:   &calendar.EventDateTime{DateTime: "also-not-a-date"},
	}
	_, _, _, err := parseEventTimes(event)
	if err == nil {
		t.Error("expected error for invalid datetime string")
	}
}

// ----- NewClient and SearchAttendees (no service call needed) -----

func TestNewClient(t *testing.T) {
	c := NewClient(nil, nil)
	if c == nil {
		t.Fatal("NewClient should return a non-nil client")
	}
}

func TestSearchAttendees_ValidEmail(t *testing.T) {
	c := &Client{}
	results, err := c.SearchAttendees(AttendeeSearchParams{Query: "user@example.com"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(results) != 1 || results[0] != "user@example.com" {
		t.Errorf("expected [user@example.com], got %v", results)
	}
}

func TestSearchAttendees_InvalidEmail(t *testing.T) {
	c := &Client{}
	_, err := c.SearchAttendees(AttendeeSearchParams{Query: "notanemail"})
	if err == nil {
		t.Error("expected error for non-email query")
	}
}

// ----- DetectOverlaps -----

func TestDetectOverlaps_NoOverlap(t *testing.T) {
	c := &Client{}
	now := time.Date(2026, 1, 1, 9, 0, 0, 0, time.UTC)
	events := []*calendar.Event{
		{
			Id:    "e1",
			Start: &calendar.EventDateTime{DateTime: now.Format(time.RFC3339)},
			End:   &calendar.EventDateTime{DateTime: now.Add(time.Hour).Format(time.RFC3339)},
		},
		{
			Id:    "e2",
			Start: &calendar.EventDateTime{DateTime: now.Add(2 * time.Hour).Format(time.RFC3339)},
			End:   &calendar.EventDateTime{DateTime: now.Add(3 * time.Hour).Format(time.RFC3339)},
		},
	}
	overlaps := c.DetectOverlaps(events, false)
	if overlaps["e1"] {
		t.Error("e1 should not be marked as overlapping")
	}
	if overlaps["e2"] {
		t.Error("e2 should not be marked as overlapping")
	}
}

func TestDetectOverlaps_WithOverlap(t *testing.T) {
	c := &Client{}
	now := time.Date(2026, 1, 1, 9, 0, 0, 0, time.UTC)
	events := []*calendar.Event{
		{
			Id:    "e1",
			Start: &calendar.EventDateTime{DateTime: now.Format(time.RFC3339)},
			End:   &calendar.EventDateTime{DateTime: now.Add(2 * time.Hour).Format(time.RFC3339)},
		},
		{
			Id:    "e2",
			Start: &calendar.EventDateTime{DateTime: now.Add(time.Hour).Format(time.RFC3339)},
			End:   &calendar.EventDateTime{DateTime: now.Add(3 * time.Hour).Format(time.RFC3339)},
		},
	}
	overlaps := c.DetectOverlaps(events, false)
	if !overlaps["e1"] {
		t.Error("e1 should be marked as overlapping")
	}
	if !overlaps["e2"] {
		t.Error("e2 should be marked as overlapping")
	}
}

func TestDetectOverlaps_AllDayEventsSkipped(t *testing.T) {
	c := &Client{}
	// All-day events should be skipped in overlap detection
	events := []*calendar.Event{
		{
			Id:    "allday1",
			Start: &calendar.EventDateTime{Date: "2026-01-01"},
			End:   &calendar.EventDateTime{Date: "2026-01-02"},
		},
		{
			Id:    "allday2",
			Start: &calendar.EventDateTime{Date: "2026-01-01"},
			End:   &calendar.EventDateTime{Date: "2026-01-02"},
		},
	}
	overlaps := c.DetectOverlaps(events, false)
	if overlaps["allday1"] {
		t.Error("all-day events should not be marked as overlapping")
	}
}

func TestDetectOverlaps_Empty(t *testing.T) {
	c := &Client{}
	overlaps := c.DetectOverlaps(nil, false)
	if len(overlaps) != 0 {
		t.Errorf("expected empty overlaps map, got %d entries", len(overlaps))
	}
}

// isEventDeclined is only testable when attendees is nil (no API call needed)
func TestIsEventDeclined_NoAttendees(t *testing.T) {
	c := &Client{}
	event := &calendar.Event{Attendees: nil}
	if c.isEventDeclined(event) {
		t.Error("event with no attendees should not be declined")
	}
}

// ----- parseFileID -----

func TestParseFileID(t *testing.T) {
	cases := []struct {
		input string
		want  string
	}{
		{"https://docs.google.com/document/d/abc123XYZ/edit", "abc123XYZ"},
		{"https://drive.google.com/file/d/xyz789/view", "xyz789"},
		{"rawfileid", "rawfileid"},
		{"", ""},
	}
	for _, tc := range cases {
		got := parseFileID(tc.input)
		if got != tc.want {
			t.Errorf("parseFileID(%q) = %q, want %q", tc.input, got, tc.want)
		}
	}
}
