#!/usr/bin/env python3
"""
Interactive Terminal Calendar Application
Uses Google Calendar MCP Server to fetch and manage events

Requirements:
    pip install mcp curses-menu
"""

import curses
import json
import asyncio
import os
import subprocess
from datetime import datetime, timedelta, timezone, date
from typing import List, Dict, Optional
import argparse

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("Error: MCP SDK not installed. Install with: pip install mcp")
    import sys
    sys.exit(1)


class CalendarEvent:
    """Represents a calendar event with overlap detection"""

    def __init__(self, event_data: Dict, is_available: bool = False, core_start_hour: int = 9, core_end_hour: int = 17):
        self.is_available = is_available
        self.core_start_hour = core_start_hour
        self.core_end_hour = core_end_hour

        if is_available:
            # Available slot - create minimal event
            self.id = 'available'
            self.start = event_data.get('start', {})
            self.end = event_data.get('end', {})
            self.status = 'available'
            self.response_status = 'needsAction'
            self.has_overlap = False
            self.overlapping_event_ids = []
            self.attendees = []
            self.event_type = 'available'
            self.is_all_day = False
            self.hangout_link = None
            self.working_location_type = None

            # Parse times first to determine summary
            self.start_time = self._parse_time(self.start)
            self.end_time = self._parse_time(self.end)

            # Generate summary with boxes
            self.summary = self._generate_available_summary()
        else:
            # Regular event
            self.id = event_data.get('id', '')
            self.summary = event_data.get('summary', 'No Title')
            self.start = event_data.get('start', {})
            self.end = event_data.get('end', {})
            self.status = event_data.get('status', 'confirmed')
            self.response_status = self._get_response_status(event_data)
            self.has_overlap = event_data.get('has_overlap', False)
            self.overlapping_event_ids = event_data.get('overlapping_event_ids', [])
            self.attendees = event_data.get('attendees', [])
            self.event_type = event_data.get('eventType', 'default')

            # Google Tasks appear as focusTime events but have tasks.google.com in description
            # Detect and reclassify them as 'task' type
            if self.event_type == 'focusTime':
                description = event_data.get('description', '')
                if 'tasks.google.com/task/' in description:
                    self.event_type = 'task'

            # Extract hangout/meet link
            self.hangout_link = event_data.get('hangoutLink', '')

            # Extract working location properties
            self.working_location_type = None
            if self.event_type == 'workingLocation':
                working_loc = event_data.get('workingLocationProperties', {})
                self.working_location_type = working_loc.get('type', '')

            # Determine if this is an all-day event
            self.is_all_day = (
                (self.start.get('date') and not self.start.get('dateTime')) or
                (self.end.get('date') and not self.end.get('dateTime'))
            )

            # Parse times
            self.start_time = self._parse_time(self.start)
            self.end_time = self._parse_time(self.end)

    def _generate_available_summary(self) -> str:
        """Generate summary for available slots with visual boxes"""
        if not self.start_time or not self.end_time:
            return "Available"

        duration_minutes = (self.end_time - self.start_time).total_seconds() / 60
        num_blocks = int(duration_minutes / 30)

        # Check if this slot is during core hours
        # Create core hours boundaries for comparison
        core_start = self.start_time.replace(hour=self.core_start_hour, minute=0, second=0, microsecond=0)
        core_end = self.start_time.replace(hour=self.core_end_hour, minute=0, second=0, microsecond=0)

        # Determine if fully outside core hours
        # A slot is outside core if it ends before core starts OR starts after core ends
        is_outside_core = (self.end_time <= core_start or self.start_time >= core_end)

        if is_outside_core:
            # Grey boxes for out-of-hours (using black square emoji)
            boxes = "⬛" * min(num_blocks, 10)  # Cap at 10 boxes for display
        else:
            # Green boxes for core hours
            boxes = "🟩" * min(num_blocks, 10)

        return f"{boxes} Available"

    def _get_response_status(self, event_data: Dict) -> str:
        """Extract response status from event data"""
        # Check if user is an attendee and get their response
        attendees = event_data.get('attendees', [])

        for attendee in attendees:
            if attendee.get('self', False):
                status = attendee.get('responseStatus', 'needsAction')
                return status
        return event_data.get('responseStatus', 'needsAction')

    def _parse_time(self, time_obj: Dict) -> Optional[datetime]:
        """Parse datetime from event time object"""
        # Check for dateTime field with non-empty value
        if 'dateTime' in time_obj and time_obj['dateTime']:
            return datetime.fromisoformat(time_obj['dateTime'].replace('Z', '+00:00'))
        # Check for date field with non-empty value (all-day events)
        elif 'date' in time_obj and time_obj['date']:
            return datetime.fromisoformat(time_obj['date'])
        return None

    def get_time_str(self) -> str:
        """Get formatted time string"""
        if self.is_all_day:
            return "📅 All Day"
        if self.start_time and self.end_time:
            start = self.start_time.strftime('%I:%M%p').lstrip('0').lower()
            end = self.end_time.strftime('%I:%M%p').lstrip('0').lower()
            return f"{start}-{end}"
        return "📅 All Day"

    def get_duration_minutes(self) -> int:
        """Get event duration in minutes"""
        if self.is_all_day:
            # Return 0 for all-day events to avoid showing huge durations
            return 0
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return 0

    def get_response_char(self) -> str:
        """Get character representing RSVP status"""
        if self.is_available:
            # No emoji in RSVP column for available slots
            return ''

        # Task gets clipboard emoji
        if self.event_type == 'task':
            return '📋'

        # Focus time gets headphone emoji
        if self.event_type == 'focusTime':
            return '🎧'

        # Working location gets location-specific emoji
        if self.event_type == 'workingLocation':
            if self.working_location_type == 'homeOffice':
                return '🏠'
            elif self.working_location_type == 'officeLocation':
                return '🏢'
            elif self.working_location_type == 'customLocation':
                return '📍'
            else:
                return '📍'  # Default location marker

        status_map = {
            'accepted': '✅',
            'declined': '❌',
            'tentative': '⏳',
            'needsAction': '❓'
        }
        return status_map.get(self.response_status, '❓')

    def get_attendee_count(self) -> str:
        """Get formatted attendee count as accepted/total"""
        if self.is_available:
            return '—'

        total = len(self.attendees)
        if total == 0:
            return '—'

        # Count accepted responses
        accepted = 0
        for attendee in self.attendees:
            status = attendee.get('responseStatus', 'needsAction')
            if status == 'accepted':
                accepted += 1

        return f'(👍🏼{accepted}/{total})'

    def get_meet_link(self) -> str:
        """Get meet link or dash"""
        if self.is_available or not self.hangout_link:
            return '—'
        return self.hangout_link

    def get_meet_link_display(self) -> tuple:
        """Get meet link for display - returns (display_text, full_url)

        For Google Meet links, returns https://g.co/meet/xxx-yyyy-zzz format.
        Returns a tuple of (display_text, full_url) for creating clickable links.
        """
        if self.is_available or not self.hangout_link:
            return ('—', None)

        # Extract meeting ID from Google Meet URLs
        # Format: https://meet.google.com/xxx-yyyy-zzz -> https://g.co/meet/xxx-yyyy-zzz
        if 'meet.google.com/' in self.hangout_link:
            parts = self.hangout_link.split('meet.google.com/')
            if len(parts) > 1:
                meeting_id = parts[1].split('?')[0]  # Remove query params if any
                short_url = f"https://g.co/meet/{meeting_id}"
                return (short_url, self.hangout_link)

        # For other links, return full URL
        return (self.hangout_link, self.hangout_link)

    def is_currently_active(self) -> bool:
        """Check if this event is currently happening"""
        if self.is_available or self.is_all_day:
            return False

        if not self.start_time or not self.end_time:
            return False

        now = datetime.now().astimezone()
        return self.start_time <= now < self.end_time


class MCPClient:
    """Client for interacting with MCP server via stdio"""

    def __init__(self, server_path: str):
        self.server_path = server_path
        self.session: Optional[ClientSession] = None
        self.stdio_context = None
        self.session_context = None

    async def connect(self):
        """Connect to MCP server"""
        server_params = StdioServerParameters(
            command=self.server_path,
            args=[],
            env=None
        )

        # Enter the stdio context
        self.stdio_context = stdio_client(server_params)
        stdio, write = await self.stdio_context.__aenter__()

        # Enter the session context
        self.session_context = ClientSession(stdio, write)
        self.session = await self.session_context.__aenter__()

        # Initialize the session
        await self.session.initialize()

    async def disconnect(self):
        """Disconnect from MCP server"""
        # Exit contexts in reverse order
        if self.session_context:
            await self.session_context.__aexit__(None, None, None)
            self.session_context = None
            self.session = None

        if self.stdio_context:
            await self.stdio_context.__aexit__(None, None, None)
            self.stdio_context = None

    async def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Call an MCP tool and return the result"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")

        result = await self.session.call_tool(tool_name, arguments)
        return result.content[0].text if result.content else {}


class CalendarTUI:
    """Terminal UI for calendar management"""

    def __init__(self, stdscr, mcp_client: MCPClient, timezone: str = "America/New_York", debug: bool = False):
        self.stdscr = stdscr
        self.mcp_client = mcp_client
        self.timezone = timezone
        self.debug = debug
        self.events: List[CalendarEvent] = []
        self.current_row = 0
        self.scroll_offset = 0
        self.status_message = ""

        # Spinner for loading states
        self.spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_index = 0
        self.is_loading = False
        self.loading_message = ""

        # Time range parameters (tracks loaded data range)
        self.time_min = None
        self.time_max = None

        # Current view date (which day we're looking at)
        self.current_view_date = datetime.now().astimezone()

        # Display mode: 1 = current day only, 2 = current day + tomorrow
        self.display_mode = 1

        # Core hours (9am to 5pm)
        self.core_start_hour = 9
        self.core_end_hour = 17

        # Background fetch task
        self.background_fetch_task = None

        # Track which dates have loaded data (for mini calendar display)
        self.loaded_dates = set()  # Set of date objects

        # Attendee details overlay
        self.show_attendee_details = False
        self.attendee_details_event = None

        # Recommendations overlay
        self.show_recommendations = False
        self.recommendations_text = ""
        self.recommendations_loading = False
        self.recommendations_scroll_offset = 0
        self.recommendations_task = None  # Background task for fetching recommendations
        self._current_recommendations_task_id = None  # Track which task is current to prevent race conditions
        self.recommendations_view_date = None  # Track which date recommendations were generated for
        self.recommendations_display_mode = None  # Track which display mode recommendations were generated for

        # Loading state indicator with spinner
        self.is_fetching = False
        self.spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.spinner_index = 0

        # Toggle for showing/hiding declined events
        self.show_declined_locally = False

        # Setup colors
        curses.start_color()

        # Try to create custom dark red color for conflicts
        # Dark Red RGB: (139, 0, 0) -> curses uses 0-1000 scale
        if curses.can_change_color():
            try:
                # Define color 8 as dark red (RGB values scaled to 0-1000)
                curses.init_color(8, 545, 0, 0)  # Dark red
                conflict_color = 8
            except:
                # Fall back to regular red if custom colors don't work
                conflict_color = curses.COLOR_RED
        else:
            # Use red as fallback if terminal doesn't support custom colors
            conflict_color = curses.COLOR_RED

        # Try to create custom light grey color for available slots
        if curses.can_change_color():
            try:
                # Define color 15 as light grey (RGB values scaled to 0-1000)
                # Using color 15 to avoid conflicts with standard 0-7 colors
                curses.init_color(15, 600, 600, 600)  # Light grey RGB: (153, 153, 153)
                light_grey_color = 15
            except:
                # Fall back to white if custom colors don't work
                light_grey_color = curses.COLOR_WHITE
        else:
            # Use white as fallback if terminal doesn't support custom colors
            light_grey_color = curses.COLOR_WHITE

        # Try to create custom orange color for task events
        if curses.can_change_color():
            try:
                # Define color 16 as orange (RGB values scaled to 0-1000)
                curses.init_color(16, 1000, 647, 0)  # Orange RGB: (255, 165, 0)
                orange_color = 16
            except:
                # Fall back to yellow if custom colors don't work
                orange_color = curses.COLOR_YELLOW
        else:
            # Use yellow as fallback if terminal doesn't support custom colors
            orange_color = curses.COLOR_YELLOW

        # Regular colors (text on black background)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Default selection (black on white)
        curses.init_pair(2, conflict_color, curses.COLOR_BLACK)  # Declined/Overlap (dark red)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Accepted
        curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Tentative (magenta)
        curses.init_pair(5, light_grey_color, curses.COLOR_BLACK)  # Light grey (Available/needsAction)
        curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Focus time (yellow)
        curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)   # Links

        # Selection colors (colored text on white background)
        curses.init_pair(8, conflict_color, curses.COLOR_WHITE)  # Selected conflict/declined (red on white)
        curses.init_pair(9, curses.COLOR_MAGENTA, curses.COLOR_WHITE) # Selected tentative (magenta on white)
        curses.init_pair(10, curses.COLOR_YELLOW, curses.COLOR_WHITE) # Selected focus time (yellow on white)

        # Dark grey for out-of-hours available slots (dimmed white appears grey)
        curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Will be used with A_DIM

        # Task colors (orange)
        curses.init_pair(15, orange_color, curses.COLOR_BLACK)  # Task (orange on black)
        curses.init_pair(16, orange_color, curses.COLOR_WHITE)  # Selected task (orange on white)

        # Mini calendar colors
        curses.init_pair(12, curses.COLOR_BLACK, curses.COLOR_GREEN)  # Current day (green background)
        curses.init_pair(13, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Loaded day (white text)
        curses.init_pair(14, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Selected day cursor (black on white)

        # Hide cursor
        curses.curs_set(0)

    def debug_log(self, message: str):
        """Log debug message to stderr if debug mode is enabled"""
        if self.debug:
            import sys
            print(f"[DEBUG] {message}", file=sys.stderr, flush=True)

    def start_loading(self, message: str):
        """Start loading animation with message"""
        self.is_loading = True
        self.loading_message = message
        self.spinner_index = 0

    def stop_loading(self, final_message: str = ""):
        """Stop loading animation and optionally set final message"""
        self.is_loading = False
        if final_message:
            self.status_message = final_message

    def update_spinner(self):
        """Update spinner to next frame"""
        if self.is_loading:
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
            # Update status message with current spinner frame
            spinner = self.spinner_frames[self.spinner_index]
            self.status_message = f"{spinner} {self.loading_message}"

    async def run_with_spinner(self, coro, loading_msg: str, success_msg: str = None):
        """Run a coroutine while animating the spinner

        Args:
            coro: The coroutine to run
            loading_msg: Message to show while loading
            success_msg: Message to show on success (None = don't change status message)
        """
        self.start_loading(loading_msg)

        # Create background task
        task = asyncio.create_task(coro)

        # Animate spinner while task runs
        while not task.done():
            self.update_spinner()
            self.update_status_line()  # Only update status line, not entire screen
            await asyncio.sleep(0.05)

        # Get result and handle errors
        try:
            result = await task
            self.is_loading = False
            # Only override status message if success_msg is provided
            if success_msg is not None:
                self.status_message = success_msg
                self.update_status_line()  # Update to show final message
            return result
        except Exception as e:
            self.is_loading = False
            self.status_message = f"❌ Error: {str(e)}"
            self.update_status_line()  # Update to show error
            raise

    async def fetch_events(self, quick_mode: bool = False) -> bool:
        """Fetch events from MCP server

        Args:
            quick_mode: If True, only fetch today to end of week (fast initial load)
                       If False, fetch full 3 weeks (previous, current, next)
        """
        try:
            now = datetime.now().astimezone()

            if quick_mode:
                # Quick mode: today + tomorrow (if tomorrow is not weekend)
                start_of_range = now.replace(hour=0, minute=0, second=0, microsecond=0)

                # Check if tomorrow is a weekday
                tomorrow = now + timedelta(days=1)
                if tomorrow.weekday() < 5:  # Monday=0, Friday=4
                    # Tomorrow is a weekday, fetch it too
                    end_of_range = tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)
                else:
                    # Tomorrow is weekend, just fetch today
                    end_of_range = now.replace(hour=23, minute=59, second=59, microsecond=0)
            else:
                # Full mode: 3-week range (previous, current, next week)
                # Find Monday of current week
                days_since_monday = now.weekday()  # 0 = Monday, 6 = Sunday
                current_monday = now - timedelta(days=days_since_monday)

                # Previous week starts on Monday of last week
                previous_monday = current_monday - timedelta(days=7)
                start_of_range = previous_monday.replace(hour=0, minute=0, second=0, microsecond=0)

                # Next week ends on Sunday (6 days after next Monday + 1 day)
                next_monday = current_monday + timedelta(days=7)
                end_of_range = (next_monday + timedelta(days=6)).replace(hour=23, minute=59, second=59, microsecond=0)

            # Build request parameters
            params = {
                "time_filter": "custom",
                "time_min": start_of_range.isoformat(),
                "time_max": end_of_range.isoformat(),
                "timezone": self.timezone,
                "detect_overlaps": True,
                "show_declined": True,  # Always fetch declined events for toggle visibility
                "max_results": 250,
                "output_format": "json"
            }

            # Store the time range for reference
            self.time_min = start_of_range.isoformat()
            self.time_max = end_of_range.isoformat()

            # Call the MCP list_events tool with JSON output format
            result = await self.mcp_client.call_tool("list_events", params)

            # Parse the JSON result
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result

            events_list = data.get('events', [])
            self.events = [CalendarEvent(e, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour) for e in events_list]

            # Filter out all-day events that started before today
            today = datetime.now().date()
            filtered_events = []
            for event in self.events:
                # Skip all-day events that started before today
                if event.is_all_day and event.start_time:
                    event_date = event.start_time.date()
                    if event_date < today:
                        continue  # Skip this event
                filtered_events.append(event)
            self.events = filtered_events

            # Client-side filter: Remove conflicts involving declined events
            # Declined events should NEVER cause conflicts, regardless of toggle state
            declined_ids = {e.id for e in self.events if e.response_status == 'declined'}
            for event in self.events:
                if event.response_status == 'declined':
                    # Declined events themselves have no conflicts
                    event.has_overlap = False
                    event.overlapping_event_ids = []
                elif event.has_overlap and event.overlapping_event_ids:
                    # Remove declined event IDs from overlap list
                    event.overlapping_event_ids = [
                        eid for eid in event.overlapping_event_ids if eid not in declined_ids
                    ]
                    # If no overlaps remain, clear the flag
                    if not event.overlapping_event_ids:
                        event.has_overlap = False

            # Insert available time slots
            self._insert_available_slots()

            # Update loaded dates for mini calendar
            self._update_loaded_dates()

            return True

        except json.JSONDecodeError as e:
            self.status_message = f"JSON parse error: {str(e)}. Result: {result[:200] if isinstance(result, str) else result}"
            return False
        except Exception as e:
            import traceback
            self.status_message = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return False

    def _update_loaded_dates(self):
        """Update the set of loaded dates based on loaded time range"""
        # Mark all dates in the loaded range as loaded (not just dates with events)
        if self.time_min and self.time_max:
            start_date = datetime.fromisoformat(self.time_min).date()
            end_date = datetime.fromisoformat(self.time_max).date()

            # Add all dates in range
            current_date = start_date
            while current_date <= end_date:
                # Only add weekdays
                if current_date.weekday() < 5:  # Monday=0, Friday=4
                    self.loaded_dates.add(current_date)
                current_date += timedelta(days=1)

    def get_filtered_events(self) -> List[CalendarEvent]:
        """Get events filtered by current display mode, view date, and declined status"""
        view_date = self.current_view_date
        day_start = view_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Helper function to check if event should be included based on decline status
        def include_event(event):
            # Always show non-declined events
            if event.response_status != 'declined':
                return True
            # Show declined events only if toggle is on
            return self.show_declined_locally

        if self.display_mode == 1:
            # Show only the current view day's events
            day_end = view_date.replace(hour=23, minute=59, second=59, microsecond=0)
            filtered = []
            for event in self.events:
                # Skip declined events if toggle is off
                if not include_event(event):
                    continue

                if event.is_all_day:
                    # Include all-day events that fall on the view date
                    if event.start_time and event.start_time.date() == view_date.date():
                        filtered.append(event)
                elif event.start_time:
                    # Include events that start on the view date
                    if day_start <= event.start_time <= day_end:
                        filtered.append(event)
            return filtered

        elif self.display_mode == 2:
            # Show current view day and next day's events
            next_day_end = (view_date + timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=0)
            filtered = []
            for event in self.events:
                # Skip declined events if toggle is off
                if not include_event(event):
                    continue

                if event.is_all_day:
                    # Include all-day events that fall on view date or next day
                    if event.start_time:
                        event_date = event.start_time.date()
                        next_date = (view_date + timedelta(days=1)).date()
                        if event_date in [view_date.date(), next_date]:
                            filtered.append(event)
                elif event.start_time:
                    # Include events that start on view date or next day
                    if day_start <= event.start_time <= next_day_end:
                        filtered.append(event)
            return filtered

        # Default: return all events (display_mode == 3), filtered by decline status
        if self.show_declined_locally:
            return self.events
        else:
            # Filter out declined events
            return [e for e in self.events if include_event(e)]

    def _find_current_event(self):
        """Find and position cursor at the current or next event"""
        # Use filtered events for navigation
        filtered_events = self.get_filtered_events()
        if not filtered_events:
            self.current_row = 0
            return

        now = datetime.now().astimezone()

        # First, try to find the currently active event
        for i, event in enumerate(filtered_events):
            # Skip available slots and all-day events
            if event.is_available or event.is_all_day:
                continue

            if event.start_time and event.end_time:
                # Make sure times are timezone-aware for comparison
                start = event.start_time
                end = event.end_time

                # Check if this event is currently happening
                if start <= now < end:
                    self.current_row = i
                    self._adjust_scroll_for_current_row()
                    return

        # If no current event, find the next upcoming event
        for i, event in enumerate(filtered_events):
            # Skip available slots and all-day events
            if event.is_available or event.is_all_day:
                continue

            if event.start_time and event.start_time > now:
                self.current_row = i
                self._adjust_scroll_for_current_row()
                return

        # If no future events, stay at position 0
        self.current_row = 0

    def _adjust_scroll_for_current_row(self):
        """Adjust scroll offset to show the current row"""
        height, _ = self.stdscr.getmaxyx()
        max_rows = height - 10

        # If current row is below visible area, scroll down
        if self.current_row >= self.scroll_offset + max_rows:
            self.scroll_offset = self.current_row - max_rows + 1
        # If current row is above visible area, scroll up
        elif self.current_row < self.scroll_offset:
            self.scroll_offset = self.current_row

    def _insert_available_slots(self):
        """Insert available time slots for gaps of 30min or more during core hours"""
        # Filter out all-day events, available slots, and sort by start time
        # Also filter out declined events (they're ALWAYS treated as free time)
        def should_block_availability(e):
            if e.is_all_day or not e.start_time or e.is_available:
                return False
            # Declined events NEVER block available time, regardless of toggle
            if e.response_status == 'declined':
                return False
            return True

        timed_events = [e for e in self.events if should_block_availability(e)]
        if not timed_events:
            return

        # Sort by start time
        timed_events.sort(key=lambda e: e.start_time)

        # Find gaps and insert available slots
        new_events = []

        for i, event in enumerate(timed_events):
            # Get core hours for this event's day
            event_date = event.start_time.date()
            core_start = datetime.combine(event_date, datetime.min.time().replace(hour=self.core_start_hour))
            core_start = core_start.replace(tzinfo=event.start_time.tzinfo)
            core_end = datetime.combine(event_date, datetime.min.time().replace(hour=self.core_end_hour))
            core_end = core_end.replace(tzinfo=event.end_time.tzinfo)

            # Check for slot BEFORE first event of this day
            is_first_event_of_day = (i == 0) or (timed_events[i-1].start_time.date() != event_date)
            if is_first_event_of_day:
                gap_before_first = (event.start_time - core_start).total_seconds() / 60
                if gap_before_first >= 30 and event.start_time > core_start:
                    # Create slot from core start to first event
                    available_event = CalendarEvent({
                        'start': {'dateTime': core_start.isoformat()},
                        'end': {'dateTime': event.start_time.isoformat()}
                    }, is_available=True, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour)
                    new_events.append(available_event)

            # Add the event
            new_events.append(event)

            # Check for slot AFTER last event of this day
            is_last_event_of_day = (i == len(timed_events) - 1) or (timed_events[i+1].start_time.date() != event_date)
            if is_last_event_of_day:
                gap_after_last = (core_end - event.end_time).total_seconds() / 60
                if gap_after_last >= 30 and event.end_time < core_end:
                    # Create slot from last event to core end
                    available_event = CalendarEvent({
                        'start': {'dateTime': event.end_time.isoformat()},
                        'end': {'dateTime': core_end.isoformat()}
                    }, is_available=True, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour)
                    new_events.append(available_event)

            # Check if there's a next event
            if i < len(timed_events) - 1:
                next_event = timed_events[i + 1]

                # Skip if events are on different days (don't create overnight slots)
                if event.end_time.date() != next_event.start_time.date():
                    continue

                gap_minutes = (next_event.start_time - event.end_time).total_seconds() / 60

                # Only add available slot if gap is 30min or more
                if gap_minutes >= 30:
                    gap_start = event.end_time
                    gap_end = next_event.start_time

                    # Check if any other events overlap this potential gap
                    has_overlap = False
                    for other_event in timed_events:
                        if other_event == event or other_event == next_event:
                            continue
                        if other_event.start_time < gap_end and other_event.end_time > gap_start:
                            has_overlap = True
                            break

                    # Only create slots within the same day
                    if not has_overlap:
                        # Determine slot type based on timing
                        slot_start_hour = gap_start.hour
                        slot_end_hour = gap_end.hour

                        # Only create the slot if:
                        # 1. It's during core hours (green boxes), OR
                        # 2. It's after core hours AND there's an evening event (grey boxes)
                        # Don't create slots that extend past core hours with no evening event

                        if slot_start_hour < self.core_end_hour:
                            # Slot starts during core hours
                            if slot_end_hour <= self.core_end_hour:
                                # Fully within core hours - add it (green boxes)
                                available_event = CalendarEvent({
                                    'start': {'dateTime': gap_start.isoformat()},
                                    'end': {'dateTime': gap_end.isoformat()}
                                }, is_available=True, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour)
                                new_events.append(available_event)
                            else:
                                # Spans core hours end - only add up to core_end, then grey slot to evening event
                                # Green slot: gap_start to core_end
                                if gap_start < core_end:
                                    available_event = CalendarEvent({
                                        'start': {'dateTime': gap_start.isoformat()},
                                        'end': {'dateTime': core_end.isoformat()}
                                    }, is_available=True, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour)
                                    new_events.append(available_event)

                                # Grey slot: core_end to next_event (evening event)
                                if core_end < gap_end:
                                    available_event = CalendarEvent({
                                        'start': {'dateTime': core_end.isoformat()},
                                        'end': {'dateTime': gap_end.isoformat()}
                                    }, is_available=True, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour)
                                    new_events.append(available_event)
                        elif slot_start_hour >= self.core_end_hour and slot_end_hour <= 23:
                            # After core hours, only add if there's an evening event
                            # This is a grey slot between evening events
                            available_event = CalendarEvent({
                                'start': {'dateTime': gap_start.isoformat()},
                                'end': {'dateTime': gap_end.isoformat()}
                            }, is_available=True, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour)
                            new_events.append(available_event)

        # Add back all-day events, events without start times, and declined events
        all_day_events = [e for e in self.events if e.is_all_day]
        events_without_times = [e for e in self.events if not e.is_all_day and not e.start_time and not e.is_available]
        declined_events = [e for e in self.events if e.response_status == 'declined' and e.start_time and not e.is_all_day and not e.is_available]

        # Merge declined events with new_events and sort by start time
        timed_events_combined = new_events + declined_events
        timed_events_combined.sort(key=lambda e: e.start_time if e.start_time else datetime.min.replace(tzinfo=timezone.utc))

        self.events = all_day_events + events_without_times + timed_events_combined

    def draw_mini_calendar(self):
        """Draw compact 3-week calendar view on one line showing loaded dates"""
        height, width = self.stdscr.getmaxyx()

        # Add loading spinner to title if fetching data
        if self.is_fetching:
            spinner_char = self.spinner_frames[self.spinner_index]
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
            title = f"📅 Interactive Calendar {spinner_char}"
        else:
            title = "📅 Interactive Calendar"

        # Show date range based on display mode
        if self.display_mode == 2:
            # Two-day view: show both dates
            next_day = self.current_view_date + timedelta(days=1)
            date_str = f"{self.current_view_date.strftime('%A, %B %d')} - {next_day.strftime('%A, %B %d, %Y')}"
        else:
            # Single day view: show one date
            date_str = self.current_view_date.strftime("%A, %B %d, %Y")

        self.stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        self.stdscr.addstr(1, (width - len(date_str)) // 2, date_str)

        # Calculate week boundaries
        now = datetime.now().astimezone()
        today = now.date()

        days_since_monday = now.weekday()
        current_monday = now - timedelta(days=days_since_monday)

        previous_monday = current_monday - timedelta(days=7)
        next_monday = current_monday + timedelta(days=7)

        # Build 3 weeks: previous, current, next (Mon-Fri only)
        weeks = []
        for week_start in [previous_monday, current_monday, next_monday]:
            week_days = []
            for i in range(5):  # Mon-Fri
                day = week_start + timedelta(days=i)
                week_days.append(day.date())
            weeks.append(week_days)

        # Build single-line calendar string
        # Format: [Mo Tu We Th Fr] Mo Tu We Th Fr [Mo Tu We Th Fr]
        #         └─ Previous ──┘ └─ Current ─┘ └── Next ──┘

        start_y = 2

        # Calculate total width needed and starting position
        # Each day: 2 chars + 1 space = 3 chars per day, 5 days = 15 chars
        # Previous week: [15] + 1 space = 16
        # Current week: 15 + 1 space = 16
        # Next week: [15] = 17
        # Separators: 2 x " | " = 6
        # Total: ~55 chars

        # Start position for centered display
        total_width = 15 + 3 + 15 + 3 + 15  # days + separators
        start_x = max(0, (width - total_width) // 2)
        current_x = start_x

        view_date = self.current_view_date.date()

        # Draw previous week with brackets
        self.stdscr.addstr(start_y, current_x, "[", curses.color_pair(5))
        current_x += 1

        for day_date in weeks[0]:
            self._draw_day_cell(start_y, current_x, day_date, today, view_date)
            current_x += 3

        self.stdscr.addstr(start_y, current_x - 1, "]", curses.color_pair(5))
        current_x += 1

        # Separator
        self.stdscr.addstr(start_y, current_x, " | ", curses.color_pair(5))
        current_x += 3

        # Draw current week (no brackets)
        for day_date in weeks[1]:
            self._draw_day_cell(start_y, current_x, day_date, today, view_date)
            current_x += 3

        # Separator
        self.stdscr.addstr(start_y, current_x - 1, " | ", curses.color_pair(5))
        current_x += 2

        # Draw next week with brackets
        self.stdscr.addstr(start_y, current_x, "[", curses.color_pair(5))
        current_x += 1

        for day_date in weeks[2]:
            self._draw_day_cell(start_y, current_x, day_date, today, view_date)
            current_x += 3

        self.stdscr.addstr(start_y, current_x - 1, "]", curses.color_pair(5))

        # Draw separator
        self.stdscr.addstr(3, 0, "─" * width)

    def _draw_day_cell(self, y: int, x: int, day_date: date, today: date, view_date: date):
        """Draw a single day cell in the mini calendar"""
        is_today = (day_date == today)
        is_loaded = day_date in self.loaded_dates

        # Check if this day is in the selected view period
        is_selected = False
        if self.display_mode == 1:
            # Single day view: only highlight current view date
            is_selected = (day_date == view_date)
        elif self.display_mode == 2:
            # Two-day view: highlight both current day AND next day
            next_date = (self.current_view_date + timedelta(days=1)).date()
            is_selected = (day_date == view_date or day_date == next_date)

        day_abbr = day_date.strftime("%a")[:2]

        # Determine color/style priority: selected > today > loaded > not loaded
        # Selection cursor overlays the green today marker
        if is_selected:
            # Selected day: light grey cursor (white background) - overlays everything
            attr = curses.color_pair(14)
        elif is_today:
            # Current day: GREEN background (when not selected)
            attr = curses.color_pair(12) | curses.A_BOLD
        elif is_loaded:
            # Loaded day: white text
            attr = curses.color_pair(13)
        else:
            # Not loaded: dim
            attr = curses.color_pair(5) | curses.A_DIM

        self.stdscr.addstr(y, x, day_abbr, attr)

    def draw_header(self):
        """Draw the application header (now using mini calendar)"""
        self.draw_mini_calendar()

    def draw_table_header(self, start_y: int):
        """Draw the table header"""
        # Format: Day | Time | Event | 📬 | Attendees | Meet Link
        header = f"{'Day':<4} │ {'Time':<11} │ {'Event':<35} │ {'📬':<4} │ {'Attendees':<14} │ {'Meet Link':<30}"
        self.stdscr.addstr(start_y, 1, header, curses.A_BOLD | curses.A_UNDERLINE)

    def draw_event_row(self, y: int, event: CalendarEvent, is_selected: bool, row_num: int, available_count: int):
        """Draw a single event row"""
        height, width = self.stdscr.getmaxyx()

        # Get day of week
        day = ""
        if event.start_time:
            day = event.start_time.strftime('%a')

        # Format time
        time_str = ""
        if event.is_all_day:
            # Emoji takes 2 cells, so we pad to 10 instead of 11 to account for it
            time_str = "📅 All Day".ljust(10)
        elif event.start_time and event.end_time:
            start = event.start_time.strftime('%H:%M')
            end = event.end_time.strftime('%H:%M')
            time_str = f"{start}-{end}".ljust(11)

        # Get event title with clock emoji prefix for currently active events
        # Emoji is 2 chars wide, so adjust title length accordingly
        if event.is_currently_active():
            # Clock emoji (2) + space (1) + title text (32) = 35 total display width
            title = f"🕐 {event.summary[:32]}"
        else:
            title = event.summary[:35]

        # Get response, attendees, link
        rsvp = event.get_response_char()

        # Add conflict emoji if there's an overlap
        # Handle padding carefully: single emoji = 2 cells, double emoji = 4 cells
        if event.has_overlap:
            rsvp = rsvp + '⚠️ '
            # Two emojis = 4 display cells, add 1 space for separation
        else:
            # Single emoji = 2 display cells, add 2 spaces
            if rsvp:
                rsvp = rsvp + '  '

        attendees = event.get_attendee_count()[:14]

        # Get link display text and full URL for clickable links
        link_display, link_url = event.get_meet_link_display()

        # Determine color based on event state
        attr = curses.A_NORMAL

        if is_selected:
            # Selection bar uses white background with colored text
            if event.event_type == 'task':
                # Orange text on white background
                attr = curses.color_pair(16) | curses.A_BOLD
            elif event.event_type == 'focusTime':
                # Yellow text on white background
                attr = curses.color_pair(10) | curses.A_BOLD
            elif event.has_overlap or event.response_status == 'declined':
                # Red text on white background
                attr = curses.color_pair(8) | curses.A_BOLD
            elif event.response_status == 'tentative':
                # Magenta text on white background
                attr = curses.color_pair(9) | curses.A_BOLD
            else:
                # Black text on white background (accepted/needsAction/available)
                attr = curses.color_pair(1) | curses.A_BOLD
        else:
            # Not selected - regular colors
            if event.is_available:
                # Check if available slot is outside core hours
                if event.start_time and event.end_time:
                    # Create core hours boundaries for comparison (same logic as _generate_available_summary)
                    core_start = event.start_time.replace(hour=self.core_start_hour, minute=0, second=0, microsecond=0)
                    core_end = event.start_time.replace(hour=self.core_end_hour, minute=0, second=0, microsecond=0)

                    # A slot is outside core if it ends before core starts OR starts after core ends
                    is_outside_core = (event.end_time <= core_start or event.start_time >= core_end)

                    if is_outside_core:
                        # Out of hours: dark grey (dimmed)
                        attr = curses.color_pair(11) | curses.A_DIM
                    else:
                        # Core hours: light grey
                        attr = curses.color_pair(5)
                else:
                    # Fallback: light grey
                    attr = curses.color_pair(5)
            elif event.has_overlap:
                # Overlapping events: red
                attr = curses.color_pair(2)
            elif event.response_status == 'tentative':
                # Tentative: magenta
                attr = curses.color_pair(4)
            elif event.response_status == 'declined':
                # Declined: red
                attr = curses.color_pair(2)
            elif event.response_status == 'accepted':
                # Accepted: default color
                attr = curses.A_NORMAL
            elif event.response_status == 'needsAction':
                # Unknown/no response: default color
                attr = curses.A_NORMAL
            else:
                # Default: normal
                attr = curses.A_NORMAL

            if event.event_type == 'task':
                # Task: orange
                attr = curses.color_pair(15)
            elif event.event_type == 'focusTime':
                # Focus time: yellow
                attr = curses.color_pair(6)

        # Build row text without link (we'll draw link separately in blue)
        # Note: time_str and rsvp are already padded to correct display width
        # For title with emoji: pad to 34 chars (emoji takes 2 display cells, so 34 chars = 35 display width)
        # For title without emoji: pad to 35 chars normally
        if event.is_currently_active():
            # Title has emoji (2 cells) + space + text, so pad to 34 to get 35 display width
            title_padded = f"{title:<34}"
        else:
            # Normal title, pad to 35
            title_padded = f"{title:<35}"

        row_text_no_link = f"{day:<4} │ {time_str} │ {title_padded} │ {rsvp} │ {attendees:<14} │"

        try:
            if is_selected:
                # Draw full width highlight
                self.stdscr.addstr(y, 0, " " * width, attr)

            # Draw main row text
            self.stdscr.addstr(y, 1, row_text_no_link[:width-2], attr)

            # Draw link - blue if not selected, highlighted color if selected
            # Calculate link position: 1(margin) + 4(Day) + 3(│) + 11(Time) + 3(│) + 35(Event) + 3(│) + 4(Status) + 3(│) + 14(Attendees) + 3(│) = 84
            link_x = 84

            # Display the meeting ID (e.g., "kmv-cnxe-buy") instead of full URL
            # This is much shorter (12-15 chars) and won't be truncated
            if link_display and link_display != '—':
                if not is_selected:
                    # Draw link in blue
                    self.stdscr.addstr(y, link_x, link_display, curses.color_pair(7))
                else:
                    # Draw link in selection color
                    self.stdscr.addstr(y, link_x, link_display, attr)
            elif link_display:
                # Draw dash
                self.stdscr.addstr(y, link_x, link_display, attr)

        except curses.error as e:
            # Handle edge case where text doesn't fit - try to write as much as possible
            # Curses error usually means we exceeded terminal width
            pass

    def draw_events(self, start_y: int):
        """Draw all events filtered by display mode"""
        height, width = self.stdscr.getmaxyx()
        max_rows = height - start_y - 4

        # Get filtered events based on display mode
        filtered_events = self.get_filtered_events()

        # Track row numbers and available slot counts
        row_num = 1
        available_count = 1
        current_y = start_y

        # Draw events
        for i, event in enumerate(filtered_events[self.scroll_offset:self.scroll_offset + max_rows]):
            actual_index = i + self.scroll_offset
            is_selected = actual_index == self.current_row

            # Calculate proper row number
            if event.is_available:
                current_available = available_count
                available_count += 1
            else:
                current_row = row_num
                row_num += 1

            self.draw_event_row(
                current_y,
                event,
                is_selected,
                current_row if not event.is_available else 0,
                current_available if event.is_available else 0
            )
            current_y += 1

    def draw_attendee_details(self):
        """Draw attendee details overlay for selected event"""
        if not self.attendee_details_event:
            return

        height, width = self.stdscr.getmaxyx()
        event = self.attendee_details_event

        # Calculate modal dimensions
        modal_width = min(80, width - 4)
        modal_height = min(30, height - 4)
        start_x = (width - modal_width) // 2
        start_y = (height - modal_height) // 2

        # Count attendees by status
        accepted = []
        declined = []
        tentative = []
        no_response = []

        for attendee in event.attendees:
            status = attendee.get('responseStatus', 'needsAction')
            name = attendee.get('displayName') or attendee.get('email', 'Unknown')
            email = attendee.get('email', '')
            is_self = attendee.get('self', False)

            attendee_info = {
                'name': name,
                'email': email,
                'is_self': is_self
            }

            if status == 'accepted':
                accepted.append(attendee_info)
            elif status == 'declined':
                declined.append(attendee_info)
            elif status == 'tentative':
                tentative.append(attendee_info)
            else:
                no_response.append(attendee_info)

        total = len(event.attendees)

        # Draw modal background
        try:
            # Draw box border
            for y in range(start_y, start_y + modal_height):
                self.stdscr.addstr(y, start_x, " " * modal_width, curses.color_pair(1))

            # Top border
            self.stdscr.addstr(start_y, start_x, "╔" + "═" * (modal_width - 2) + "╗", curses.color_pair(1) | curses.A_BOLD)

            # Title
            title = f" Attendees for {event.summary[:40]} "
            title_x = start_x + (modal_width - len(title)) // 2
            self.stdscr.addstr(start_y, title_x, title, curses.color_pair(1) | curses.A_BOLD)

            current_y = start_y + 1

            # Visual status bar chart
            if total > 0:
                self.stdscr.addstr(current_y, start_x, "║" + " " * (modal_width - 2) + "║", curses.color_pair(1))
                current_y += 1

                # Calculate percentages
                accepted_pct = (len(accepted) / total) * 100
                declined_pct = (len(declined) / total) * 100
                tentative_pct = (len(tentative) / total) * 100
                no_response_pct = (len(no_response) / total) * 100

                # Draw status summary
                summary = f"  Total: {total} | ✅ {len(accepted)} | ❌ {len(declined)} | ⏳ {len(tentative)} | ❓ {len(no_response)}"
                self.stdscr.addstr(current_y, start_x, "║", curses.color_pair(1))
                self.stdscr.addstr(current_y, start_x + 1, summary.ljust(modal_width - 2), curses.color_pair(1) | curses.A_BOLD)
                self.stdscr.addstr(current_y, start_x + modal_width - 1, "║", curses.color_pair(1))
                current_y += 1

                # Visual bar chart
                bar_width = modal_width - 6
                accepted_bars = int((len(accepted) / total) * bar_width)
                declined_bars = int((len(declined) / total) * bar_width)
                tentative_bars = int((len(tentative) / total) * bar_width)
                no_response_bars = bar_width - accepted_bars - declined_bars - tentative_bars

                self.stdscr.addstr(current_y, start_x, "║", curses.color_pair(1))
                bar_x = start_x + 3

                # Green bars for accepted
                if accepted_bars > 0:
                    self.stdscr.addstr(current_y, bar_x, "█" * accepted_bars, curses.color_pair(3))
                    bar_x += accepted_bars

                # Red bars for declined
                if declined_bars > 0:
                    self.stdscr.addstr(current_y, bar_x, "█" * declined_bars, curses.color_pair(2))
                    bar_x += declined_bars

                # Yellow bars for tentative
                if tentative_bars > 0:
                    self.stdscr.addstr(current_y, bar_x, "█" * tentative_bars, curses.color_pair(4))
                    bar_x += tentative_bars

                # Grey bars for no response
                if no_response_bars > 0:
                    self.stdscr.addstr(current_y, bar_x, "█" * no_response_bars, curses.color_pair(5))

                self.stdscr.addstr(current_y, start_x + modal_width - 1, "║", curses.color_pair(1))
                current_y += 1

                # Separator
                self.stdscr.addstr(current_y, start_x, "║" + "─" * (modal_width - 2) + "║", curses.color_pair(1))
                current_y += 1

            # List attendees grouped by status
            max_list_height = modal_height - (current_y - start_y) - 3
            attendee_y = 0

            def draw_attendee_group(title, attendees_list, emoji, color_pair):
                nonlocal current_y, attendee_y
                if not attendees_list or attendee_y >= max_list_height:
                    return

                # Group header
                if attendee_y < max_list_height:
                    self.stdscr.addstr(current_y, start_x, "║", curses.color_pair(1))
                    header = f"  {emoji} {title} ({len(attendees_list)})"
                    self.stdscr.addstr(current_y, start_x + 1, header.ljust(modal_width - 2), color_pair | curses.A_BOLD)
                    self.stdscr.addstr(current_y, start_x + modal_width - 1, "║", curses.color_pair(1))
                    current_y += 1
                    attendee_y += 1

                # List attendees
                for att in attendees_list:
                    if attendee_y >= max_list_height:
                        break

                    self.stdscr.addstr(current_y, start_x, "║", curses.color_pair(1))

                    # Format: Name (email) with "You" indicator
                    name = att['name'][:30]
                    email = att['email'][:40] if att['email'] != att['name'] else ""

                    if att['is_self']:
                        line = f"    • {name} (You)"
                    elif email:
                        line = f"    • {name}"
                    else:
                        line = f"    • {name}"

                    self.stdscr.addstr(current_y, start_x + 1, line.ljust(modal_width - 2)[:modal_width - 2], color_pair)
                    self.stdscr.addstr(current_y, start_x + modal_width - 1, "║", curses.color_pair(1))
                    current_y += 1
                    attendee_y += 1

            # Draw each group
            draw_attendee_group("Accepted", accepted, "✅", curses.color_pair(3))
            draw_attendee_group("Tentative", tentative, "⏳", curses.color_pair(4))
            draw_attendee_group("No Response", no_response, "❓", curses.color_pair(5))
            draw_attendee_group("Declined", declined, "❌", curses.color_pair(2))

            # Fill remaining space
            while current_y < start_y + modal_height - 2:
                self.stdscr.addstr(current_y, start_x, "║" + " " * (modal_width - 2) + "║", curses.color_pair(1))
                current_y += 1

            # Footer
            footer_text = "Press ESC or Enter to close"
            footer_x = start_x + (modal_width - len(footer_text)) // 2
            self.stdscr.addstr(current_y, start_x, "║" + " " * (modal_width - 2) + "║", curses.color_pair(1))
            self.stdscr.addstr(current_y, footer_x, footer_text, curses.color_pair(1) | curses.A_DIM)
            current_y += 1

            # Bottom border
            self.stdscr.addstr(current_y, start_x, "╚" + "═" * (modal_width - 2) + "╝", curses.color_pair(1) | curses.A_BOLD)

        except curses.error:
            pass

        self.stdscr.refresh()

    def _clear_recommendations(self):
        """Clear cached recommendations when calendar data changes"""
        if self.show_recommendations:
            self.show_recommendations = False
        self.recommendations_text = ""
        self.recommendations_scroll_offset = 0
        self.recommendations_view_date = None
        self.recommendations_display_mode = None

    def _are_recommendations_valid_for_current_view(self) -> bool:
        """Check if cached recommendations are for the current view"""
        if not self.recommendations_text:
            return False
        if self.recommendations_view_date is None or self.recommendations_display_mode is None:
            return False
        # Check if view date and mode match
        return (self.recommendations_view_date == self.current_view_date.date() and
                self.recommendations_display_mode == self.display_mode)

    def _collect_events_for_recommendations(self) -> dict:
        """Collect events from current view for recommendations"""
        filtered_events = self.get_filtered_events()

        # Convert events to JSON-serializable format
        events_data = []
        for event in filtered_events:
            # Skip available slots and workingLocation events
            if event.is_available:
                continue
            if event.event_type == 'workingLocation':
                continue

            event_dict = {
                'id': event.id,
                'summary': event.summary,
                'start': event.start,
                'end': event.end,
                'has_overlap': event.has_overlap,
                'overlapping_event_ids': event.overlapping_event_ids,
                'attendees': event.attendees,
                'eventType': event.event_type,
                'responseStatus': event.response_status
            }
            events_data.append(event_dict)

        return {
            'events': events_data,
            'count': len(events_data)
        }

    async def _fetch_recommendations_background(self):
        """Background task to fetch recommendations without blocking the UI"""
        # Capture the task ID at start to check if we're still current when we finish
        my_task_id = id(asyncio.current_task())

        try:
            # Collect event data
            events_data = self._collect_events_for_recommendations()

            # Convert to JSON
            events_json = json.dumps(events_data, indent=2)

            # Write events to file
            event_prompt_file = "event-prompt.json"
            with open(event_prompt_file, 'w') as f:
                f.write(events_json)

            self.debug_log(f"Calendar data written to {event_prompt_file}")

            # Call Claude Code /recommend command (async, non-blocking)
            self.debug_log(f"Calling claude /recommend with {events_data['count']} events")

            # Use asyncio subprocess for non-blocking execution
            process = await asyncio.create_subprocess_exec(
                'claude', '/recommend', '@./'+event_prompt_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Wait for process to complete (with timeout) - yielding to event loop periodically
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=60.0
                )

                if process.returncode == 0:
                    recommendations = stdout.decode('utf-8').strip()

                    # Debug: Dump the complete output received from Claude Code
                    if self.debug:
                        self.debug_log("=" * 80)
                        self.debug_log("RAW OUTPUT RECEIVED FROM CLAUDE CODE (STDOUT):")
                        self.debug_log("=" * 80)
                        self.debug_log(recommendations if recommendations else "(empty response)")
                        self.debug_log("=" * 80)

                        # Also log stderr in case there's thinking or other info there
                        stderr_text = stderr.decode('utf-8').strip() if stderr else ""
                        if stderr_text:
                            self.debug_log("=" * 80)
                            self.debug_log("STDERR OUTPUT FROM CLAUDE CODE:")
                            self.debug_log("=" * 80)
                            self.debug_log(stderr_text)
                            self.debug_log("=" * 80)

                        self.debug_log("Note: Claude thinking output may be included above if enabled in Claude Code settings.")

                    # Only update if we're still the current task
                    if hasattr(self, '_current_recommendations_task_id') and my_task_id == self._current_recommendations_task_id:
                        if recommendations:
                            self.recommendations_text = recommendations
                        else:
                            self.recommendations_text = "No recommendations generated."
                else:
                    # Only update if we're still the current task
                    if hasattr(self, '_current_recommendations_task_id') and my_task_id == self._current_recommendations_task_id:
                        error_msg = stderr.decode('utf-8').strip() if stderr else "Unknown error"
                        self.recommendations_text = f"❌ Error getting recommendations:\n{error_msg}"
                        self.debug_log(f"Claude /recommend failed: {error_msg}")

            except asyncio.TimeoutError:
                # Only update if we're still the current task
                if hasattr(self, '_current_recommendations_task_id') and my_task_id == self._current_recommendations_task_id:
                    self.recommendations_text = "❌ Request timed out. Please try again."
                    self.debug_log("Claude /recommend timed out")
                # Kill the process if it's still running
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass

        except FileNotFoundError:
            # Only update if we're still the current task
            if hasattr(self, '_current_recommendations_task_id') and my_task_id == self._current_recommendations_task_id:
                self.recommendations_text = "❌ Claude Code CLI not found. Make sure 'claude' is in your PATH."
                self.debug_log("claude command not found")
        except asyncio.CancelledError:
            # Task was cancelled, don't update any state (a new task is running)
            self.debug_log(f"Recommendations task {my_task_id} was cancelled")
            raise  # Re-raise to properly handle cancellation
        except Exception as e:
            # Only update state if we're still the current task
            if hasattr(self, '_current_recommendations_task_id') and my_task_id == self._current_recommendations_task_id:
                self.recommendations_text = f"❌ Error: {str(e)}"
                self.debug_log(f"Error getting recommendations: {e}")
        finally:
            # Only update state if we're still the current task
            if hasattr(self, '_current_recommendations_task_id') and my_task_id == self._current_recommendations_task_id:
                self.recommendations_loading = False
                self.recommendations_task = None
                # Save which view these recommendations were generated for
                self.recommendations_view_date = self.current_view_date.date()
                self.recommendations_display_mode = self.display_mode

                # Clean up event-prompt.json if not in debug mode
                if not self.debug:
                    try:
                        if os.path.exists("event-prompt.json"):
                            os.remove("event-prompt.json")
                    except Exception as e:
                        self.debug_log(f"Failed to remove event-prompt.json: {e}")

                # Always redraw to update light bulb indicator in footer
                # If modal is visible, full redraw; otherwise just update footer
                if self.show_recommendations:
                    self.draw()
                else:
                    # Update footer to show light bulb indicator
                    self.draw_footer()
                    self.stdscr.refresh()

    def start_recommendations_fetch(self, show_popup: bool = True):
        """Start fetching recommendations in background

        Args:
            show_popup: If True, shows the modal immediately. If False, fetches silently in background.
        """
        # Cancel any existing task
        if self.recommendations_task and not self.recommendations_task.done():
            self.recommendations_task.cancel()

        # Show loading state
        self.recommendations_loading = True
        if show_popup:
            self.show_recommendations = True
            self.spinner_index = 0  # Reset spinner animation
            self.draw()

        self.recommendations_text = ""  # Empty text while loading
        self.recommendations_scroll_offset = 0  # Reset scroll position

        # Start background task and store reference to check if it's still current when it completes
        self.recommendations_task = asyncio.create_task(self._fetch_recommendations_background())
        # Store the task ID so the background task can check if it's still current
        self._current_recommendations_task_id = id(self.recommendations_task)

    def _wrap_text_lines(self, text: str, max_width: int) -> list:
        """Wrap text lines to fit within max_width, preserving formatting"""
        wrapped_lines = []

        for line in text.split('\n'):
            if len(line) <= max_width:
                # Line fits, add as-is
                wrapped_lines.append(line)
            else:
                # Line is too long, need to wrap
                # Preserve leading whitespace for indentation (calculate once)
                leading_spaces = len(line) - len(line.lstrip())
                indent = line[:leading_spaces]
                continuation_indent = indent + "  "  # Add extra indent for wrapped lines

                # Wrap the line at word boundaries
                remaining = line

                while remaining:
                    if len(remaining) <= max_width:
                        wrapped_lines.append(remaining)
                        break

                    # Find the last space within max_width
                    wrap_point = max_width
                    for i in range(max_width, 0, -1):
                        if remaining[i-1] in (' ', '-', ','):
                            wrap_point = i
                            break

                    # If no good break point found, just hard break
                    if wrap_point == max_width and len(remaining) > max_width:
                        wrap_point = max_width

                    # Add the wrapped portion
                    wrapped_lines.append(remaining[:wrap_point])

                    # Continue with remainder, adding continuation indent
                    remaining = remaining[wrap_point:].lstrip()
                    if remaining:
                        remaining = continuation_indent + remaining

        return wrapped_lines

    def draw_recommendations(self):
        """Draw recommendations overlay"""
        if not self.show_recommendations:
            return

        height, width = self.stdscr.getmaxyx()

        # Calculate modal dimensions
        modal_width = min(100, width - 4)
        modal_height = min(40, height - 4)
        start_x = (width - modal_width) // 2
        start_y = (height - modal_height) // 2

        try:
            # Draw modal background
            for y in range(start_y, start_y + modal_height):
                self.stdscr.addstr(y, start_x, " " * modal_width, curses.color_pair(1))

            # Top border
            self.stdscr.addstr(start_y, start_x, "╔" + "═" * (modal_width - 2) + "╗", curses.color_pair(1) | curses.A_BOLD)

            # Title - show actual date(s) being viewed
            if self.display_mode == 1:
                view_days = self.current_view_date.strftime("%a %b %d")
            else:
                # Two-day view
                next_day = self.current_view_date + timedelta(days=1)
                view_days = f"{self.current_view_date.strftime('%a %b %d')} - {next_day.strftime('%a %b %d')}"
            title = f" Calendar Recommendations ({view_days}) "
            title_x = start_x + (modal_width - len(title)) // 2
            self.stdscr.addstr(start_y, title_x, title, curses.color_pair(1) | curses.A_BOLD)

            current_y = start_y + 1

            # Draw separator
            self.stdscr.addstr(current_y, start_x, "║" + "─" * (modal_width - 2) + "║", curses.color_pair(1))
            current_y += 1

            # If loading, show animated spinner in center
            if self.recommendations_loading:
                spinner_char = self.spinner_frames[self.spinner_index]
                loading_lines = [
                    "",
                    f"{spinner_char} Analyzing calendar and generating recommendations...",
                    "",
                    "This may take a moment.",
                    "",
                    "Press ESC to cancel"
                ]

                # Calculate center position
                content_start_y = start_y + (modal_height // 2) - (len(loading_lines) // 2)

                for i, line in enumerate(loading_lines):
                    y_pos = content_start_y + i
                    if start_y + 2 <= y_pos < start_y + modal_height - 2:
                        self.stdscr.addstr(y_pos, start_x, "║", curses.color_pair(1))
                        # Pad line to full width to prevent ghosting of old spinner frames
                        line_padded = line.center(modal_width - 2)
                        self.stdscr.addstr(y_pos, start_x + 1, line_padded, curses.color_pair(1) | curses.A_BOLD)
                        self.stdscr.addstr(y_pos, start_x + modal_width - 1, "║", curses.color_pair(1))

                # Fill remaining space above and below
                for y_pos in range(start_y + 2, start_y + modal_height - 2):
                    if y_pos < content_start_y or y_pos >= content_start_y + len(loading_lines):
                        self.stdscr.addstr(y_pos, start_x, "║" + " " * (modal_width - 2) + "║", curses.color_pair(1))

            else:
                # Show recommendations content with word wrapping
                # Wrap text to fit modal width (accounting for borders and padding)
                max_line_width = modal_width - 4
                lines = self._wrap_text_lines(self.recommendations_text, max_line_width)

                max_content_height = modal_height - 5
                total_lines = len(lines)

                # Calculate scroll position
                visible_start = self.recommendations_scroll_offset
                visible_end = visible_start + max_content_height

                # Draw recommendations content with scrolling
                for i, line in enumerate(lines[visible_start:visible_end]):
                    if current_y >= start_y + modal_height - 3:
                        break

                    self.stdscr.addstr(current_y, start_x, "║", curses.color_pair(1))

                    # Line is already wrapped to fit, just ensure it's exactly the right length
                    display_line = line[:max_line_width].ljust(max_line_width)

                    # Color code recommendations based on original line content
                    attr = curses.color_pair(1)
                    line_stripped = line.strip()
                    if line_stripped.startswith('DECLINE:') or 'CONFLICT' in line_stripped:
                        attr = curses.color_pair(2)  # Red
                    elif line_stripped.startswith('RESCHEDULE:'):
                        attr = curses.color_pair(4)  # Magenta
                    elif line_stripped.startswith('TENTATIVE:'):
                        attr = curses.color_pair(4)  # Magenta
                    elif line_stripped.startswith('ACCEPT:'):
                        attr = curses.color_pair(3)  # Green
                    elif line_stripped and line_stripped[0].isdigit() and '. ' in line_stripped[:5]:
                        # Number followed by period (e.g., "1. ", "2. ")
                        attr = curses.color_pair(1) | curses.A_BOLD

                    self.stdscr.addstr(current_y, start_x + 2, display_line, attr)
                    self.stdscr.addstr(current_y, start_x + modal_width - 1, "║", curses.color_pair(1))
                    current_y += 1

                # Fill remaining space
                while current_y < start_y + modal_height - 2:
                    self.stdscr.addstr(current_y, start_x, "║" + " " * (modal_width - 2) + "║", curses.color_pair(1))
                    current_y += 1

            # Footer
            current_y = start_y + modal_height - 2
            if self.recommendations_loading:
                footer_text = "Press ESC to cancel"
            else:
                # Use wrapped lines for accurate scroll calculation
                max_line_width = modal_width - 4
                lines = self._wrap_text_lines(self.recommendations_text, max_line_width)
                total_lines = len(lines)
                max_content_height = modal_height - 5

                # Show scroll indicators if content is scrollable
                if total_lines > max_content_height:
                    can_scroll_up = self.recommendations_scroll_offset > 0
                    can_scroll_down = self.recommendations_scroll_offset + max_content_height < total_lines

                    scroll_hint = ""
                    if can_scroll_up and can_scroll_down:
                        scroll_hint = "↑↓ Scroll | "
                    elif can_scroll_down:
                        scroll_hint = "↓ More below | "
                    elif can_scroll_up:
                        scroll_hint = "↑ Scroll up | "

                    footer_text = f"{scroll_hint}ESC/Enter: Close | 'r': Refresh"
                else:
                    footer_text = "Press ESC or Enter to close | 'r' to refresh"

            footer_x = start_x + (modal_width - len(footer_text)) // 2
            self.stdscr.addstr(current_y, start_x, "║" + " " * (modal_width - 2) + "║", curses.color_pair(1))
            self.stdscr.addstr(current_y, footer_x, footer_text, curses.color_pair(1) | curses.A_DIM)
            current_y += 1

            # Bottom border
            self.stdscr.addstr(current_y, start_x, "╚" + "═" * (modal_width - 2) + "╝", curses.color_pair(1) | curses.A_BOLD)

        except curses.error:
            pass

        self.stdscr.refresh()

    def draw_footer(self):
        """Draw the footer with help text"""
        height, width = self.stdscr.getmaxyx()

        # Add indicator if recommendations are ready but not shown
        recommendations_indicator = ""
        if (not self.show_recommendations and
            not self.recommendations_loading and
            self._are_recommendations_valid_for_current_view()):
            recommendations_indicator = "💡 "  # Lightbulb emoji indicates recommendations are ready

        help_text = f"↑/↓: Navigate | ←/→: Prev/Next Day | 1: Single Day | 2: Two Days | Enter: Attendees | {recommendations_indicator}r: Recommendations | R: Refresh | a: Accept | t: Tentative | d: Decline/Delete | -: Toggle Declined | f: Focus | q: Quit"

        # Status legend with declined toggle indicator
        declined_status = "👁️ Shown" if self.show_declined_locally else "🙈 Hidden"
        legend = f"Status: ✅ Accepted | ⏳ Maybe/Tentative | ❓ No Response | 📋 Task | 🎧 Focus time | ⚠️  Conflict | Declined: {declined_status}"

        # Add debug indicator to legend if debug mode is enabled
        if self.debug:
            legend += " | 🐛 DEBUG MODE (stderr→debug.log)"

        try:
            self.stdscr.addstr(height - 3, 0, "─" * width)
            self.stdscr.addstr(height - 2, 2, legend[:width-4])
            self.stdscr.addstr(height - 1, 2, help_text[:width-4])

            if self.status_message:
                msg = self.status_message[:width-4]
                self.stdscr.addstr(height - 4, 2, msg, curses.color_pair(3))
        except curses.error:
            pass

    def update_status_line(self):
        """Update only the status message line without redrawing entire screen"""
        height, width = self.stdscr.getmaxyx()

        try:
            # Clear the status line
            self.stdscr.addstr(height - 4, 0, " " * width)

            # Draw the status message if there is one
            if self.status_message:
                msg = self.status_message[:width-4]
                self.stdscr.addstr(height - 4, 2, msg, curses.color_pair(3))

            # Refresh only the status line area
            self.stdscr.refresh()
        except curses.error:
            pass

    def set_loading_status(self, message: str):
        """Set status message and immediately refresh to show loading state"""
        self.status_message = message
        self.is_fetching = True
        # Force immediate screen update to show the loading message
        try:
            self.draw()
        except:
            pass  # Ignore any drawing errors during update

    def clear_loading_status(self, message: str = ""):
        """Clear loading state and optionally set completion message"""
        self.is_fetching = False
        if message:
            self.status_message = message

    def draw(self):
        """Draw the entire UI"""
        self.stdscr.clear()

        self.draw_header()
        self.draw_table_header(5)
        self.draw_events(6)
        self.draw_footer()

        # Draw attendee details overlay on top if showing
        if self.show_attendee_details:
            self.draw_attendee_details()

        # Draw recommendations overlay on top if showing
        if self.show_recommendations:
            self.draw_recommendations()

        self.stdscr.refresh()

    def handle_navigation(self, key: int):
        """Handle up/down navigation"""
        filtered_events = self.get_filtered_events()
        max_row = len(filtered_events) - 1

        if key == curses.KEY_UP:
            if self.current_row > 0:
                self.current_row -= 1

                # Adjust scroll offset if needed
                height, _ = self.stdscr.getmaxyx()
                max_rows = height - 10
                if self.current_row < self.scroll_offset:
                    self.scroll_offset = self.current_row

        elif key == curses.KEY_DOWN:
            if self.current_row < max_row:
                self.current_row += 1

                # Adjust scroll offset if needed
                height, _ = self.stdscr.getmaxyx()
                max_rows = height - 10
                if self.current_row >= self.scroll_offset + max_rows:
                    self.scroll_offset = self.current_row - max_rows + 1

    async def delete_focus_time(self):
        """Delete a focus time event (optimistic update)"""
        filtered_events = self.get_filtered_events()
        if not filtered_events or self.current_row >= len(filtered_events):
            self.status_message = "No event selected"
            return

        event = filtered_events[self.current_row]

        # Check if it's a focus time event
        if event.event_type != 'focusTime':
            self.status_message = "Only focus time events can be deleted with 'd'"
            return

        if not event.id:
            self.status_message = "Event has no ID, cannot delete"
            return

        # Clear cached recommendations since calendar is changing
        self._clear_recommendations()
        # Start fetching new recommendations in background
        self.start_recommendations_fetch(show_popup=False)

        # Capture event date for reloading later
        event_date = event.start_time.date() if event.start_time else None

        # Optimistic update: Remove from local state immediately
        event_id = event.id
        self.events = [e for e in self.events if e.id != event_id]
        self._insert_available_slots()
        self.status_message = "✅ Focus time deleted"

        # Async: Delete on server in background
        asyncio.create_task(self._delete_event_background(event_id, event_date))

    async def _delete_event_background(self, event_id: str, event_date):
        """Background task to delete event on server"""
        try:
            params = {"event_id": event_id, "send_notifications": False}
            self.debug_log(f"Background: Deleting event: {event_id}")
            result = await self.mcp_client.call_tool("delete_event", params)

            if isinstance(result, str) and ("Error:" in result or "error" in result.lower()):
                self.status_message = f"❌ Delete failed, reloading"
                self.debug_log(f"Delete error: {result}")
                await self._reload_event_day(event_date)
            else:
                self.debug_log("Background: Delete successful, reloading to sync and recalculate available slots")
                # Reload to sync server state and recalculate available slots
                await self._reload_event_day(event_date)
        except Exception as e:
            self.status_message = f"❌ Delete failed, reloading"
            self.debug_log(f"Delete exception: {e}")
            await self._reload_event_day(event_date)

    async def _reload_current_period(self, start_date: datetime = None, end_date: datetime = None):
        """Reload the current period's data

        Args:
            start_date: Optional start of period. If None, uses current_view_date start of day.
            end_date: Optional end of period. If None, calculates based on display_mode:
                      - display_mode 1: end of current day
                      - display_mode 2: end of next day (current + tomorrow)
        """
        try:
            view_date = self.current_view_date

            # Calculate start of period
            if start_date is None:
                start_date = view_date.replace(hour=0, minute=0, second=0, microsecond=0)

            # Calculate end of period based on display mode if not provided
            if end_date is None:
                if self.display_mode == 2:
                    # Two-day view: include next day
                    next_day = view_date + timedelta(days=1)
                    end_date = next_day.replace(hour=23, minute=59, second=59, microsecond=0)
                else:
                    # Single day view: just current day
                    end_date = view_date.replace(hour=23, minute=59, second=59, microsecond=0)

            self.debug_log(f"_reload_current_period: view_date={view_date.date()}, mode={self.display_mode}, range={start_date.date()} to {end_date.date()}, events_before={len(self.events)}")

            await self._fetch_week_range(start_date, end_date, replace=True)

            self.debug_log(f"_reload_current_period: events_after={len(self.events)}")
            self.draw()
        except Exception as e:
            self.debug_log(f"Error reloading current period: {e}")

    async def _reload_event_day(self, event_date):
        """Reload the specific day an event is on"""
        if not event_date:
            self.debug_log("No event date provided, reloading current period instead")
            await self._reload_current_period()
            return

        try:
            # Convert date to datetime for the API call
            from datetime import datetime
            event_datetime = datetime.combine(event_date, datetime.min.time())
            start_of_day = event_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = event_datetime.replace(hour=23, minute=59, second=59, microsecond=0)

            self.debug_log(f"Reloading events for {event_date}")
            await self._fetch_week_range(start_of_day, end_of_day, replace=True)
            self.draw()
        except Exception as e:
            self.debug_log(f"Error reloading event day {event_date}: {e}")

    async def handle_rsvp(self, response: str):
        """Handle RSVP response (accept/tentative/decline) with optimistic update"""
        filtered_events = self.get_filtered_events()
        if not filtered_events or self.current_row >= len(filtered_events):
            return

        event = filtered_events[self.current_row]

        # Store event date for reloading the correct day later
        event_date = event.start_time.date() if event.start_time else None

        # Clear cached recommendations since calendar is changing
        self._clear_recommendations()
        # Start fetching new recommendations in background
        self.start_recommendations_fetch(show_popup=False)

        # Optimistic update: Update local state immediately
        event_id = event.id
        for e in self.events:
            if e.id == event_id:
                # Update the response status locally
                if response == 'accepted':
                    e.response_status = 'accepted'
                    self.status_message = "✅ Event accepted"
                elif response == 'tentative':
                    e.response_status = 'tentative'
                    self.status_message = "✅ Event tentative"
                elif response == 'declined':
                    e.response_status = 'declined'
                    self.status_message = "✅ Event declined"
                break

        # Async: Update on server in background, pass event date for reloading
        asyncio.create_task(self._update_rsvp_background(event_id, response, event_date))

    async def _update_rsvp_background(self, event_id: str, response: str, event_date):
        """Background task to update RSVP on server - single event only"""
        try:
            # Find the event in our local state to get attendees
            event = None
            for e in self.events:
                if e.id == event_id:
                    event = e
                    break

            if not event:
                self.debug_log(f"Event {event_id} not found for RSVP update")
                return

            # Build attendees list with updated response - SINGLE EVENT ONLY
            attendees = []
            for attendee in event.attendees:
                attendee_data = {"email": attendee.get('email')}
                if attendee.get('self', False):
                    # Only update this one event's response
                    attendee_data["response_status"] = response
                else:
                    # Preserve other attendees' status unchanged
                    attendee_data["response_status"] = attendee.get('responseStatus', 'needsAction')
                attendees.append(attendee_data)

            self.debug_log(f"Background: Updating RSVP for single event {event_id} to {response}")
            result = await self.mcp_client.call_tool(
                "edit_event",
                {
                    "event_id": event_id,
                    "attendees": attendees,
                    "send_notifications": False
                }
            )

            if isinstance(result, str) and ("Error:" in result or "error" in result.lower()):
                self.status_message = f"❌ RSVP update failed, reloading"
                self.debug_log(f"RSVP error: {result}")
                await self._reload_event_day(event_date)
            else:
                self.debug_log("Background: RSVP update successful, reloading to hide/show events")
                # Reload the specific day this event is on to hide declined events (show_declined=False)
                await self._reload_event_day(event_date)

        except Exception as e:
            self.status_message = f"❌ RSVP update failed, reloading"
            self.debug_log(f"RSVP exception: {e}")
            await self._reload_event_day(event_date)

    async def create_focus_time(self):
        """Create a focus time block from the selected available slot with optimistic update"""
        self.debug_log("=== create_focus_time() called ===")

        # Check if we have events
        if not self.events:
            self.status_message = "No events loaded"
            self.debug_log("No events loaded")
            return

        # Check if current selection is an available slot (use filtered events!)
        filtered_events = self.get_filtered_events()
        current_event = None
        if self.current_row < len(filtered_events):
            current_event = filtered_events[self.current_row]
            self.debug_log(f"Selected event: is_available={current_event.is_available}, summary='{current_event.summary}'")

        # Only create focus time if on an available slot
        if current_event and current_event.is_available:
            self.debug_log("Creating focus time for single available slot - optimistic update")

            # Clear cached recommendations since calendar is changing
            self._clear_recommendations()
            # Start fetching new recommendations in background
            self.start_recommendations_fetch(show_popup=False)

            # Capture event date for reloading later
            event_date = current_event.start_time.date() if current_event.start_time else None

            self._optimistic_create_single_focus_time(current_event)
            # Background API call
            asyncio.create_task(self._create_single_focus_time_background(current_event, event_date))
        else:
            self.status_message = "❌ Select an available time slot first (press 'f' on green boxes)"
            self.debug_log("No available slot selected")

    def _optimistic_create_single_focus_time(self, available_slot):
        """Optimistically create focus time locally (instant UI update)"""
        start_time = available_slot.start_time
        end_time = available_slot.end_time

        if not start_time or not end_time:
            return

        # Calculate duration and title
        duration_minutes = (end_time - start_time).total_seconds() / 60
        if duration_minutes <= 40:
            title = "Paperwork - Focus time"
        else:
            title = "Development - Focus time"

        # Create a temporary focus time event
        focus_event = CalendarEvent({
            'id': f'temp-focus-{int(start_time.timestamp())}',  # Temporary ID
            'summary': title,
            'start': {'dateTime': start_time.isoformat()},
            'end': {'dateTime': end_time.isoformat()},
            'status': 'confirmed',
            'eventType': 'focusTime',
            'colorId': '5',  # Yellow
            'focusTimeProperties': {
                'autoDeclineMode': 'declineOnlyNewConflictingInvitations',
                'chatStatus': 'doNotDisturb'
            }
        }, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour)

        # Remove the available slot and add the focus time event
        # Find and remove the available slot
        for i, e in enumerate(self.events):
            if e == available_slot:
                self.events.pop(i)
                break

        # Add the focus time event
        self.events.append(focus_event)

        # Re-insert available slots to recalculate gaps
        self._insert_available_slots()

        # Set status message
        self.status_message = f"✅ Creating {int(duration_minutes)}min {title}..."
        self.debug_log(f"Optimistic: Added temp focus time event, removed available slot")

    async def _create_single_focus_time_background(self, available_slot, event_date):
        """Background task to create focus time on server"""
        try:
            start_time = available_slot.start_time
            end_time = available_slot.end_time

            if not start_time or not end_time:
                self.debug_log("Background: Invalid time range")
                await self._reload_event_day(event_date)
                return

            # Calculate duration and title
            duration_minutes = (end_time - start_time).total_seconds() / 60
            if duration_minutes <= 40:
                title = "Paperwork - Focus time"
            else:
                title = "Development - Focus time"

            # Prepare arguments
            args = {
                "summary": title,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "eventType": "focusTime",
                "timezone": self.timezone,
                "colorId": "5",
                "focusTimeProperties": {
                    "autoDeclineMode": "declineOnlyNewConflictingInvitations",
                    "chatStatus": "doNotDisturb"
                },
                "send_notifications": False
            }

            self.debug_log(f"Background: Creating focus time via API...")
            result = await self.mcp_client.call_tool("create_event", args)

            # Check if result contains an error
            if isinstance(result, str) and ("Error:" in result or "error" in result.lower()):
                self.debug_log(f"Background: API error: {result}")
                self.status_message = f"❌ Focus time creation failed, reloading"
                await self._reload_event_day(event_date)
            else:
                self.debug_log("Background: Focus time created successfully, reloading to get real event ID")
                self.status_message = f"✅ Created {int(duration_minutes)}min {title}"
                # Reload to replace temp event ID with real server ID
                await self._reload_event_day(event_date)

        except Exception as e:
            self.debug_log(f"Background: Exception creating focus time: {e}")
            self.status_message = f"❌ Focus time creation failed, reloading"
            await self._reload_event_day(event_date)

    def navigate_to_weekday(self, direction: int):
        """Navigate to previous (-1) or next (1) weekday, skipping weekends

        Args:
            direction: -1 for previous weekday, 1 for next weekday
        """
        target_date = self.current_view_date + timedelta(days=direction)

        # Skip weekends
        while target_date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            target_date += timedelta(days=direction)

        self.current_view_date = target_date

        # Check if we need to refetch data (if target is outside loaded range)
        if self.time_min and self.time_max:
            range_start = datetime.fromisoformat(self.time_min)
            range_end = datetime.fromisoformat(self.time_max)

            # Convert to dates for comparison (ignore time component)
            target_date_only = target_date.date()
            range_start_date = range_start.date()
            range_end_date = range_end.date()

            # Only refetch if target is actually outside the loaded range
            # Add a 1-day buffer: refetch if we're going beyond loaded data
            if target_date_only < range_start_date or target_date_only > range_end_date:
                self.debug_log(f"Target date {target_date_only} is outside loaded range {range_start_date} to {range_end_date}")
                return True

        return False

    async def _fetch_week_range(self, start_date: datetime, end_date: datetime, replace: bool = False) -> bool:
        """Fetch events for a specific date range and merge with existing events

        Args:
            start_date: Start of date range
            end_date: End of date range
            replace: If True, replace events in range (for reloads). If False, merge (for background fetch)
        """
        try:
            params = {
                "time_filter": "custom",
                "time_min": start_date.isoformat(),
                "time_max": end_date.isoformat(),
                "timezone": self.timezone,
                "detect_overlaps": True,
                "show_declined": True,  # Always fetch declined events for toggle visibility
                "max_results": 250,
                "output_format": "json"
            }

            result = await self.mcp_client.call_tool("list_events", params)

            # Parse the JSON result
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result

            events_list = data.get('events', [])
            new_events = [CalendarEvent(e, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour) for e in events_list]

            # Filter out all-day events that started before today
            today = datetime.now().date()
            filtered_new_events = []
            for event in new_events:
                if event.is_all_day and event.start_time:
                    event_date = event.start_time.date()
                    if event_date < today:
                        continue
                filtered_new_events.append(event)

            if replace:
                # REPLACE mode: Remove all existing events in range, then add new ones
                # This ensures temp events (like temp-focus-*) get replaced by real server events
                def event_in_range(event, range_start, range_end):
                    if not event.start_time:
                        return False
                    # Check if event starts within the reload range
                    return range_start <= event.start_time < range_end

                # Keep only events outside the reload range
                self.events = [e for e in self.events if not event_in_range(e, start_date, end_date)]

                # Add all new events from server
                self.events.extend(filtered_new_events)
            else:
                # MERGE mode: Add new events, avoiding duplicates by ID
                # Used for background fetch to accumulate data from multiple weeks
                existing_ids = {e.id for e in self.events if e.id}
                for event in filtered_new_events:
                    if event.id and event.id not in existing_ids:
                        self.events.append(event)
                        existing_ids.add(event.id)

            # Client-side filter: Remove conflicts involving declined events
            # Declined events should NEVER cause conflicts, regardless of toggle state
            declined_ids = {e.id for e in self.events if e.response_status == 'declined'}
            for event in self.events:
                if event.response_status == 'declined':
                    # Declined events themselves have no conflicts
                    event.has_overlap = False
                    event.overlapping_event_ids = []
                elif event.has_overlap and event.overlapping_event_ids:
                    # Remove declined event IDs from overlap list
                    event.overlapping_event_ids = [
                        eid for eid in event.overlapping_event_ids if eid not in declined_ids
                    ]
                    # If no overlaps remain, clear the flag
                    if not event.overlapping_event_ids:
                        event.has_overlap = False

            # Re-insert available slots
            self._insert_available_slots()

            # Update the overall time range FIRST
            if self.time_min:
                current_min = datetime.fromisoformat(self.time_min)
                if start_date < current_min:
                    self.time_min = start_date.isoformat()
            else:
                self.time_min = start_date.isoformat()

            if self.time_max:
                current_max = datetime.fromisoformat(self.time_max)
                if end_date > current_max:
                    self.time_max = end_date.isoformat()
            else:
                self.time_max = end_date.isoformat()

            # Update loaded dates for mini calendar AFTER updating time range
            self._update_loaded_dates()

            return True

        except Exception as e:
            self.debug_log(f"Error fetching week range: {e}")
            return False

    async def _fetch_more_data(self, direction: int):
        """Fetch more data in the requested direction (background task)

        Args:
            direction: -1 for previous week, 1 for next week
        """
        try:
            now = datetime.now().astimezone()

            if direction < 0:
                # Fetch previous week
                if self.time_min:
                    current_start = datetime.fromisoformat(self.time_min)
                    # Go back one more week
                    new_start = current_start - timedelta(days=7)
                    new_end = current_start - timedelta(days=1)

                    self.set_loading_status("📥 Loading previous week...")
                    success = await self._fetch_week_range(
                        new_start.replace(hour=0, minute=0, second=0, microsecond=0),
                        new_end.replace(hour=23, minute=59, second=59, microsecond=0)
                    )
                    self.clear_loading_status()

                    if success:
                        self.status_message = "✅ Previous week loaded"
                        self.draw()  # Redraw to show loaded days
                    else:
                        self.status_message = "⚠️ Failed to load previous week"
            else:
                # Fetch next week
                if self.time_max:
                    current_end = datetime.fromisoformat(self.time_max)
                    # Go forward one more week
                    new_start = current_end + timedelta(days=1)
                    new_end = current_end + timedelta(days=7)

                    self.set_loading_status("📥 Loading next week...")
                    success = await self._fetch_week_range(
                        new_start.replace(hour=0, minute=0, second=0, microsecond=0),
                        new_end.replace(hour=23, minute=59, second=59, microsecond=0)
                    )
                    self.clear_loading_status()

                    if success:
                        self.status_message = "✅ Next week loaded"
                        self.draw()  # Redraw to show loaded days
                    else:
                        self.status_message = "⚠️ Failed to load next week"

        except Exception as e:
            self.debug_log(f"Error fetching more data: {e}")
            self.status_message = f"❌ Error loading data: {str(e)}"

    async def _background_fetch_full_range(self):
        """Background task to incrementally fetch full 3-week range"""
        try:
            # Small delay to let UI render first
            await asyncio.sleep(0.5)

            now = datetime.now().astimezone()

            # Calculate week boundaries
            days_since_monday = now.weekday()  # 0 = Monday, 6 = Sunday
            current_monday = now - timedelta(days=days_since_monday)
            current_sunday = current_monday + timedelta(days=6)

            previous_monday = current_monday - timedelta(days=7)
            previous_sunday = previous_monday + timedelta(days=6)

            next_monday = current_monday + timedelta(days=7)
            next_sunday = next_monday + timedelta(days=6)

            # Step 1: Complete the current week (we already have today/tomorrow)
            # Decide: load whole week vs remaining days
            # If we're early in the week (Mon-Tue), load whole week is simpler/faster
            # If we're later (Wed-Sun), load remaining days

            days_remaining = 6 - now.weekday()  # Days left in week (0 = Sunday is last day)

            # Always load the full current week to ensure we have past days
            self.set_loading_status("📥 Loading current week...")
            self.debug_log("Fetching current week (full week)")

            week_start = current_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = current_sunday.replace(hour=23, minute=59, second=59, microsecond=0)

            success = await self._fetch_week_range(week_start, week_end)
            self.clear_loading_status()

            if success:
                self.status_message = "✅ Current week loaded"
                self.draw()  # Redraw to show loaded days in calendar
                await asyncio.sleep(0.3)  # Brief pause between fetches
            else:
                self.status_message = "⚠️ Current week fetch failed"
                await asyncio.sleep(0.3)

            # Step 2: Load next week
            self.set_loading_status("📥 Loading next week...")
            self.debug_log("Fetching next week")

            next_week_start = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            next_week_end = next_sunday.replace(hour=23, minute=59, second=59, microsecond=0)

            success = await self._fetch_week_range(next_week_start, next_week_end)
            self.clear_loading_status()
            if success:
                self.status_message = "✅ Next week loaded"
                self.draw()  # Redraw to show loaded days in calendar
                await asyncio.sleep(0.3)
            else:
                self.status_message = "⚠️ Next week fetch failed"
                await asyncio.sleep(0.3)

            # Step 3: Load previous week
            self.set_loading_status("📥 Loading previous week...")
            self.debug_log("Fetching previous week")

            prev_week_start = previous_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            prev_week_end = previous_sunday.replace(hour=23, minute=59, second=59, microsecond=0)

            success = await self._fetch_week_range(prev_week_start, prev_week_end)
            self.clear_loading_status()
            if success:
                self.status_message = "✅ Full calendar loaded (3 weeks)"
                self.debug_log("Background fetch completed successfully")
                self.draw()  # Final redraw to show all loaded days
            else:
                self.status_message = "⚠️ Previous week fetch failed"

        except Exception as e:
            self.debug_log(f"Background fetch error: {e}")
            import traceback
            self.debug_log(traceback.format_exc())
            self.status_message = f"❌ Background fetch error: {str(e)}"


    async def run(self):
        """Main event loop"""
        # Quick initial fetch (today + tomorrow if weekday) for fast startup
        success = await self.run_with_spinner(
            self.fetch_events(quick_mode=True),
            "Loading today...",
            "✅ Ready!"
        )
        if not success:
            # Show the actual error message
            error_msg = f"Failed to fetch events: {self.status_message}. Press any key to exit."
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, error_msg)
            self.stdscr.refresh()
            self.stdscr.nodelay(False)  # Make blocking
            self.stdscr.getch()
            return

        # Position cursor at current/next event on initial load
        self._find_current_event()

        # Set non-blocking input
        self.stdscr.nodelay(True)

        # Draw initial UI
        self.draw()

        # Start background fetch for full 3 weeks
        self.background_fetch_task = asyncio.create_task(self._background_fetch_full_range())

        # Start background recommendations fetch (silently, without showing popup)
        self.start_recommendations_fetch(show_popup=False)

        while True:
            # Check for key input (non-blocking)
            try:
                key = self.stdscr.getch()
            except:
                key = -1

            # Small delay to prevent busy-waiting
            await asyncio.sleep(0.05)

            # Update spinner if loading (runs even when no key pressed)
            if self.is_loading:
                self.update_spinner()
                self.update_status_line()

            # Update recommendations modal spinner if loading recommendations
            if self.recommendations_loading and self.show_recommendations:
                self.spinner_index = (self.spinner_index + 1) % len(self.spinner_frames)
                # Only redraw the modal overlay, not the entire screen
                self.draw_recommendations()

            # Update header only if fetching data in background (to animate spinner in title)
            if self.is_fetching:
                self.draw_header()

            # Skip key processing if no key was pressed
            if key == -1:
                continue

            # Track if we need to redraw
            needs_redraw = True

            if key == ord('q'):
                break
            elif key in [curses.KEY_UP, curses.KEY_DOWN]:
                # Handle scrolling in recommendations modal
                if self.show_recommendations and not self.recommendations_loading:
                    # Use wrapped lines for accurate scrolling
                    height, width = self.stdscr.getmaxyx()
                    modal_width = min(100, width - 4)
                    modal_height = min(40, height - 4)
                    max_line_width = modal_width - 4
                    lines = self._wrap_text_lines(self.recommendations_text, max_line_width)
                    max_content_height = modal_height - 5
                    total_lines = len(lines)

                    if key == curses.KEY_UP:
                        if self.recommendations_scroll_offset > 0:
                            self.recommendations_scroll_offset -= 1
                    elif key == curses.KEY_DOWN:
                        if self.recommendations_scroll_offset + max_content_height < total_lines:
                            self.recommendations_scroll_offset += 1
                # Don't navigate if attendee details showing
                elif not self.show_attendee_details:
                    self.handle_navigation(key)
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                # Enter key - toggle attendee details or close recommendations
                if self.show_attendee_details:
                    # Close the attendee details overlay
                    self.show_attendee_details = False
                    self.attendee_details_event = None
                elif self.show_recommendations:
                    # Close recommendations modal (even if loading)
                    self.show_recommendations = False
                    # Cancel background task if still running
                    if self.recommendations_loading and self.recommendations_task:
                        self.recommendations_task.cancel()
                        self.recommendations_loading = False
                        self.status_message = "Recommendations request cancelled"
                else:
                    # Show attendee details for current event
                    filtered_events = self.get_filtered_events()
                    if filtered_events and self.current_row < len(filtered_events):
                        event = filtered_events[self.current_row]
                        # Only show if event has attendees and is not an available slot
                        if not event.is_available and event.attendees:
                            self.show_attendee_details = True
                            self.attendee_details_event = event
                        else:
                            self.status_message = "No attendees for this event"
                            needs_redraw = False
            elif key == 27:  # ESC key
                # Close attendee details or recommendations if showing
                if self.show_attendee_details:
                    self.show_attendee_details = False
                    self.attendee_details_event = None
                elif self.show_recommendations:
                    # Close recommendations modal (even if loading)
                    self.show_recommendations = False
                    # Cancel background task if still running
                    if self.recommendations_loading and self.recommendations_task:
                        self.recommendations_task.cancel()
                        self.recommendations_loading = False
                        self.status_message = "Recommendations request cancelled"
                else:
                    needs_redraw = False
            elif key == curses.KEY_LEFT:
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Navigate to previous weekday
                prev_date = self.current_view_date
                needs_refetch = self.navigate_to_weekday(-1)
                if needs_refetch:
                    # Revert navigation - can't go beyond loaded data yet
                    self.current_view_date = prev_date

                    # Check if background task is still running
                    if self.background_fetch_task and not self.background_fetch_task.done():
                        self.status_message = "⏳ Loading data... (background fetch in progress)"
                    else:
                        # Background fetch complete but still need more data - start new fetch
                        self.background_fetch_task = asyncio.create_task(self._fetch_more_data(-1))
                        self.status_message = "⏳ Loading previous data..."
                    needs_redraw = False  # Don't redraw since we didn't actually move
                else:
                    # Clear cached recommendations since view is changing
                    self._clear_recommendations()
                    self.current_row = 0
                    self.scroll_offset = 0
                    # Start fetching recommendations for new view in background
                    self.start_recommendations_fetch(show_popup=False)
                    needs_redraw = True
            elif key == curses.KEY_RIGHT:
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Navigate to next weekday
                prev_date = self.current_view_date
                needs_refetch = self.navigate_to_weekday(1)
                if needs_refetch:
                    # Revert navigation - can't go beyond loaded data yet
                    self.current_view_date = prev_date

                    # Check if background task is still running
                    if self.background_fetch_task and not self.background_fetch_task.done():
                        self.status_message = "⏳ Loading data... (background fetch in progress)"
                    else:
                        # Background fetch complete but still need more data - start new fetch
                        self.background_fetch_task = asyncio.create_task(self._fetch_more_data(1))
                        self.status_message = "⏳ Loading future data..."
                    needs_redraw = False  # Don't redraw since we didn't actually move
                else:
                    # Clear cached recommendations since view is changing
                    self._clear_recommendations()
                    self.current_row = 0
                    self.scroll_offset = 0
                    # Start fetching recommendations for new view in background
                    self.start_recommendations_fetch(show_popup=False)
                    needs_redraw = True
            elif key == ord('1'):
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Switch to single day view and reset to today
                # Clear cached recommendations since view is changing
                self._clear_recommendations()
                self.display_mode = 1
                self.current_view_date = datetime.now().astimezone()
                self.current_row = 0
                self.scroll_offset = 0
                self._find_current_event()  # Position at current/next event
                self.status_message = "Single day view (today)"
                # Start fetching recommendations for new view in background
                self.start_recommendations_fetch(show_popup=False)
                needs_redraw = True
            elif key == ord('2'):
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Switch to two day view and reset to today
                # Clear cached recommendations since view is changing
                self._clear_recommendations()
                self.display_mode = 2
                self.current_view_date = datetime.now().astimezone()
                self.current_row = 0
                self.scroll_offset = 0
                self._find_current_event()  # Position at current/next event
                self.status_message = "Two day view (today + tomorrow)"
                # Start fetching recommendations for new view in background
                self.start_recommendations_fetch(show_popup=False)
                needs_redraw = True
            elif key == ord('a'):
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Accept - optimistic update (instant, no spinner)
                await self.handle_rsvp('accepted')
                needs_redraw = True
            elif key == ord('t'):
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Tentative - optimistic update (instant, no spinner)
                await self.handle_rsvp('tentative')
                needs_redraw = True
            elif key == ord('d'):
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Check event type to determine action
                filtered_events = self.get_filtered_events()
                if filtered_events and self.current_row < len(filtered_events):
                    event = filtered_events[self.current_row]
                    if event.event_type == 'task':
                        # Block deletion of tasks - they must be completed in Google Tasks
                        self.status_message = "❌ Tasks cannot be deleted from calendar. Mark complete in Google Tasks."
                        needs_redraw = True
                    elif event.event_type == 'focusTime':
                        # Delete focus time - optimistic update (instant, no spinner)
                        await self.delete_focus_time()
                        needs_redraw = True
                    else:
                        # Decline regular event - optimistic update (instant, no spinner)
                        await self.handle_rsvp('declined')
                        needs_redraw = True
                else:
                    # Decline - optimistic update (instant, no spinner)
                    await self.handle_rsvp('declined')
                    needs_redraw = True
            elif key == ord('f'):
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Optimistic update - instant, no spinner
                await self.create_focus_time()
                # Redraw full screen to show new focus time event
                needs_redraw = True
            elif key == ord('r'):
                # Get/show recommendations
                if self.show_recommendations and not self.recommendations_loading:
                    # If already showing, refresh the recommendations
                    self.start_recommendations_fetch(show_popup=True)
                elif not self.show_recommendations and self._are_recommendations_valid_for_current_view() and not self.recommendations_loading:
                    # Recommendations already cached for this exact view, just show them
                    self.show_recommendations = True
                    self.recommendations_scroll_offset = 0
                else:
                    # Fetch and show recommendations (either no cache or cache is stale)
                    self.start_recommendations_fetch(show_popup=True)
                needs_redraw = True
            elif key == ord('R'):
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Refresh current period (respects display_mode: 1 day or 2 days)
                self._clear_recommendations()
                if self.display_mode == 2:
                    loading_msg = "Refreshing today + tomorrow..."
                    success_msg = "✅ Refreshed today + tomorrow"
                else:
                    loading_msg = "Refreshing today..."
                    success_msg = "✅ Refreshed today"

                await self.run_with_spinner(
                    self._reload_current_period(),
                    loading_msg,
                    success_msg
                )
                # Start fetching new recommendations in background
                self.start_recommendations_fetch(show_popup=False)
                needs_redraw = True
            elif key == ord('-'):
                # Ignore if modal is open
                if self.show_attendee_details or self.show_recommendations:
                    needs_redraw = False
                    continue

                # Toggle showing/hiding declined events
                self.show_declined_locally = not self.show_declined_locally

                if self.show_declined_locally:
                    self.status_message = "👁️ Showing declined events"

                    # Debug: Dump in-memory events when showing declined
                    import sys
                    declined_events = [e for e in self.events if e.response_status == 'declined']
                    print(f"\n[DEBUG] === Toggled to SHOW declined events ===", file=sys.stderr, flush=True)
                    print(f"[DEBUG] Total events in memory: {len(self.events)}", file=sys.stderr, flush=True)
                    print(f"[DEBUG] Declined events in memory: {len(declined_events)}", file=sys.stderr, flush=True)
                    if declined_events:
                        print(f"[DEBUG] Declined events:", file=sys.stderr, flush=True)
                        for e in declined_events:
                            start_str = e.start_time.strftime('%Y-%m-%d %H:%M') if e.start_time else 'N/A'
                            print(f"[DEBUG]   - {start_str} | {e.summary} | id={e.id}", file=sys.stderr, flush=True)
                    else:
                        print(f"[DEBUG] No declined events found in memory!", file=sys.stderr, flush=True)
                else:
                    self.status_message = "🙈 Hiding declined events"

                # No need to reload - just redraw with new filter
                # Declined events are always fetched and never block time/conflicts
                needs_redraw = True
            else:
                needs_redraw = False

            # Only redraw if there was a state change
            if needs_redraw:
                self.draw()


def parse_day_filter(day_str: str) -> tuple:
    """Parse day filter and return (time_filter, time_min, time_max)"""
    # Handle standard filters
    if day_str.lower() in ['today', 'this_week', 'next_week']:
        return (day_str.lower(), None, None)

    # Handle tomorrow
    if day_str.lower() == 'tomorrow':
        now = datetime.now().astimezone()
        tomorrow = now + timedelta(days=1)
        start_of_day = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)
        return ('custom', start_of_day.isoformat(), end_of_day.isoformat())

    # Map day abbreviations to weekday numbers (0=Monday, 6=Sunday)
    day_map = {
        'mon': 0,
        'tue': 1,
        'wed': 2,
        'thu': 3,
        'fri': 4,
        'sat': 5,
        'sun': 6
    }

    day_abbr = day_str.lower()[:3]
    if day_abbr not in day_map:
        return ('today', None, None)  # Default to today if invalid

    target_weekday = day_map[day_abbr]

    # Get current date and weekday (with timezone)
    now = datetime.now().astimezone()
    current_weekday = now.weekday()

    # Calculate days until target weekday
    days_ahead = target_weekday - current_weekday

    # If target day is before today, go to next week
    if days_ahead < 0:
        days_ahead += 7

    # Calculate target date
    target_date = now + timedelta(days=days_ahead)

    # Set time range for the entire day (timezone-aware)
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=0)

    return ('custom', start_of_day.isoformat(), end_of_day.isoformat())


def get_system_timezone():
    """Get the system timezone from environment or detect from system"""
    # First check TZ environment variable
    tz = os.environ.get('TZ')
    if tz:
        return tz

    # Try to get timezone from system
    try:
        # Get local timezone info
        local_tz = datetime.now().astimezone().tzinfo
        # Try to get the zone name (works on most systems)
        if hasattr(local_tz, 'zone'):
            return local_tz.zone
        elif hasattr(local_tz, 'key'):
            return local_tz.key
    except:
        pass

    # Fallback to UTC if we can't detect
    return 'UTC'


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Interactive Calendar TUI')
    parser.add_argument('--timezone', default=None, help='Timezone for events (default: system timezone)')
    parser.add_argument('--filter', default='today',
                       help='Time filter: today, this_week, next_week, tomorrow, or day abbreviation (mon-sun)')
    parser.add_argument('--server-path', help='Path to gcal-mcp-server binary')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging to stderr')

    args = parser.parse_args()

    # Use provided timezone or detect from system
    if args.timezone is None:
        args.timezone = get_system_timezone()

    server_path = args.server_path or "/home/jpacker/workspace_git/gcal-mcp-server/bin/gcal-mcp-server"

    # Shared state for MCP client
    mcp_client = None

    async def async_run_app(stdscr):
        """Async function that runs inside curses"""
        nonlocal mcp_client

        # Create and connect MCP client
        mcp_client = MCPClient(server_path)
        await mcp_client.connect()

        try:
            # Parse the filter
            time_filter, time_min, time_max = parse_day_filter(args.filter)

            # Run the TUI
            app = CalendarTUI(stdscr, mcp_client, timezone=args.timezone, debug=args.debug)
            app.time_filter = time_filter
            app.time_min = time_min
            app.time_max = time_max
            await app.run()
        finally:
            # Disconnect
            await mcp_client.disconnect()

    def curses_main(stdscr):
        """Curses wrapper function - runs the async event loop"""
        # Run the async app in the current thread
        asyncio.run(async_run_app(stdscr))

    # Print debug instructions before curses takes over the terminal
    if args.debug:
        import sys
        print("\n" + "="*70, file=sys.stderr)
        print("🐛 DEBUG MODE ENABLED", file=sys.stderr)
        print("="*70, file=sys.stderr)
        print("Debug logs are being written to stderr.", file=sys.stderr)
        print("\nTo view logs while using the TUI, run in another terminal:", file=sys.stderr)
        print("  tail -f debug.log", file=sys.stderr)
        print("\nOr run with output redirection:", file=sys.stderr)
        print("  python3 calendar_tui.py --debug 2>debug.log", file=sys.stderr)
        print("\nPress Enter to start the TUI...", file=sys.stderr)
        print("="*70 + "\n", file=sys.stderr)
        input()  # Wait for user to press Enter

    # Run curses wrapper
    try:
        curses.wrapper(curses_main)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
