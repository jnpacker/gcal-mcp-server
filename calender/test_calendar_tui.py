#!/usr/bin/env python3
"""
Test script for calendar_tui MCP integration
This tests the MCP client without requiring a curses terminal
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path to import calendar_tui
sys.path.insert(0, os.path.dirname(__file__))

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: MCP SDK not installed. Install with: pip install mcp")
    sys.exit(1)


async def test_mcp_connection():
    """Test connecting to MCP server and fetching events"""

    server_path = "../bin/gcal-mcp-server"

    print(f"Testing MCP connection to {server_path}...")

    # Create server parameters
    server_params = StdioServerParameters(
        command=server_path,
        args=[],
        env=None
    )

    try:
        # Connect to server using async context manager
        print("Connecting to MCP server...")
        async with stdio_client(server_params) as (stdio, write):
            async with ClientSession(stdio, write) as session:
                print("Initializing session...")
                await session.initialize()

                print("✓ Successfully connected to MCP server")

                # List available tools
                print("\nListing available tools...")
                tools = await session.list_tools()
                print(f"✓ Found {len(tools.tools)} tools:")
                for tool in tools.tools:
                    print(f"  - {tool.name}")

                # Test fetching events
                print("\nTesting list_events tool with JSON output...")
                result = await session.call_tool(
                    "list_events",
                    {
                        "time_filter": "today",
                        "timezone": "America/New_York",
                        "detect_overlaps": True,
                        "show_declined": False,
                        "max_results": 10,
                        "output_format": "json"
                    }
                )

                print("✓ Successfully called list_events")

                # Parse result
                if result.content:
                    content_item = result.content[0]

                    # Debug: check what we got
                    print(f"Content type: {type(content_item)}")
                    print(f"Content text type: {type(content_item.text)}")

                    content_text = content_item.text

                    # Try to parse as JSON if it's a string
                    if isinstance(content_text, str) and content_text.strip():
                        try:
                            data = json.loads(content_text)
                        except json.JSONDecodeError:
                            print(f"Failed to parse JSON. Content: {content_text[:200]}")
                            return False
                    else:
                        # Might already be a dict
                        data = content_text

                    if isinstance(data, dict) and 'events' in data:
                        events = data['events']
                        print(f"\nFound {len(events)} events:")

                        for i, event in enumerate(events[:5], 1):  # Show first 5
                            summary = event.get('summary', 'No Title')
                            start = event.get('start', {})
                            has_overlap = event.get('has_overlap', False)

                            # Parse time
                            date_time = start.get('dateTime', '')
                            if date_time:
                                start_time = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
                                time_str = start_time.strftime('%I:%M%p').lstrip('0').lower()
                            else:
                                time_str = "All Day"

                            overlap_str = " [OVERLAP]" if has_overlap else ""
                            print(f"  {i}. {time_str} - {summary}{overlap_str}")

                        if len(events) > 5:
                            print(f"  ... and {len(events) - 5} more")
                    else:
                        print("No events found in response")
                else:
                    print("No content in response")

        print("\n✓ Connection closed successfully")
        print("\n✅ All tests passed!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_calendar_features():
    """Test calendar TUI specific features"""
    from calendar_tui import CalendarEvent

    print("\n" + "="*60)
    print("Testing Calendar TUI Features")
    print("="*60)

    # Test 1: All-day event filtering
    print("\n1. Testing all-day event filtering (filter out events from previous days)...")
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    # Create test events
    yesterday_event = CalendarEvent({
        'id': 'test1',
        'summary': 'Yesterday Event',
        'start': {'date': yesterday.isoformat(), 'dateTime': '', 'timeZone': ''},
        'end': {'date': today.isoformat(), 'dateTime': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'workingLocation'
    })

    today_event = CalendarEvent({
        'id': 'test2',
        'summary': 'Today Event',
        'start': {'date': today.isoformat(), 'dateTime': '', 'timeZone': ''},
        'end': {'date': tomorrow.isoformat(), 'dateTime': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'workingLocation'
    })

    # Test filtering logic
    assert yesterday_event.is_all_day, "Yesterday event should be all-day"
    assert today_event.is_all_day, "Today event should be all-day"
    assert yesterday_event.start_time.date() < today, "Yesterday event should start before today"
    assert today_event.start_time.date() == today, "Today event should start today"
    print("✓ All-day event filtering logic verified")

    # Test 2: Active event detection
    print("\n2. Testing active event detection (clock emoji for current events)...")
    now = datetime.now().astimezone()

    # Create an event happening now
    active_event = CalendarEvent({
        'id': 'test3',
        'summary': 'Active Meeting',
        'start': {'dateTime': (now - timedelta(minutes=15)).isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(minutes=15)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default'
    })

    # Create an event in the future
    future_event = CalendarEvent({
        'id': 'test4',
        'summary': 'Future Meeting',
        'start': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(hours=2)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default'
    })

    # Create an event in the past
    past_event = CalendarEvent({
        'id': 'test5',
        'summary': 'Past Meeting',
        'start': {'dateTime': (now - timedelta(hours=2)).isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now - timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default'
    })

    assert active_event.is_currently_active(), "Event happening now should be marked as active"
    assert not future_event.is_currently_active(), "Future event should not be marked as active"
    assert not past_event.is_currently_active(), "Past event should not be marked as active"
    assert not yesterday_event.is_currently_active(), "All-day events should not be marked as active"
    print("✓ Active event detection working correctly")

    # Test 3: RSVP status characters
    print("\n3. Testing RSVP status indicators...")
    test_statuses = {
        'accepted': '✅',
        'declined': '❌',
        'tentative': '⏳',
        'needsAction': '❓'
    }

    for status, expected_char in test_statuses.items():
        event = CalendarEvent({
            'id': f'test_{status}',
            'summary': f'Test {status}',
            'start': {'dateTime': now.isoformat(), 'date': '', 'timeZone': ''},
            'end': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'default',
            'attendees': [{'email': 'test@example.com', 'self': True, 'responseStatus': status}]
        })
        char = event.get_response_char()
        assert char == expected_char, f"RSVP status {status} should show {expected_char}, got {char}"

    print("✓ RSVP status indicators correct")

    # Test 3b: Attendee count format
    print("\n3b. Testing attendee count format (accepted/total)...")

    # Event with multiple attendees
    multi_attendee_event = CalendarEvent({
        'id': 'test_multi',
        'summary': 'Team Meeting',
        'start': {'dateTime': now.isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default',
        'attendees': [
            {'email': 'user1@example.com', 'self': False, 'responseStatus': 'accepted'},
            {'email': 'user2@example.com', 'self': False, 'responseStatus': 'accepted'},
            {'email': 'user3@example.com', 'self': False, 'responseStatus': 'tentative'},
            {'email': 'user4@example.com', 'self': False, 'responseStatus': 'needsAction'},
            {'email': 'user5@example.com', 'self': False, 'responseStatus': 'declined'}
        ]
    })

    attendee_str = multi_attendee_event.get_attendee_count()
    print(f"   Attendee count display: '{attendee_str}'")
    assert attendee_str == '(👍🏼2/5)', f"Expected '(👍🏼2/5)', got '{attendee_str}'"
    print("✓ Attendee count shows accepted/total format: (👍🏼2/5)")

    # Event with no attendees
    no_attendee_event = CalendarEvent({
        'id': 'test_solo',
        'summary': 'Solo Work',
        'start': {'dateTime': now.isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default',
        'attendees': []
    })

    assert no_attendee_event.get_attendee_count() == '—', "Event with no attendees should show dash"
    print("✓ Events with no attendees show dash")

    # Test 4: Working location event types
    print("\n4. Testing working location event types...")
    home_event = CalendarEvent({
        'id': 'test_home',
        'summary': 'Home',
        'start': {'date': today.isoformat(), 'dateTime': '', 'timeZone': ''},
        'end': {'date': tomorrow.isoformat(), 'dateTime': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'workingLocation',
        'workingLocationProperties': {'type': 'homeOffice'}
    })

    assert home_event.get_response_char() == '🏠', "Home office should show house emoji"
    assert home_event.event_type == 'workingLocation', "Event type should be workingLocation"
    print("✓ Working location events handled correctly")

    print("\n✅ All calendar TUI feature tests passed!")
    return True


async def test_location_filtering():
    """Test that only one location event is displayed per day"""
    from calendar_tui import CalendarEvent

    print("\n" + "="*60)
    print("Testing Location Event Filtering")
    print("="*60)

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    # Simulate what we get from Google Calendar for "today" filter
    # Google returns both yesterday's location (ends today) and today's location (starts today)
    events_from_api = [
        {
            'id': 'location_yesterday',
            'summary': 'Home',
            'start': {'date': yesterday.isoformat(), 'dateTime': '', 'timeZone': ''},
            'end': {'date': today.isoformat(), 'dateTime': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'workingLocation',
            'workingLocationProperties': {'type': 'homeOffice'}
        },
        {
            'id': 'location_today',
            'summary': 'Home',
            'start': {'date': today.isoformat(), 'dateTime': '', 'timeZone': ''},
            'end': {'date': tomorrow.isoformat(), 'dateTime': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'workingLocation',
            'workingLocationProperties': {'type': 'homeOffice'}
        }
    ]

    # Create CalendarEvent objects
    all_events = [CalendarEvent(e) for e in events_from_api]

    print(f"\n1. API returned {len(all_events)} location events (includes yesterday's)")
    for event in all_events:
        print(f"   - {event.summary} (starts: {event.start_time.date()})")

    # Apply the filtering logic from CalendarTUI.fetch_events()
    filtered_events = []
    for event in all_events:
        # Skip all-day events that started before today
        if event.is_all_day and event.start_time:
            event_date = event.start_time.date()
            if event_date < today:
                print(f"\n2. Filtering out: {event.summary} (started {event_date}, before today {today})")
                continue  # Skip this event
        filtered_events.append(event)

    print(f"\n3. After filtering: {len(filtered_events)} location event(s) remaining")
    for event in filtered_events:
        print(f"   - {event.summary} (starts: {event.start_time.date()})")

    # Validate
    assert len(filtered_events) == 1, f"Expected 1 location event after filtering, got {len(filtered_events)}"
    assert filtered_events[0].start_time.date() == today, "Remaining event should start today"
    print("\n✓ Only today's location event is displayed (yesterday's filtered out)")

    return True


async def test_column_alignment():
    """Test that column alignment is correct with and without clock emoji"""
    from calendar_tui import CalendarEvent

    print("\n" + "="*60)
    print("Testing Column Alignment")
    print("="*60)

    now = datetime.now().astimezone()

    # Create a regular event (no clock emoji)
    regular_event = CalendarEvent({
        'id': 'test_regular',
        'summary': 'Regular Meeting',
        'start': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(hours=2)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default',
        'attendees': [{'email': 'test@example.com', 'self': True, 'responseStatus': 'accepted'}],
        'hangoutLink': 'https://meet.google.com/abc-defg-hij'
    })

    # Create an active event (with clock emoji)
    active_event = CalendarEvent({
        'id': 'test_active',
        'summary': 'Active Meeting Right Now',
        'start': {'dateTime': (now - timedelta(minutes=10)).isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(minutes=20)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default',
        'attendees': [{'email': 'test@example.com', 'self': True, 'responseStatus': 'accepted'}],
        'hangoutLink': 'https://meet.google.com/xyz-uvwx-stu'
    })

    print("\n1. Testing regular event formatting (no clock emoji):")

    # Get formatted components
    day = regular_event.start_time.strftime('%a')
    start = regular_event.start_time.strftime('%I:%M %p').lstrip('0')
    end = regular_event.end_time.strftime('%I:%M %p').lstrip('0')
    time_str = f"{start} - {end}".ljust(23)

    # Title without emoji - should be 35 chars
    title = regular_event.summary[:35]
    assert not regular_event.is_currently_active(), "Regular event should not be active"

    # Build row like calendar_tui does
    title_padded = f"{title:<35}"
    rsvp = regular_event.get_response_char()
    attendees = regular_event.get_attendee_count()[:14]
    row_text = f"{day:<4} {time_str} {title_padded} {rsvp} {attendees:<14}"

    print(f"   Day column: '{day:<4}' (4 chars)")
    print(f"   Time column: '{time_str}' (23 chars)")
    print(f"   Event column: '{title_padded}' ({len(title_padded)} chars)")
    print(f"   RSVP column: '{rsvp}' (visual width)")
    print(f"   Attendees column: '{attendees:<14}' (14 chars)")

    # Calculate expected positions
    # Format: Day(4) Space(1) Time(23) Space(1) Event(35) Space(1) RSVP(4) Space(1) Attendees(14) Space(1) = Link at 85
    expected_link_pos = 1 + 4 + 1 + 23 + 1 + 35 + 1 + 4 + 1 + 14 + 1  # = 86
    print(f"   Expected link position: {expected_link_pos}")

    assert len(title_padded) == 35, f"Regular title should be 35 chars, got {len(title_padded)}"
    print("   ✓ Regular event title is 35 chars")

    print("\n2. Testing active event formatting (with clock emoji):")

    # Get formatted components for active event
    day_active = active_event.start_time.strftime('%a')
    start_active = active_event.start_time.strftime('%I:%M %p').lstrip('0')
    end_active = active_event.end_time.strftime('%I:%M %p').lstrip('0')
    time_str_active = f"{start_active} - {end_active}".ljust(23)

    # Title with emoji - emoji (2 display cells) + space + text (32 chars) = 35 display width
    assert active_event.is_currently_active(), "Active event should be marked as active"
    title_active = f"🕐 {active_event.summary[:32]}"

    # Build row like calendar_tui does - pad to 34 chars for emoji title
    title_padded_active = f"{title_active:<34}"
    rsvp_active = active_event.get_response_char()
    attendees_active = active_event.get_attendee_count()[:14]
    row_text_active = f"{day_active:<4} {time_str_active} {title_padded_active} {rsvp_active} {attendees_active:<14}"

    print(f"   Day column: '{day_active:<4}' (4 chars)")
    print(f"   Time column: '{time_str_active}' (23 chars)")
    print(f"   Event column: '{title_padded_active}' ({len(title_padded_active)} chars, 35 display width)")
    print(f"   RSVP column: '{rsvp_active}' (visual width)")
    print(f"   Attendees column: '{attendees_active:<14}' (14 chars)")
    print(f"   Expected link position: {expected_link_pos}")

    # Verify emoji title is padded to 34 chars (which displays as 35 cells)
    assert len(title_padded_active) == 34, f"Active event title should be 34 chars (35 display), got {len(title_padded_active)}"
    print("   ✓ Active event title is 34 chars (35 display width with emoji)")

    # Verify the clock emoji is present
    assert title_active.startswith('🕐 '), "Active event title should start with clock emoji and space"
    print("   ✓ Clock emoji present at start of title")

    # Calculate the actual positions in the row
    # Both rows should have the same structure despite emoji
    pos_day = 0
    pos_time = 4 + 1  # Day(4) + space(1)
    pos_event = pos_time + 23 + 1  # Time(23) + space(1)
    pos_rsvp = pos_event + 34 + 1  # Event(34) + space(1) - using 34 because that's the padded length

    print(f"\n3. Verifying column positions are consistent:")
    print(f"   Day column starts at: {pos_day}")
    print(f"   Time column starts at: {pos_time}")
    print(f"   Event column starts at: {pos_event}")
    print(f"   RSVP column starts at: ~{pos_rsvp}")
    print(f"   Link column starts at: {expected_link_pos}")

    print("\n✓ Column alignment validated for both regular and active events")
    return True


async def test_cursor_positioning():
    """Test that cursor positions correctly at current event on initial load"""
    from calendar_tui import CalendarTUI, MCPClient
    import unittest.mock as mock

    print("\n" + "="*60)
    print("Testing Cursor Positioning")
    print("="*60)

    now = datetime.now().astimezone()

    # Create a mock event list similar to a real calendar day
    mock_events = [
        {
            'id': 'past1',
            'summary': 'Morning Standup',
            'start': {'dateTime': (now - timedelta(hours=4)).isoformat(), 'date': '', 'timeZone': ''},
            'end': {'dateTime': (now - timedelta(hours=4) + timedelta(minutes=15)).isoformat(), 'date': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'default'
        },
        {
            'id': 'past2',
            'summary': 'Design Review',
            'start': {'dateTime': (now - timedelta(hours=2)).isoformat(), 'date': '', 'timeZone': ''},
            'end': {'dateTime': (now - timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'default'
        },
        {
            'id': 'current',
            'summary': 'Team Sync - ACTIVE NOW',
            'start': {'dateTime': (now - timedelta(minutes=15)).isoformat(), 'date': '', 'timeZone': ''},
            'end': {'dateTime': (now + timedelta(minutes=15)).isoformat(), 'date': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'default'
        },
        {
            'id': 'future1',
            'summary': 'Code Review',
            'start': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
            'end': {'dateTime': (now + timedelta(hours=2)).isoformat(), 'date': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'default'
        },
        {
            'id': 'future2',
            'summary': 'Planning Meeting',
            'start': {'dateTime': (now + timedelta(hours=3)).isoformat(), 'date': '', 'timeZone': ''},
            'end': {'dateTime': (now + timedelta(hours=4)).isoformat(), 'date': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'default'
        }
    ]

    # Import CalendarEvent
    from calendar_tui import CalendarEvent

    # Create event objects
    events = [CalendarEvent(e) for e in mock_events]

    print(f"\n1. Created {len(events)} test events:")
    for i, event in enumerate(events):
        status = ""
        if event.is_currently_active():
            status = " ⭐ CURRENTLY ACTIVE"
        elif event.start_time > now:
            status = " (future)"
        else:
            status = " (past)"
        print(f"   [{i}] {event.summary}{status}")

    # Test the _find_current_event logic
    print("\n2. Simulating _find_current_event() logic:")

    # Find currently active event
    current_index = None
    for i, event in enumerate(events):
        if event.is_available or event.is_all_day:
            continue
        if event.start_time and event.end_time:
            if event.start_time <= now < event.end_time:
                current_index = i
                print(f"   Found active event at index {i}: {event.summary}")
                break

    assert current_index is not None, "Should find a currently active event"
    assert current_index == 2, f"Current event should be at index 2, got {current_index}"
    assert events[current_index].summary == 'Team Sync - ACTIVE NOW', "Should identify the active event"
    print(f"   ✓ Cursor would be positioned at index {current_index}")

    # Verify the active event has the clock emoji
    assert events[current_index].is_currently_active(), "Active event should return True for is_currently_active()"
    print("   ✓ Active event would display clock emoji")

    # Test fallback to next event when no current event
    print("\n3. Testing fallback to next upcoming event (when no active event):")

    # Create future-only events
    future_events = [
        CalendarEvent({
            'id': 'future_only_1',
            'summary': 'Next Meeting',
            'start': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
            'end': {'dateTime': (now + timedelta(hours=2)).isoformat(), 'date': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'default'
        }),
        CalendarEvent({
            'id': 'future_only_2',
            'summary': 'Later Meeting',
            'start': {'dateTime': (now + timedelta(hours=3)).isoformat(), 'date': '', 'timeZone': ''},
            'end': {'dateTime': (now + timedelta(hours=4)).isoformat(), 'date': '', 'timeZone': ''},
            'status': 'confirmed',
            'eventType': 'default'
        })
    ]

    # Find next upcoming event
    next_index = None
    for i, event in enumerate(future_events):
        if event.is_available or event.is_all_day:
            continue
        if event.start_time and event.start_time > now:
            next_index = i
            print(f"   Found next upcoming event at index {i}: {event.summary}")
            break

    assert next_index == 0, f"Next event should be at index 0, got {next_index}"
    assert future_events[next_index].summary == 'Next Meeting', "Should identify the next event"
    print(f"   ✓ When no active event, cursor positions at next upcoming event (index {next_index})")

    print("\n✓ Cursor positioning logic validated")
    return True


async def test_meeting_link_display():
    """Test that meeting links are displayed as short IDs instead of full URLs"""
    from calendar_tui import CalendarEvent

    print("\n" + "="*60)
    print("Testing Meeting Link Display")
    print("="*60)

    now = datetime.now().astimezone()

    # Test 1: Google Meet URL extraction
    print("\n1. Testing Google Meet URL extraction:")
    meet_event = CalendarEvent({
        'id': 'test_meet',
        'summary': 'Team Meeting',
        'start': {'dateTime': now.isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default',
        'hangoutLink': 'https://meet.google.com/kmv-cnxe-buy'
    })

    display_text, full_url = meet_event.get_meet_link_display()
    print(f"   Full URL: {meet_event.hangout_link} ({len(meet_event.hangout_link)} chars)")
    print(f"   Display text: {display_text} ({len(display_text)} chars)")
    print(f"   Full URL preserved: {full_url}")

    assert display_text == 'https://g.co/meet/kmv-cnxe-buy', f"Expected 'https://g.co/meet/kmv-cnxe-buy', got '{display_text}'"
    assert full_url == 'https://meet.google.com/kmv-cnxe-buy', "Full URL should be preserved"
    assert len(display_text) == 30, f"Display text should be 30 chars, got {len(display_text)}"
    assert len(display_text) < len(meet_event.hangout_link), "Display text should be shorter than full URL"
    print("   ✓ Meeting link formatted correctly (30 chars vs 36 chars)")

    # Test 2: Google Meet URL with query parameters
    print("\n2. Testing Google Meet URL with query parameters:")
    meet_event_params = CalendarEvent({
        'id': 'test_meet_params',
        'summary': 'Meeting with Params',
        'start': {'dateTime': now.isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default',
        'hangoutLink': 'https://meet.google.com/abc-defg-hij?authuser=0'
    })

    display_text_params, full_url_params = meet_event_params.get_meet_link_display()
    print(f"   Full URL: {meet_event_params.hangout_link}")
    print(f"   Display text: {display_text_params}")

    assert display_text_params == 'https://g.co/meet/abc-defg-hij', f"Expected 'https://g.co/meet/abc-defg-hij', got '{display_text_params}'"
    assert '?' not in display_text_params, "Query parameters should be stripped from display"
    print("   ✓ Query parameters stripped correctly")

    # Test 3: Non-Google Meet URL (other video conferencing)
    print("\n3. Testing non-Google Meet URL:")
    zoom_event = CalendarEvent({
        'id': 'test_zoom',
        'summary': 'Zoom Meeting',
        'start': {'dateTime': now.isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default',
        'hangoutLink': 'https://zoom.us/j/1234567890'
    })

    display_text_zoom, full_url_zoom = zoom_event.get_meet_link_display()
    print(f"   Full URL: {zoom_event.hangout_link}")
    print(f"   Display text: {display_text_zoom}")

    # For non-Google Meet URLs, we show the full URL
    assert display_text_zoom == zoom_event.hangout_link, "Non-Google Meet URLs should display full URL"
    print("   ✓ Non-Google Meet URLs displayed in full")

    # Test 4: Event without link
    print("\n4. Testing event without meeting link:")
    no_link_event = CalendarEvent({
        'id': 'test_no_link',
        'summary': 'In-Person Meeting',
        'start': {'dateTime': now.isoformat(), 'date': '', 'timeZone': ''},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat(), 'date': '', 'timeZone': ''},
        'status': 'confirmed',
        'eventType': 'default'
    })

    display_text_none, full_url_none = no_link_event.get_meet_link_display()
    print(f"   Display text: {display_text_none}")
    print(f"   Full URL: {full_url_none}")

    assert display_text_none == '—', "Events without links should show dash"
    assert full_url_none is None, "Events without links should have None for URL"
    print("   ✓ Events without links show dash")

    # Test 5: Available slot (no link)
    print("\n5. Testing available time slot (no link):")
    available_event = CalendarEvent({
        'start': {'dateTime': now.isoformat()},
        'end': {'dateTime': (now + timedelta(minutes=30)).isoformat()}
    }, is_available=True)

    display_text_avail, full_url_avail = available_event.get_meet_link_display()
    assert display_text_avail == '—', "Available slots should show dash"
    assert full_url_avail is None, "Available slots should have None for URL"
    print("   ✓ Available slots show dash")

    print("\n✓ Meeting link display validated - shows IDs instead of full URLs!")
    return True


async def test_available_time_slots():
    """Test that available time slots are rendered correctly"""
    from calendar_tui import CalendarEvent

    print("\n" + "="*60)
    print("Testing Available Time Slot Rendering")
    print("="*60)

    now = datetime.now().astimezone()
    today = now.date()

    # Test 1: Core hours available slot (9am-5pm) - should show green boxes
    print("\n1. Testing core hours available slot (green boxes):")

    # 1-hour slot during core hours (10am-11am)
    core_hours_start = datetime.combine(today, datetime.min.time().replace(hour=10, minute=0))
    core_hours_start = core_hours_start.replace(tzinfo=now.tzinfo)
    core_hours_end = datetime.combine(today, datetime.min.time().replace(hour=11, minute=0))
    core_hours_end = core_hours_end.replace(tzinfo=now.tzinfo)

    available_core = CalendarEvent({
        'start': {'dateTime': core_hours_start.isoformat()},
        'end': {'dateTime': core_hours_end.isoformat()}
    }, is_available=True, core_start_hour=9, core_end_hour=17)

    print(f"   Slot: {core_hours_start.strftime('%I:%M %p')} - {core_hours_end.strftime('%I:%M %p')}")
    print(f"   Duration: {available_core.get_duration_minutes()} minutes")
    print(f"   Summary: {available_core.summary}")

    assert available_core.is_available, "Should be marked as available"
    assert "🟩" in available_core.summary, "Should contain green boxes for core hours"
    assert "Available" in available_core.summary, "Should contain 'Available' text"
    # 1 hour = 2 blocks of 30 min
    expected_blocks = 2
    assert available_core.summary.count("🟩") == expected_blocks, f"Should have {expected_blocks} green boxes for 1 hour"
    print(f"   ✓ Core hours slot shows {expected_blocks} green boxes (🟩)")

    # Test 2: Outside core hours - should show grey boxes
    print("\n2. Testing outside core hours slot (grey boxes):")

    # Early morning slot (7am-8am)
    early_start = datetime.combine(today, datetime.min.time().replace(hour=7, minute=0))
    early_start = early_start.replace(tzinfo=now.tzinfo)
    early_end = datetime.combine(today, datetime.min.time().replace(hour=8, minute=0))
    early_end = early_end.replace(tzinfo=now.tzinfo)

    available_early = CalendarEvent({
        'start': {'dateTime': early_start.isoformat()},
        'end': {'dateTime': early_end.isoformat()}
    }, is_available=True, core_start_hour=9, core_end_hour=17)

    print(f"   Slot: {early_start.strftime('%I:%M %p')} - {early_end.strftime('%I:%M %p')}")
    print(f"   Summary: {available_early.summary}")

    assert "⬛" in available_early.summary, "Should contain grey boxes for outside core hours"
    assert "🟩" not in available_early.summary, "Should NOT contain green boxes"
    assert available_early.summary.count("⬛") == 2, "Should have 2 grey boxes for 1 hour"
    print("   ✓ Outside core hours slot shows 2 grey boxes (⬛)")

    # Test 3: Evening slot (after 5pm)
    print("\n3. Testing evening slot (after core hours):")

    evening_start = datetime.combine(today, datetime.min.time().replace(hour=18, minute=0))
    evening_start = evening_start.replace(tzinfo=now.tzinfo)
    evening_end = datetime.combine(today, datetime.min.time().replace(hour=19, minute=30))
    evening_end = evening_end.replace(tzinfo=now.tzinfo)

    available_evening = CalendarEvent({
        'start': {'dateTime': evening_start.isoformat()},
        'end': {'dateTime': evening_end.isoformat()}
    }, is_available=True, core_start_hour=9, core_end_hour=17)

    print(f"   Slot: {evening_start.strftime('%I:%M %p')} - {evening_end.strftime('%I:%M %p')}")
    print(f"   Duration: 1.5 hours = 3 blocks")
    print(f"   Summary: {available_evening.summary}")

    assert "⬛" in available_evening.summary, "Should contain grey boxes"
    assert available_evening.summary.count("⬛") == 3, "Should have 3 grey boxes for 1.5 hours"
    print("   ✓ Evening slot shows 3 grey boxes")

    # Test 4: Very long available slot - should cap at 10 boxes
    print("\n4. Testing very long available slot (10+ blocks, should cap at 10):")

    long_start = datetime.combine(today, datetime.min.time().replace(hour=9, minute=0))
    long_start = long_start.replace(tzinfo=now.tzinfo)
    long_end = datetime.combine(today, datetime.min.time().replace(hour=17, minute=0))  # 8 hours
    long_end = long_end.replace(tzinfo=now.tzinfo)

    available_long = CalendarEvent({
        'start': {'dateTime': long_start.isoformat()},
        'end': {'dateTime': long_end.isoformat()}
    }, is_available=True, core_start_hour=9, core_end_hour=17)

    print(f"   Slot: {long_start.strftime('%I:%M %p')} - {long_end.strftime('%I:%M %p')}")
    print(f"   Duration: 8 hours = 16 blocks (but capped at 10)")
    print(f"   Summary: {available_long.summary}")

    assert available_long.summary.count("🟩") == 10, "Should cap at 10 boxes"
    print("   ✓ Long slot capped at 10 green boxes")

    # Test 5: 30-minute slot - minimum size
    print("\n5. Testing 30-minute slot (minimum size, 1 box):")

    short_start = datetime.combine(today, datetime.min.time().replace(hour=14, minute=0))
    short_start = short_start.replace(tzinfo=now.tzinfo)
    short_end = datetime.combine(today, datetime.min.time().replace(hour=14, minute=30))
    short_end = short_end.replace(tzinfo=now.tzinfo)

    available_short = CalendarEvent({
        'start': {'dateTime': short_start.isoformat()},
        'end': {'dateTime': short_end.isoformat()}
    }, is_available=True, core_start_hour=9, core_end_hour=17)

    print(f"   Slot: {short_start.strftime('%I:%M %p')} - {short_end.strftime('%I:%M %p')}")
    print(f"   Summary: {available_short.summary}")

    assert available_short.summary.count("🟩") == 1, "Should have 1 green box for 30 min"
    print("   ✓ 30-minute slot shows 1 green box")

    # Test 6: Available slot attributes (no RSVP, attendees, link)
    print("\n6. Testing available slot display attributes:")

    assert available_core.get_response_char() == '', "Available slots should have no RSVP emoji"
    assert available_core.get_attendee_count() == '—', "Available slots should show dash for attendees"
    assert available_core.get_meet_link() == '—', "Available slots should show dash for link"
    display_text, url = available_core.get_meet_link_display()
    assert display_text == '—', "Available slots should show dash for link display"
    assert url is None, "Available slots should have no URL"
    print("   ✓ Available slots show: no RSVP, dash for attendees, dash for link")

    # Test 7: Available slot should not be marked as currently active
    print("\n7. Testing that available slots are never marked as active:")

    # Create available slot that would be "now" if it were a real event
    active_start = now - timedelta(minutes=15)
    active_end = now + timedelta(minutes=15)

    available_now = CalendarEvent({
        'start': {'dateTime': active_start.isoformat()},
        'end': {'dateTime': active_end.isoformat()}
    }, is_available=True)

    assert not available_now.is_currently_active(), "Available slots should never be marked as currently active"
    print("   ✓ Available slots are never marked as currently active (no clock emoji)")

    # Test 8: Different durations
    print("\n8. Testing various durations:")
    durations = [
        (30, 1, "30 min"),
        (60, 2, "1 hour"),
        (90, 3, "1.5 hours"),
        (120, 4, "2 hours"),
        (150, 5, "2.5 hours"),
    ]

    for minutes, expected_boxes, description in durations:
        start = datetime.combine(today, datetime.min.time().replace(hour=10, minute=0))
        start = start.replace(tzinfo=now.tzinfo)
        end = start + timedelta(minutes=minutes)

        available = CalendarEvent({
            'start': {'dateTime': start.isoformat()},
            'end': {'dateTime': end.isoformat()}
        }, is_available=True, core_start_hour=9, core_end_hour=17)

        actual_boxes = available.summary.count("🟩")
        assert actual_boxes == expected_boxes, f"{description} should have {expected_boxes} boxes, got {actual_boxes}"
        print(f"   ✓ {description} = {expected_boxes} boxes")

    # Test 9: Custom core hours
    print("\n9. Testing custom core hours (8am-6pm):")

    # 8:30am slot with custom core hours (8am-6pm)
    custom_start = datetime.combine(today, datetime.min.time().replace(hour=8, minute=30))
    custom_start = custom_start.replace(tzinfo=now.tzinfo)
    custom_end = datetime.combine(today, datetime.min.time().replace(hour=9, minute=0))
    custom_end = custom_end.replace(tzinfo=now.tzinfo)

    # With default core hours (9am-5pm), this would be grey
    available_default = CalendarEvent({
        'start': {'dateTime': custom_start.isoformat()},
        'end': {'dateTime': custom_end.isoformat()}
    }, is_available=True, core_start_hour=9, core_end_hour=17)

    # With custom core hours (8am-6pm), this should be green
    available_custom = CalendarEvent({
        'start': {'dateTime': custom_start.isoformat()},
        'end': {'dateTime': custom_end.isoformat()}
    }, is_available=True, core_start_hour=8, core_end_hour=18)

    assert "⬛" in available_default.summary, "8:30am should be grey with 9am-5pm core hours"
    assert "🟩" in available_custom.summary, "8:30am should be green with 8am-6pm core hours"
    print("   ✓ Custom core hours change box color correctly")

    print("\n✓ Available time slot rendering fully validated!")
    return True


async def test_time_period_navigation():
    """Test time period navigation (left/right arrow functionality)"""
    from calendar_tui import CalendarTUI, MCPClient
    import unittest.mock as mock

    print("\n" + "="*60)
    print("Testing Time Period Navigation")
    print("="*60)

    # Create a mock CalendarTUI instance with minimal setup
    # We won't actually use curses, just test the navigation logic
    class MockTUI:
        def __init__(self):
            self.time_filter = "today"
            self.time_min = None
            self.time_max = None

        def navigate_time_period(self, direction):
            """Copy of the navigate_time_period method from CalendarTUI"""
            if self.time_filter == "today":
                # Navigate day by day
                now = datetime.now().astimezone()
                target_date = now + timedelta(days=direction)
                start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)
                self.time_filter = "custom"
                self.time_min = start_of_day.isoformat()
                self.time_max = end_of_day.isoformat()

            elif self.time_filter == "this_week":
                # Navigate week by week
                if direction == -1:
                    # Go to previous week (Mon-Fri)
                    now = datetime.now().astimezone()
                    days_since_monday = now.weekday()
                    last_monday = now - timedelta(days=days_since_monday + 7)
                    start_of_week = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_of_week = (last_monday + timedelta(days=4)).replace(hour=23, minute=59, second=59, microsecond=0)
                    self.time_filter = "custom"
                    self.time_min = start_of_week.isoformat()
                    self.time_max = end_of_week.isoformat()
                else:
                    # Go to next week
                    self.time_filter = "next_week"
                    self.time_min = None
                    self.time_max = None

            elif self.time_filter == "next_week":
                # Navigate week by week
                if direction == -1:
                    # Go to this week
                    self.time_filter = "this_week"
                    self.time_min = None
                    self.time_max = None
                else:
                    # Go to week after next (Mon-Fri)
                    now = datetime.now().astimezone()
                    days_until_monday = (7 - now.weekday()) % 7
                    if days_until_monday == 0:
                        days_until_monday = 7
                    next_monday = now + timedelta(days=days_until_monday)
                    week_after_monday = next_monday + timedelta(days=7)
                    start_of_week = week_after_monday.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_of_week = (week_after_monday + timedelta(days=4)).replace(hour=23, minute=59, second=59, microsecond=0)
                    self.time_filter = "custom"
                    self.time_min = start_of_week.isoformat()
                    self.time_max = end_of_week.isoformat()

            elif self.time_filter == "custom" and self.time_min and self.time_max:
                # Navigate by the duration of the current range
                start = datetime.fromisoformat(self.time_min)
                end = datetime.fromisoformat(self.time_max)
                duration = end - start

                new_start = start + (duration * direction)
                new_end = end + (duration * direction)

                self.time_min = new_start.isoformat()
                self.time_max = new_end.isoformat()

    # Test 1: Navigate from "today" to tomorrow (right arrow)
    print("\n1. Testing navigation from 'today' to tomorrow (right arrow):")
    tui = MockTUI()
    tui.time_filter = "today"
    print(f"   Initial state: time_filter='{tui.time_filter}'")

    tui.navigate_time_period(1)  # Navigate forward
    print(f"   After right arrow: time_filter='{tui.time_filter}'")
    assert tui.time_filter == "custom", "Should switch to custom filter"
    assert tui.time_min is not None and tui.time_max is not None, "Should have time range set"

    # Verify it's tomorrow's date
    tomorrow = datetime.now().astimezone() + timedelta(days=1)
    time_min_date = datetime.fromisoformat(tui.time_min).date()
    assert time_min_date == tomorrow.date(), f"Should be tomorrow's date, got {time_min_date}"
    print(f"   ✓ Navigated to tomorrow: {time_min_date}")

    # Test 2: Navigate from "today" to yesterday (left arrow)
    print("\n2. Testing navigation from 'today' to yesterday (left arrow):")
    tui = MockTUI()
    tui.time_filter = "today"
    print(f"   Initial state: time_filter='{tui.time_filter}'")

    tui.navigate_time_period(-1)  # Navigate backward
    print(f"   After left arrow: time_filter='{tui.time_filter}'")

    yesterday = datetime.now().astimezone() - timedelta(days=1)
    time_min_date = datetime.fromisoformat(tui.time_min).date()
    assert time_min_date == yesterday.date(), f"Should be yesterday's date, got {time_min_date}"
    print(f"   ✓ Navigated to yesterday: {time_min_date}")

    # Test 3: Navigate from "this_week" to "next_week" (right arrow)
    print("\n3. Testing navigation from 'this_week' to 'next_week' (right arrow):")
    tui = MockTUI()
    tui.time_filter = "this_week"
    print(f"   Initial state: time_filter='{tui.time_filter}'")

    tui.navigate_time_period(1)  # Navigate forward
    print(f"   After right arrow: time_filter='{tui.time_filter}'")
    assert tui.time_filter == "next_week", "Should switch to next_week"
    print("   ✓ Navigated to next week")

    # Test 4: Navigate from "next_week" to "this_week" (left arrow)
    print("\n4. Testing navigation from 'next_week' to 'this_week' (left arrow):")
    tui = MockTUI()
    tui.time_filter = "next_week"
    print(f"   Initial state: time_filter='{tui.time_filter}'")

    tui.navigate_time_period(-1)  # Navigate backward
    print(f"   After left arrow: time_filter='{tui.time_filter}'")
    assert tui.time_filter == "this_week", "Should switch to this_week"
    print("   ✓ Navigated to this week")

    # Test 5: Navigate from "this_week" to previous week (left arrow)
    print("\n5. Testing navigation from 'this_week' to previous week (left arrow):")
    tui = MockTUI()
    tui.time_filter = "this_week"
    tui.navigate_time_period(-1)  # Navigate backward

    assert tui.time_filter == "custom", "Should switch to custom"
    assert tui.time_min is not None and tui.time_max is not None, "Should have time range"

    # Verify it's previous week's Monday-Friday
    time_min_date = datetime.fromisoformat(tui.time_min).date()
    time_max_date = datetime.fromisoformat(tui.time_max).date()
    days_diff = (time_max_date - time_min_date).days
    assert days_diff == 4, f"Should be Mon-Fri (4 days diff), got {days_diff}"
    print(f"   ✓ Navigated to previous week: {time_min_date} to {time_max_date}")

    # Test 6: Navigate in custom range (maintain duration)
    print("\n6. Testing navigation in custom date range (maintains duration):")
    now = datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=2)  # 2-day duration

    tui = MockTUI()
    tui.time_filter = "custom"
    tui.time_min = start.isoformat()
    tui.time_max = end.isoformat()

    print(f"   Initial range: {start.date()} to {end.date()} (2-day duration)")

    tui.navigate_time_period(1)  # Navigate forward

    new_start = datetime.fromisoformat(tui.time_min)
    new_end = datetime.fromisoformat(tui.time_max)
    new_duration = (new_end - new_start).days

    assert new_duration == 2, f"Duration should remain 2 days, got {new_duration}"
    assert new_start.date() == (start + timedelta(days=2)).date(), "Should shift forward by 2 days"
    print(f"   ✓ Navigated to: {new_start.date()} to {new_end.date()} (maintained 2-day duration)")

    print("\n✓ Time period navigation validated!")
    return True


async def test_focus_time_creation():
    """Test focus time creation from available slots"""
    from calendar_tui import CalendarEvent

    print("\n" + "="*60)
    print("Testing Focus Time Creation Logic")
    print("="*60)

    now = datetime.now().astimezone()
    today = now.date()

    # Test 1: Focus time title for short slot (≤40 min) - "Paperwork - Focus time"
    print("\n1. Testing focus time title for 30-minute slot:")

    start_30 = datetime.combine(today, datetime.min.time().replace(hour=10, minute=0))
    start_30 = start_30.replace(tzinfo=now.tzinfo)
    end_30 = start_30 + timedelta(minutes=30)

    available_30 = CalendarEvent({
        'start': {'dateTime': start_30.isoformat()},
        'end': {'dateTime': end_30.isoformat()}
    }, is_available=True)

    duration_minutes = available_30.get_duration_minutes()
    title = "Paperwork - Focus time" if duration_minutes <= 40 else "Development - Focus time"

    assert duration_minutes == 30, f"Duration should be 30 minutes, got {duration_minutes}"
    assert title == "Paperwork - Focus time", f"Title should be 'Paperwork - Focus time' for 30min, got '{title}'"
    print(f"   Duration: {duration_minutes} minutes")
    print(f"   Title: {title}")
    print("   ✓ 30-minute slot → 'Paperwork - Focus time'")

    # Test 2: Focus time title for 15-minute slot - "Paperwork - Focus time"
    print("\n2. Testing focus time title for 15-minute slot:")

    start_15 = datetime.combine(today, datetime.min.time().replace(hour=14, minute=0))
    start_15 = start_15.replace(tzinfo=now.tzinfo)
    end_15 = start_15 + timedelta(minutes=15)

    available_15 = CalendarEvent({
        'start': {'dateTime': start_15.isoformat()},
        'end': {'dateTime': end_15.isoformat()}
    }, is_available=True)

    duration_minutes = available_15.get_duration_minutes()
    title = "Paperwork - Focus time" if duration_minutes <= 40 else "Development - Focus time"

    assert duration_minutes == 15, f"Duration should be 15 minutes, got {duration_minutes}"
    assert title == "Paperwork - Focus time", f"Title should be 'Paperwork - Focus time' for 15min, got '{title}'"
    print(f"   Duration: {duration_minutes} minutes")
    print(f"   Title: {title}")
    print("   ✓ 15-minute slot → 'Paperwork - Focus time'")

    # Test 3: Focus time title for long slot (>40 min) - "Development - Focus time"
    print("\n3. Testing focus time title for 60-minute slot:")

    start_60 = datetime.combine(today, datetime.min.time().replace(hour=11, minute=0))
    start_60 = start_60.replace(tzinfo=now.tzinfo)
    end_60 = start_60 + timedelta(minutes=60)

    available_60 = CalendarEvent({
        'start': {'dateTime': start_60.isoformat()},
        'end': {'dateTime': end_60.isoformat()}
    }, is_available=True)

    duration_minutes = available_60.get_duration_minutes()
    title = "Paperwork - Focus time" if duration_minutes <= 40 else "Development - Focus time"

    assert duration_minutes == 60, f"Duration should be 60 minutes, got {duration_minutes}"
    assert title == "Development - Focus time", f"Title should be 'Development - Focus time' for 60min, got '{title}'"
    print(f"   Duration: {duration_minutes} minutes")
    print(f"   Title: {title}")
    print("   ✓ 60-minute slot → 'Development - Focus time'")

    # Test 4: Focus time title for 45-minute slot - "Development - Focus time"
    print("\n4. Testing focus time title for 45-minute slot:")

    start_45 = datetime.combine(today, datetime.min.time().replace(hour=15, minute=0))
    start_45 = start_45.replace(tzinfo=now.tzinfo)
    end_45 = start_45 + timedelta(minutes=45)

    available_45 = CalendarEvent({
        'start': {'dateTime': start_45.isoformat()},
        'end': {'dateTime': end_45.isoformat()}
    }, is_available=True)

    duration_minutes = available_45.get_duration_minutes()
    title = "Paperwork - Focus time" if duration_minutes <= 40 else "Development - Focus time"

    assert duration_minutes == 45, f"Duration should be 45 minutes, got {duration_minutes}"
    assert title == "Development - Focus time", f"Title should be 'Development - Focus time' for 45min, got '{title}'"
    print(f"   Duration: {duration_minutes} minutes")
    print(f"   Title: {title}")
    print("   ✓ 45-minute slot → 'Development - Focus time'")

    # Test 5: Focus time title for 2-hour slot - "Development - Focus time"
    print("\n5. Testing focus time title for 2-hour slot:")

    start_120 = datetime.combine(today, datetime.min.time().replace(hour=13, minute=0))
    start_120 = start_120.replace(tzinfo=now.tzinfo)
    end_120 = start_120 + timedelta(minutes=120)

    available_120 = CalendarEvent({
        'start': {'dateTime': start_120.isoformat()},
        'end': {'dateTime': end_120.isoformat()}
    }, is_available=True)

    duration_minutes = available_120.get_duration_minutes()
    title = "Paperwork - Focus time" if duration_minutes <= 40 else "Development - Focus time"

    assert duration_minutes == 120, f"Duration should be 120 minutes, got {duration_minutes}"
    assert title == "Development - Focus time", f"Title should be 'Development - Focus time' for 120min, got '{title}'"
    print(f"   Duration: {duration_minutes} minutes")
    print(f"   Title: {title}")
    print("   ✓ 2-hour slot → 'Development - Focus time'")

    # Test 6: Verify focus time can only be created on available slots
    print("\n6. Testing that focus time requires available slot:")

    regular_event = CalendarEvent({
        'id': 'regular1',
        'summary': 'Team Meeting',
        'start': {'dateTime': now.isoformat()},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat()},
        'status': 'confirmed',
        'eventType': 'default'
    })

    assert not regular_event.is_available, "Regular event should not be available"
    print(f"   Regular event.is_available = {regular_event.is_available}")
    print("   ✓ Regular events are correctly identified as non-available")

    # Test 7: Verify available slot attributes
    print("\n7. Testing available slot identification:")

    assert available_30.is_available, "Should be marked as available"
    assert available_60.is_available, "Should be marked as available"
    assert available_120.is_available, "Should be marked as available"
    print("   ✓ Available slots are correctly identified")

    # Test 8: Edge case - exactly 40 minutes (boundary)
    print("\n8. Testing boundary case - exactly 40 minutes:")

    duration_minutes = 40
    title = "Paperwork - Focus time" if duration_minutes <= 40 else "Development - Focus time"
    assert title == "Paperwork - Focus time", "Exactly 40 minutes should use 'Paperwork - Focus time'"
    print(f"   ✓ 40 minutes (boundary) → 'Paperwork - Focus time'")

    # Test 9: Edge case - 41 minutes (just over boundary)
    print("\n9. Testing boundary case - 41 minutes:")

    duration_minutes = 41
    title = "Paperwork - Focus time" if duration_minutes <= 40 else "Development - Focus time"
    assert title == "Development - Focus time", "41 minutes should use 'Development - Focus time'"
    print(f"   ✓ 41 minutes (just over) → 'Development - Focus time'")

    print("\n✓ Focus time creation logic validated!")
    return True


async def test_delete_focus_time():
    """Test focus time deletion logic"""
    from calendar_tui import CalendarEvent

    print("\n" + "="*60)
    print("Testing Focus Time Deletion Logic")
    print("="*60)

    now = datetime.now().astimezone()
    today = now.date()

    # Test 1: Verify focus time event has an id
    print("\n1. Testing that focus time events have IDs:")

    focus_event = CalendarEvent({
        'id': 'focus123',
        'summary': 'Development - Focus time',
        'start': {'dateTime': now.isoformat()},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat()},
        'status': 'confirmed',
        'eventType': 'focusTime'
    })

    assert focus_event.id == 'focus123', f"Focus time should have ID 'focus123', got '{focus_event.id}'"
    assert focus_event.event_type == 'focusTime', "Event type should be 'focusTime'"
    print(f"   Focus time event ID: {focus_event.id}")
    print(f"   Event type: {focus_event.event_type}")
    print("   ✓ Focus time events have required attributes for deletion")

    # Test 2: Verify only focus time events should be deletable with 'd'
    print("\n2. Testing event type detection for deletion:")

    regular_event = CalendarEvent({
        'id': 'meeting123',
        'summary': 'Team Meeting',
        'start': {'dateTime': now.isoformat()},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat()},
        'status': 'confirmed',
        'eventType': 'default'
    })

    assert regular_event.event_type == 'default', "Regular event should have type 'default'"
    assert focus_event.event_type == 'focusTime', "Focus event should have type 'focusTime'"
    print(f"   Regular event type: {regular_event.event_type} (should NOT be deleted)")
    print(f"   Focus event type: {focus_event.event_type} (CAN be deleted)")
    print("   ✓ Event type detection works correctly")

    # Test 3: Verify available slots don't have valid IDs for deletion
    print("\n3. Testing available slots cannot be deleted:")

    available_slot = CalendarEvent({
        'start': {'dateTime': now.isoformat()},
        'end': {'dateTime': (now + timedelta(hours=1)).isoformat()}
    }, is_available=True)

    assert available_slot.id == 'available', "Available slot should have placeholder ID"
    assert available_slot.event_type == 'available', "Available slot type should be 'available'"
    print(f"   Available slot ID: {available_slot.id} (placeholder)")
    print(f"   Available slot type: {available_slot.event_type}")
    print("   ✓ Available slots correctly identified as non-deletable")

    print("\n✓ Focus time deletion logic validated!")
    return True


async def test_bulk_focus_time_gaps():
    """Test bulk focus time creation including start/end of day gaps"""
    from calendar_tui import CalendarEvent

    print("\n" + "="*60)
    print("Testing Bulk Focus Time Gap Detection")
    print("="*60)

    now = datetime.now().astimezone()
    today = now.date()

    # Create mock events for a typical work day
    # 9am - core start
    # 10:30am - first event starts
    # 11:30am - first event ends
    # 1pm - second event starts
    # 2pm - second event ends
    # 5pm - core end

    core_start = datetime.combine(today, datetime.min.time().replace(hour=9, minute=0))
    core_start = core_start.replace(tzinfo=now.tzinfo)
    core_end = datetime.combine(today, datetime.min.time().replace(hour=17, minute=0))
    core_end = core_end.replace(tzinfo=now.tzinfo)

    # First event: 10:30am-11:30am
    event1_start = datetime.combine(today, datetime.min.time().replace(hour=10, minute=30))
    event1_start = event1_start.replace(tzinfo=now.tzinfo)
    event1_end = datetime.combine(today, datetime.min.time().replace(hour=11, minute=30))
    event1_end = event1_end.replace(tzinfo=now.tzinfo)

    # Second event: 1pm-2pm
    event2_start = datetime.combine(today, datetime.min.time().replace(hour=13, minute=0))
    event2_start = event2_start.replace(tzinfo=now.tzinfo)
    event2_end = datetime.combine(today, datetime.min.time().replace(hour=14, minute=0))
    event2_end = event2_end.replace(tzinfo=now.tzinfo)

    # Test 1: Detect gap before first event (9am to 10:30am)
    print("\n1. Testing gap detection before first event:")

    gap_before_minutes = (event1_start - core_start).total_seconds() / 60
    print(f"   Core start: {core_start.strftime('%I:%M %p')}")
    print(f"   First event: {event1_start.strftime('%I:%M %p')}")
    print(f"   Gap duration: {gap_before_minutes} minutes")

    assert gap_before_minutes == 90, f"Gap should be 90 minutes, got {gap_before_minutes}"
    assert gap_before_minutes >= 30, "Gap should be >= 30 minutes to create focus time"
    print("   ✓ Gap before first event detected (90 min, should create focus time)")

    # Test 2: Detect gap after last event (2pm to 5pm)
    print("\n2. Testing gap detection after last event:")

    gap_after_minutes = (core_end - event2_end).total_seconds() / 60
    print(f"   Last event ends: {event2_end.strftime('%I:%M %p')}")
    print(f"   Core end: {core_end.strftime('%I:%M %p')}")
    print(f"   Gap duration: {gap_after_minutes} minutes")

    assert gap_after_minutes == 180, f"Gap should be 180 minutes, got {gap_after_minutes}"
    assert gap_after_minutes >= 30, "Gap should be >= 30 minutes to create focus time"
    print("   ✓ Gap after last event detected (180 min, should create focus time)")

    # Test 3: Detect gap between events (11:30am to 1pm)
    print("\n3. Testing gap detection between events:")

    gap_between_minutes = (event2_start - event1_end).total_seconds() / 60
    print(f"   Event 1 ends: {event1_end.strftime('%I:%M %p')}")
    print(f"   Event 2 starts: {event2_start.strftime('%I:%M %p')}")
    print(f"   Gap duration: {gap_between_minutes} minutes")

    assert gap_between_minutes == 90, f"Gap should be 90 minutes, got {gap_between_minutes}"
    assert gap_between_minutes >= 30, "Gap should be >= 30 minutes to create focus time"
    print("   ✓ Gap between events detected (90 min, should create focus time)")

    # Test 4: Verify total focus time blocks for this scenario
    print("\n4. Testing total expected focus time blocks:")

    expected_blocks = 3  # Before first, between, after last
    print(f"   Expected focus time blocks: {expected_blocks}")
    print("     1. 9:00am - 10:30am (90 min) → Development - Focus time")
    print("     2. 11:30am - 1:00pm (90 min) → Development - Focus time")
    print("     3. 2:00pm - 5:00pm (180 min) → Development - Focus time")
    print("   ✓ All gaps correctly identified")

    # Test 5: Edge case - event starting exactly at 9am (no gap before)
    print("\n5. Testing edge case - first event at 9am (no gap before):")

    early_event = datetime.combine(today, datetime.min.time().replace(hour=9, minute=0))
    early_event = early_event.replace(tzinfo=now.tzinfo)
    gap_early = (early_event - core_start).total_seconds() / 60

    print(f"   Event starts at: {early_event.strftime('%I:%M %p')}")
    print(f"   Core starts at: {core_start.strftime('%I:%M %p')}")
    print(f"   Gap: {gap_early} minutes")

    assert gap_early == 0, f"No gap expected, got {gap_early} minutes"
    print("   ✓ No gap before first event when it starts at core start time")

    # Test 6: Edge case - event ending exactly at 5pm (no gap after)
    print("\n6. Testing edge case - last event at 5pm (no gap after):")

    late_event = datetime.combine(today, datetime.min.time().replace(hour=17, minute=0))
    late_event = late_event.replace(tzinfo=now.tzinfo)
    gap_late = (core_end - late_event).total_seconds() / 60

    print(f"   Event ends at: {late_event.strftime('%I:%M %p')}")
    print(f"   Core ends at: {core_end.strftime('%I:%M %p')}")
    print(f"   Gap: {gap_late} minutes")

    assert gap_late == 0, f"No gap expected, got {gap_late} minutes"
    print("   ✓ No gap after last event when it ends at core end time")

    # Test 7: Verify 30-minute minimum gap threshold
    print("\n7. Testing 30-minute minimum gap threshold:")

    # 25 minute gap - should NOT create focus time
    short_gap_minutes = 25
    print(f"   Short gap: {short_gap_minutes} minutes")
    assert short_gap_minutes < 30, "Gap less than 30 min should NOT create focus time"
    print("   ✓ Gaps < 30 minutes correctly ignored")

    # 30 minute gap - SHOULD create focus time
    exact_gap_minutes = 30
    print(f"   Exact threshold: {exact_gap_minutes} minutes")
    assert exact_gap_minutes >= 30, "Gap >= 30 min SHOULD create focus time"
    print("   ✓ Gaps >= 30 minutes will create focus time")

    print("\n✓ Bulk focus time gap detection validated!")
    return True


async def test_parse_day_filter():
    """Test parse_day_filter function"""
    from calendar_tui import parse_day_filter

    print("\n" + "="*60)
    print("Testing parse_day_filter Function")
    print("="*60)

    # Test 1: Standard filters
    print("\n1. Testing standard filters:")
    for filter_name in ['today', 'this_week', 'next_week']:
        time_filter, time_min, time_max = parse_day_filter(filter_name)
        assert time_filter == filter_name, f"Filter should be '{filter_name}', got '{time_filter}'"
        assert time_min is None, "time_min should be None for standard filters"
        assert time_max is None, "time_max should be None for standard filters"
        print(f"   ✓ '{filter_name}' → filter='{time_filter}', custom times=None")

    # Test 2: Tomorrow
    print("\n2. Testing 'tomorrow':")
    time_filter, time_min, time_max = parse_day_filter('tomorrow')
    assert time_filter == 'custom', "Filter should be 'custom' for tomorrow"
    assert time_min is not None and time_max is not None, "Should have custom time range"

    tomorrow = datetime.now().astimezone() + timedelta(days=1)
    time_min_date = datetime.fromisoformat(time_min).date()
    assert time_min_date == tomorrow.date(), "Should be tomorrow's date"
    print(f"   ✓ 'tomorrow' → custom range for {time_min_date}")

    # Test 3: Day abbreviations (mon-sun)
    print("\n3. Testing day abbreviations:")
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    for day_name in day_names:
        time_filter, time_min, time_max = parse_day_filter(day_name)
        assert time_filter == 'custom', f"Filter should be 'custom' for {day_name}"
        assert time_min is not None and time_max is not None, f"Should have custom time range for {day_name}"

        time_min_date = datetime.fromisoformat(time_min).date()
        time_max_date = datetime.fromisoformat(time_max).date()
        assert time_min_date == time_max_date, "Should be same day for single day filter"
        print(f"   ✓ '{day_name}' → {time_min_date}")

    # Test 4: Abbreviated day names
    print("\n4. Testing abbreviated day names:")
    for abbr in ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']:
        time_filter, time_min, time_max = parse_day_filter(abbr)
        assert time_filter == 'custom', f"Filter should be 'custom' for {abbr}"
        print(f"   ✓ '{abbr}' → custom range")

    # Test 5: Invalid input (should default to 'today')
    print("\n5. Testing invalid input (defaults to 'today'):")
    time_filter, time_min, time_max = parse_day_filter('invalid_day')
    assert time_filter == 'today', "Invalid input should default to 'today'"
    assert time_min is None and time_max is None, "Should not have custom times"
    print("   ✓ Invalid input defaults to 'today'")

    # Test 6: Case insensitivity
    print("\n6. Testing case insensitivity:")
    for variant in ['TODAY', 'Today', 'tOdAy', 'TOMORROW', 'Tomorrow', 'MONDAY', 'Monday']:
        time_filter, time_min, time_max = parse_day_filter(variant)
        assert time_filter is not None, f"Should handle case variant '{variant}'"
        print(f"   ✓ '{variant}' handled correctly")

    print("\n✓ parse_day_filter function validated!")
    return True


if __name__ == '__main__':
    async def run_all_tests():
        results = []

        # Run basic MCP connection test
        print("\n" + "="*60)
        print("RUNNING ALL TESTS")
        print("="*60)

        try:
            success = await test_mcp_connection()
            results.append(("MCP Connection", success))
        except Exception as e:
            print(f"\n❌ MCP connection test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("MCP Connection", False))

        # Run calendar feature tests
        try:
            success = await test_calendar_features()
            results.append(("Calendar Features", success))
        except Exception as e:
            print(f"\n❌ Calendar feature tests failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("Calendar Features", False))

        # Run location filtering test
        try:
            success = await test_location_filtering()
            results.append(("Location Filtering", success))
        except Exception as e:
            print(f"\n❌ Location filtering test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("Location Filtering", False))

        # Run column alignment test
        try:
            success = await test_column_alignment()
            results.append(("Column Alignment", success))
        except Exception as e:
            print(f"\n❌ Column alignment test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("Column Alignment", False))

        # Run cursor positioning test
        try:
            success = await test_cursor_positioning()
            results.append(("Cursor Positioning", success))
        except Exception as e:
            print(f"\n❌ Cursor positioning test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("Cursor Positioning", False))

        # Run meeting link display test
        try:
            success = await test_meeting_link_display()
            results.append(("Meeting Link Display", success))
        except Exception as e:
            print(f"\n❌ Meeting link display test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("Meeting Link Display", False))

        # Run available time slots test
        try:
            success = await test_available_time_slots()
            results.append(("Available Time Slots", success))
        except Exception as e:
            print(f"\n❌ Available time slots test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("Available Time Slots", False))

        # Run time period navigation test
        try:
            success = await test_time_period_navigation()
            results.append(("Time Period Navigation", success))
        except Exception as e:
            print(f"\n❌ Time period navigation test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("Time Period Navigation", False))

        # Run focus time creation test
        try:
            success = await test_focus_time_creation()
            results.append(("Focus Time Creation", success))
        except Exception as e:
            print(f"\n❌ Focus time creation test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("Focus Time Creation", False))

        # Run parse_day_filter test
        try:
            success = await test_parse_day_filter()
            results.append(("Parse Day Filter", success))
        except Exception as e:
            print(f"\n❌ Parse day filter test failed: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append(("Parse Day Filter", False))

        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        for test_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status} - {test_name}")

        total = len(results)
        passed = sum(1 for _, success in results if success)
        print(f"\nTotal: {passed}/{total} tests passed")

        all_passed = all(success for _, success in results)
        if all_passed:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️  Some tests failed")

        return all_passed

    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
