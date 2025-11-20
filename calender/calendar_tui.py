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
from datetime import datetime, timedelta, timezone
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
        start_hour = self.start_time.hour
        end_hour = self.end_time.hour

        # Determine if fully outside core hours, partially outside, or fully inside
        is_outside_core = (end_hour <= self.core_start_hour or start_hour >= self.core_end_hour)

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
                return attendee.get('responseStatus', 'needsAction')
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

        # Time filter parameters
        self.time_filter = "today"
        self.time_min = None
        self.time_max = None

        # Core hours (9am to 5pm)
        self.core_start_hour = 9
        self.core_end_hour = 17

        # Recommendations (displayed inline below events, non-interactive)
        self.show_recommendations = False
        self.recommendations_text = ""
        self.recommendations_list = []  # Parsed list of recommendation items (max 2 lines each)
        self.recommendations_task = None  # Background task for fetching recommendations

        # Attendee details overlay
        self.show_attendee_details = False
        self.attendee_details_event = None

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

        # Regular colors (text on black background)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)  # Default selection (black on white)
        curses.init_pair(2, conflict_color, curses.COLOR_BLACK)  # Declined/Overlap (dark red)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Accepted
        curses.init_pair(4, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Tentative (magenta)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Light grey (Available/needsAction)
        curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Focus time (yellow)
        curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)   # Links

        # Selection colors (colored text on white background)
        curses.init_pair(8, conflict_color, curses.COLOR_WHITE)  # Selected conflict/declined (red on white)
        curses.init_pair(9, curses.COLOR_MAGENTA, curses.COLOR_WHITE) # Selected tentative (magenta on white)
        curses.init_pair(10, curses.COLOR_YELLOW, curses.COLOR_WHITE) # Selected focus time (yellow on white)

        # Dark grey for out-of-hours available slots (dimmed white appears grey)
        curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Will be used with A_DIM

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

    async def fetch_events(self, time_filter: str = "today", time_min: str = None, time_max: str = None) -> bool:
        """Fetch events from MCP server"""
        try:
            # Build request parameters
            params = {
                "time_filter": time_filter,
                "timezone": self.timezone,
                "detect_overlaps": True,
                "show_declined": False,
                "max_results": 250,
                "output_format": "json"
            }

            # Add time_min and time_max if using custom filter
            if time_filter == "custom" and time_min and time_max:
                params["time_min"] = time_min
                params["time_max"] = time_max

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

            # Insert available time slots
            self._insert_available_slots()

            # Start background recommendations analysis
            self.start_recommendations_analysis()

            return True

        except json.JSONDecodeError as e:
            self.status_message = f"JSON parse error: {str(e)}. Result: {result[:200] if isinstance(result, str) else result}"
            return False
        except Exception as e:
            import traceback
            self.status_message = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return False

    def _find_current_event(self):
        """Find and position cursor at the current or next event"""
        if not self.events:
            return

        now = datetime.now().astimezone()

        # First, try to find the currently active event
        for i, event in enumerate(self.events):
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
        for i, event in enumerate(self.events):
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
        """Insert available time slots for gaps of 30min or more"""
        # Filter out all-day events and sort by start time
        timed_events = [e for e in self.events if not e.is_all_day and e.start_time]
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

            # Add the event first
            new_events.append(event)

            # Check if this is the first event and it ends before core hours start
            added_core_hours_slot = False
            if i == 0 and event.end_time < core_start:
                # Add grey available slot between event end and core start
                available_event = CalendarEvent({
                    'start': {'dateTime': event.end_time.isoformat()},
                    'end': {'dateTime': core_start.isoformat()}
                }, is_available=True, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour)
                new_events.append(available_event)
                added_core_hours_slot = True

            # Check if there's a next event
            if i < len(timed_events) - 1:
                next_event = timed_events[i + 1]
                gap_minutes = (next_event.start_time - event.end_time).total_seconds() / 60

                # Only add available slot if:
                # 1. Gap is 30min or more
                # 2. We didn't already add a core-hours slot (to avoid duplicates)
                # 3. No other events overlap this gap
                # Note: Grey vs green boxes are determined by CalendarEvent based on core hours
                if gap_minutes >= 30 and not added_core_hours_slot:
                    # Check if any other events overlap this potential gap
                    gap_start = event.end_time
                    gap_end = next_event.start_time
                    has_overlap = False

                    for other_event in timed_events:
                        # Skip the current event and next event
                        if other_event == event or other_event == next_event:
                            continue

                        # Check if this event overlaps the gap
                        # Event overlaps if: event_start < gap_end AND event_end > gap_start
                        if other_event.start_time < gap_end and other_event.end_time > gap_start:
                            has_overlap = True
                            break

                    # Only insert available slot if there's no overlap
                    if not has_overlap:
                        available_event = CalendarEvent({
                            'start': {'dateTime': event.end_time.isoformat()},
                            'end': {'dateTime': next_event.start_time.isoformat()}
                        }, is_available=True, core_start_hour=self.core_start_hour, core_end_hour=self.core_end_hour)
                        new_events.append(available_event)

        # Add back all-day events at the beginning
        all_day_events = [e for e in self.events if e.is_all_day]
        self.events = all_day_events + new_events

    def draw_header(self):
        """Draw the application header"""
        height, width = self.stdscr.getmaxyx()

        title = "📅 Interactive Calendar"
        date_str = datetime.now().strftime("%A, %B %d, %Y")

        # Determine viewing period description
        period_str = ""
        if self.time_filter == "today":
            period_str = "Viewing: Today"
        elif self.time_filter == "this_week":
            period_str = "Viewing: This Week (Mon-Fri)"
        elif self.time_filter == "next_week":
            period_str = "Viewing: Next Week (Mon-Fri)"
        elif self.time_filter == "custom" and self.time_min and self.time_max:
            start = datetime.fromisoformat(self.time_min)
            end = datetime.fromisoformat(self.time_max)
            # Check if it's a single day
            if start.date() == end.date():
                period_str = f"Viewing: {start.strftime('%A, %B %d, %Y')}"
            else:
                period_str = f"Viewing: {start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"

        self.stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        self.stdscr.addstr(1, (width - len(date_str)) // 2, date_str)

        # Show viewing period if available
        if period_str:
            self.stdscr.addstr(2, (width - len(period_str)) // 2, period_str, curses.color_pair(5))

        # Draw separator
        self.stdscr.addstr(3, 0, "─" * width)

    def draw_table_header(self, start_y: int):
        """Draw the table header"""
        # Format: Day | Time | Event | 📬 | Attendees | Meet Link
        header = f"{'Day':<4} │ {'Time':<23} │ {'Event':<35} │ {'📬':<4} │ {'Attendees':<14} │ {'Meet Link':<30}"
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
            # Emoji takes 2 cells, so we pad to 22 instead of 23 to account for it
            time_str = "📅 All Day".ljust(22)
        elif event.start_time and event.end_time:
            start = event.start_time.strftime('%I:%M %p').lstrip('0')
            end = event.end_time.strftime('%I:%M %p').lstrip('0')
            time_str = f"{start} - {end}".ljust(23)

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
            if event.event_type == 'focusTime':
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
                    start_hour = event.start_time.hour
                    end_hour = event.end_time.hour
                    is_outside_core = (end_hour <= self.core_start_hour or start_hour >= self.core_end_hour)

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

            if event.event_type == 'focusTime':
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
            # Calculate link position: 1(margin) + 4(Day) + 3(│) + 23(Time) + 3(│) + 35(Event) + 3(│) + 4(Status) + 3(│) + 14(Attendees) + 3(│) = 96
            link_x = 96

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
        """Draw all events and recommendations"""
        height, width = self.stdscr.getmaxyx()
        max_rows = height - start_y - 4

        # Track row numbers and available slot counts
        row_num = 1
        available_count = 1
        current_y = start_y

        # Draw events
        for i, event in enumerate(self.events[self.scroll_offset:self.scroll_offset + max_rows]):
            actual_index = i + self.scroll_offset
            # Selection is always active (recommendations are displayed inline, not as a mode)
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

        # Draw recommendations if available (max 2 lines each, no selection)
        if self.show_recommendations:
            # Add blank line
            if current_y < height - 4:
                current_y += 1

            # Draw recommendation header
            if current_y < height - 4:
                try:
                    self.stdscr.addstr(current_y, 1, "Recommendations:", curses.A_BOLD)
                    current_y += 1
                except curses.error:
                    pass

            # Draw recommendations or "no recommendations" message
            if self.recommendations_list:
                # Draw each recommendation (2 lines max, with bullet points)
                for rec in self.recommendations_list:
                    if current_y >= height - 4:
                        break

                    try:
                        # Line 1: Bullet + Action line (e.g., "• 1. DECLINE: Meeting Title")
                        line1 = rec.get('line1', '')
                        if line1:
                            # Add bullet point
                            bullet_line = f"• {line1}"[:width-4]
                            self.stdscr.addstr(current_y, 2, bullet_line, curses.A_NORMAL)
                            current_y += 1

                        # Line 2: Reason/details (if present, indented)
                        line2 = rec.get('line2', '')
                        if line2 and current_y < height - 4:
                            # Add extra indent for second line
                            indented_line = f"  {line2}"[:width-4]
                            self.stdscr.addstr(current_y, 2, indented_line, curses.color_pair(5))  # Dimmed color
                            current_y += 1
                    except curses.error:
                        pass
            else:
                # No recommendations found
                if current_y < height - 4:
                    try:
                        self.stdscr.addstr(current_y, 2, "No recommendations - schedule looks good!", curses.color_pair(5))
                    except curses.error:
                        pass

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

    def draw_footer(self):
        """Draw the footer with help text"""
        height, width = self.stdscr.getmaxyx()

        help_text = "↑/↓: Navigate | ←/→: Prev/Next Period | Enter: Attendees | a: Accept | t: Tentative | d: Decline/Delete | f: Focus | r: Refresh | q: Quit"

        # Status legend
        legend = "Status: ✅ Accepted | ⏳ Maybe/Tentative | ❓ No Response | 🎧 Focus time | ⚠️  Conflict"

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

        self.stdscr.refresh()

    def handle_navigation(self, key: int):
        """Handle up/down navigation"""
        if key == curses.KEY_UP:
            if self.current_row > 0:
                self.current_row -= 1

                # Adjust scroll offset if needed
                height, _ = self.stdscr.getmaxyx()
                max_rows = height - 10
                if self.current_row < self.scroll_offset:
                    self.scroll_offset = self.current_row

        elif key == curses.KEY_DOWN:
            if self.current_row < len(self.events) - 1:
                self.current_row += 1

                # Adjust scroll offset if needed
                height, _ = self.stdscr.getmaxyx()
                max_rows = height - 10
                if self.current_row >= self.scroll_offset + max_rows:
                    self.scroll_offset = self.current_row - max_rows + 1

    async def delete_focus_time(self):
        """Delete a focus time event"""
        if not self.events or self.current_row >= len(self.events):
            self.status_message = "No event selected"
            return

        event = self.events[self.current_row]

        # Check if it's a focus time event
        if event.event_type != 'focusTime':
            self.status_message = "Only focus time events can be deleted with 'd'"
            return

        if not event.id:
            self.status_message = "Event has no ID, cannot delete"
            return

        try:
            self.debug_log(f"Deleting focus time event: {event.id}")

            # Call MCP delete_event tool
            result = await self.mcp_client.call_tool(
                "delete_event",
                {
                    "event_id": event.id,
                    "send_notifications": False
                }
            )

            self.debug_log(f"Delete result: {result}")

            # Check if result contains an error
            if isinstance(result, str) and ("Error:" in result or "error" in result.lower()):
                self.status_message = f"❌ Failed to delete: {result[:100]}"
                self.debug_log(f"MCP returned error: {result}")
            else:
                self.status_message = "✅ Focus time deleted"
                # Refresh events to show the deletion
                await self.fetch_events(self.time_filter, self.time_min, self.time_max)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.status_message = f"❌ Error deleting: {str(e)}"
            self.debug_log(f"ERROR deleting focus time: {tb}")
            import sys
            print(f"\n[ERROR] Failed to delete focus time:\n{tb}", file=sys.stderr, flush=True)

    async def handle_rsvp(self, response: str):
        """Handle RSVP response (accept/tentative/decline)"""
        if not self.events or self.current_row >= len(self.events):
            return

        event = self.events[self.current_row]

        try:
            # Call MCP edit_event tool
            # First, need to update attendee response status
            attendees = []
            for attendee in event.attendees:
                attendee_data = {"email": attendee.get('email')}
                if attendee.get('self', False):
                    attendee_data["response_status"] = response
                else:
                    attendee_data["response_status"] = attendee.get('responseStatus', 'needsAction')
                attendees.append(attendee_data)

            await self.mcp_client.call_tool(
                "edit_event",
                {
                    "event_id": event.id,
                    "attendees": attendees,
                    "send_notifications": False
                }
            )

            event.response_status = response
            self.status_message = f"Event {response}!"

        except Exception as e:
            self.status_message = f"Error: {str(e)}"

    async def create_focus_time(self):
        """Create a focus time block from the selected available slot, or all core hours slots if not on available"""
        try:
            self.debug_log("=== create_focus_time() called ===")

            # Check if we have events
            if not self.events:
                self.status_message = "No events loaded"
                self.debug_log("No events loaded")
                return

            # Check if current selection is an available slot
            current_event = None
            if self.current_row < len(self.events):
                current_event = self.events[self.current_row]
                self.debug_log(f"Selected event: is_available={current_event.is_available}, summary='{current_event.summary}'")

            # If current selection is available, create focus time for just that slot
            if current_event and current_event.is_available:
                self.debug_log("Creating focus time for single available slot")
                await self._create_single_focus_time(current_event)
            else:
                # Create focus time for ALL available slots during core hours
                self.debug_log("Creating focus time for all available core hours slots")
                await self._create_bulk_focus_time()

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.debug_log(f"ERROR creating focus time: {tb}")
            # Always print errors to stderr for visibility
            import sys
            print(f"\n[ERROR] Failed to create focus time:\n{tb}", file=sys.stderr, flush=True)
            # Re-raise so run_with_spinner can handle the error message
            raise

    async def _create_single_focus_time(self, event):
        """Create focus time for a single available slot"""
        # Use the available slot's time range
        start_time = event.start_time
        end_time = event.end_time
        self.debug_log(f"Time range: {start_time} to {end_time}")

        if not start_time or not end_time:
            self.status_message = "Invalid time range for available slot"
            self.debug_log("Invalid time range: start_time or end_time is None")
            return

        # Calculate duration in minutes
        duration_minutes = (end_time - start_time).total_seconds() / 60
        self.debug_log(f"Duration: {duration_minutes} minutes")

        # Set title based on duration
        if duration_minutes <= 40:
            title = "Paperwork - Focus time"
        else:
            title = "Development - Focus time"
        self.debug_log(f"Title: '{title}'")

        # Format times with timezone (use isoformat to preserve timezone offset)
        start_str = start_time.isoformat()
        end_str = end_time.isoformat()

        # Extract timezone from the start_time object
        event_timezone = str(start_time.tzinfo) if start_time.tzinfo else self.timezone
        self.debug_log(f"Formatted times: start={start_str}, end={end_str}, event_timezone={event_timezone}")

        # Prepare arguments
        args = {
            "summary": title,
            "start_time": start_str,
            "end_time": end_str,
            "eventType": "focusTime",
            "timezone": self.timezone,
            "colorId": "5",  # Yellow in Google Calendar
            "focusTimeProperties": {
                "autoDeclineMode": "declineOnlyNewConflictingInvitations",
                "chatStatus": "doNotDisturb"
            },
            "send_notifications": False
        }
        self.debug_log(f"MCP call arguments: {args}")

        # Call MCP create_event tool
        self.debug_log("Calling MCP create_event tool...")
        result = await self.mcp_client.call_tool("create_event", args)
        self.debug_log(f"MCP result: {result}")

        # Check if result contains an error
        if isinstance(result, str) and ("Error:" in result or "error" in result.lower()):
            self.debug_log(f"MCP returned error: {result}")
            self.status_message = f"❌ Failed: {result[:100]}"
            return

        self.debug_log("Focus time created successfully, refreshing events...")
        await self.fetch_events(self.time_filter, self.time_min, self.time_max)
        self.debug_log("Events refreshed")
        self.status_message = f"✅ Created {int(duration_minutes)}min {title}"

    async def _create_bulk_focus_time(self):
        """Create focus time for all available slots during core hours, including gaps before/after events"""
        # Find all available slots during core hours (9am-5pm)
        core_available_slots = []

        for event in self.events:
            if not event.is_available:
                continue

            if not event.start_time or not event.end_time:
                continue

            # Check if slot is during core hours
            start_hour = event.start_time.hour
            end_hour = event.end_time.hour

            # Slot must be fully within core hours (9am-5pm)
            if start_hour >= self.core_start_hour and end_hour <= self.core_end_hour:
                core_available_slots.append(event)
                self.debug_log(f"Found core hours slot: {event.start_time} to {event.end_time}")

        # Also check for gaps at the beginning and end of the work day
        # Get all timed events (not just available slots) for today
        timed_events = [e for e in self.events if not e.is_all_day and e.start_time and not e.is_available]

        if timed_events:
            # Sort by start time
            timed_events.sort(key=lambda e: e.start_time)

            # Get the date we're working with (use first timed event's date)
            work_date = timed_events[0].start_time.date()
            core_start = datetime.combine(work_date, datetime.min.time().replace(hour=self.core_start_hour))
            core_start = core_start.replace(tzinfo=timed_events[0].start_time.tzinfo)
            core_end = datetime.combine(work_date, datetime.min.time().replace(hour=self.core_end_hour))
            core_end = core_end.replace(tzinfo=timed_events[0].start_time.tzinfo)

            # Check for gap before first event (9am to first event start)
            first_event = timed_events[0]
            if first_event.start_time > core_start:
                gap_minutes = (first_event.start_time - core_start).total_seconds() / 60
                if gap_minutes >= 30:
                    self.debug_log(f"Found gap before first event: {core_start} to {first_event.start_time} ({gap_minutes} min)")
                    # Create a pseudo-available slot for this gap
                    gap_slot = CalendarEvent({
                        'start': {'dateTime': core_start.isoformat()},
                        'end': {'dateTime': first_event.start_time.isoformat()}
                    }, is_available=True)
                    core_available_slots.append(gap_slot)

            # Check for gap after last event (last event end to 5pm)
            last_event = timed_events[-1]
            if last_event.end_time and last_event.end_time < core_end:
                gap_minutes = (core_end - last_event.end_time).total_seconds() / 60
                if gap_minutes >= 30:
                    self.debug_log(f"Found gap after last event: {last_event.end_time} to {core_end} ({gap_minutes} min)")
                    # Create a pseudo-available slot for this gap
                    gap_slot = CalendarEvent({
                        'start': {'dateTime': last_event.end_time.isoformat()},
                        'end': {'dateTime': core_end.isoformat()}
                    }, is_available=True)
                    core_available_slots.append(gap_slot)

        if not core_available_slots:
            self.status_message = "No available slots during core hours (9am-5pm)"
            self.debug_log("No available slots found during core hours")
            return

        self.debug_log(f"Creating focus time for {len(core_available_slots)} available slots")

        # Create focus time for each slot
        created_count = 0
        failed_count = 0

        for slot in core_available_slots:
            duration_minutes = (slot.end_time - slot.start_time).total_seconds() / 60

            # Set title based on duration
            if duration_minutes <= 40:
                title = "Paperwork - Focus time"
            else:
                title = "Development - Focus time"

            # Prepare arguments
            args = {
                "summary": title,
                "start_time": slot.start_time.isoformat(),
                "end_time": slot.end_time.isoformat(),
                "eventType": "focusTime",
                "timezone": self.timezone,
                "colorId": "5",  # Yellow in Google Calendar
                "focusTimeProperties": {
                    "autoDeclineMode": "declineOnlyNewConflictingInvitations",
                    "chatStatus": "doNotDisturb"
                },
                "send_notifications": False
            }

            # Call MCP create_event tool
            try:
                result = await self.mcp_client.call_tool("create_event", args)

                # Check if result contains an error
                if isinstance(result, str) and ("Error:" in result or "error" in result.lower()):
                    self.debug_log(f"Failed to create focus time for slot {slot.start_time}: {result}")
                    failed_count += 1
                else:
                    self.debug_log(f"Created focus time for slot {slot.start_time}")
                    created_count += 1
            except Exception as e:
                self.debug_log(f"Exception creating focus time for slot {slot.start_time}: {e}")
                failed_count += 1

        # Refresh events to show new focus times
        await self.fetch_events(self.time_filter, self.time_min, self.time_max)

        # Set status message
        if created_count > 0 and failed_count == 0:
            self.status_message = f"✅ Created {created_count} focus time blocks"
        elif created_count > 0 and failed_count > 0:
            self.status_message = f"⚠️ Created {created_count}, failed {failed_count}"
        else:
            self.status_message = f"❌ Failed to create focus times"

    def navigate_time_period(self, direction: int):
        """Navigate to previous (-1) or next (1) time period

        Args:
            direction: -1 for previous, 1 for next
        """
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
                # Find last week's Monday
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
                # Find next week's Monday
                days_until_monday = (7 - now.weekday()) % 7
                if days_until_monday == 0:
                    days_until_monday = 7
                next_monday = now + timedelta(days=days_until_monday)
                # Add another week
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

    def start_recommendations_analysis(self):
        """Start background task to get recommendations"""
        # Cancel any existing task before starting a new one
        # This ensures we always analyze the CURRENT view, not a previous one
        if self.recommendations_task and not self.recommendations_task.done():
            self.debug_log("Cancelling previous recommendations task")
            self.recommendations_task.cancel()

        # Start new task
        self.recommendations_task = asyncio.create_task(self.get_recommendations())
        self.start_loading("Analyzing calendar...")
        # Clear previous recommendations while new analysis runs
        self.show_recommendations = False
        self.recommendations_list = []

    async def get_recommendations(self):
        """Get calendar recommendations from Claude Code via /recommend slash command"""
        try:
            self.debug_log("=== get_recommendations() called ===")
            self.debug_log(f"CWD: /home/jpacker/workspace_git/gcal-mcp-server")

            # Serialize current events to JSON (exclude available slots)
            events_data = []
            overlap_count = 0
            for event in self.events:
                if event.is_available:
                    continue  # Skip available slots

                # Build event data matching Google Calendar API format
                event_dict = {
                    'id': event.id,
                    'summary': event.summary,
                    'start': event.start,
                    'end': event.end,
                    'status': event.status,
                    'eventType': event.event_type,
                    'attendees': event.attendees,
                    'has_overlap': event.has_overlap,
                    'overlapping_event_ids': event.overlapping_event_ids
                }
                events_data.append(event_dict)

                # Count overlaps for debugging
                if event.has_overlap:
                    overlap_count += 1
                    self.debug_log(f"  Overlap: {event.summary} conflicts with {event.overlapping_event_ids}")

            # Write events to a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump({'events': events_data, 'count': len(events_data)}, f, indent=2)
                events_file = f.name

            self.debug_log(f"Serialized {len(events_data)} events to {events_file}")
            self.debug_log(f"Found {overlap_count} events with overlaps")
            self.debug_log(f"Temp file path: {events_file} (will be kept for inspection)")

            # Pass the file path to Claude
            prompt_arg = f"Analyze the events in {events_file} and provide recommendations"
            self.debug_log(f"Command: ['claude', '/recommend', '{prompt_arg}']")

            # Use asyncio subprocess to avoid blocking the event loop
            # This allows the spinner to keep rotating while Claude thinks
            self.debug_log("Starting subprocess...")
            process = await asyncio.create_subprocess_exec(
                'claude', '/recommend', prompt_arg,
                cwd='/home/jpacker/workspace_git/gcal-mcp-server',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=120
                )
            except asyncio.TimeoutError:
                self.debug_log("Recommendation request timed out, killing process")
                process.kill()
                await process.wait()
                self.status_message = "❌ Recommendation request timed out"
                return None
            except asyncio.CancelledError:
                # Task was cancelled (user navigated away)
                self.debug_log("Recommendation task cancelled, killing subprocess")
                process.kill()
                await process.wait()
                raise  # Re-raise to propagate cancellation

            stdout_text = stdout.decode('utf-8') if stdout else ""
            stderr_text = stderr.decode('utf-8') if stderr else ""

            self.debug_log(f"Subprocess completed with return code: {process.returncode}")
            self.debug_log(f"stdout length: {len(stdout_text)} chars")
            self.debug_log(f"stderr length: {len(stderr_text)} chars")

            if stderr_text:
                self.debug_log(f"stderr content: {stderr_text[:500]}")

            if process.returncode != 0:
                self.debug_log(f"Claude command failed: {stderr_text}")
                self.status_message = f"❌ Failed to get recommendations: {stderr_text[:100]}"
                return None

            self.debug_log(f"Got recommendations ({len(stdout_text)} chars)")
            self.debug_log(f"First 500 chars: {stdout_text[:500]}")
            self.debug_log(f"Full output: {stdout_text}")

            # Clean up temp file (DISABLED for debugging)
            # try:
            #     import os
            #     os.unlink(events_file)
            #     self.debug_log(f"Cleaned up temp file: {events_file}")
            # except:
            #     pass
            self.debug_log(f"Keeping temp file for inspection: {events_file}")

            return stdout_text

        except asyncio.CancelledError:
            # Task was cancelled - re-raise without logging as error
            self.debug_log("get_recommendations cancelled")
            raise
        except FileNotFoundError:
            self.status_message = "❌ Claude CLI not found. Install claude-code CLI tool."
            return None
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.debug_log(f"ERROR getting recommendations: {tb}")
            self.status_message = f"❌ Error: {str(e)}"
            return None

    def parse_recommendations(self, text: str) -> List[Dict]:
        """Parse recommendations text into structured list

        Extracts recommendations and formats each to max 2 lines.
        """
        recommendations = []

        self.debug_log(f"=== parse_recommendations() called ===")
        self.debug_log(f"Text length: {len(text)} chars")

        # Split by lines
        lines = text.split('\n')
        self.debug_log(f"Total lines: {len(lines)}")

        for line in lines:
            # Look for numbered recommendations (1., 2., etc.)
            stripped = line.strip()
            if not stripped:
                continue

            # Match patterns like "1. DECLINE:", "2. RESCHEDULE:", etc.
            if stripped and stripped[0].isdigit() and '. ' in stripped[:5]:
                # Extract the first line (action line)
                # Format: "1. DECLINE: Event Title (event_id)"
                action_line = stripped
                self.debug_log(f"Found recommendation: {action_line[:50]}...")

                # Limit to reasonable width (about 100 chars for first line)
                if len(action_line) > 100:
                    action_line = action_line[:97] + "..."

                recommendations.append({
                    'line1': action_line,
                    'line2': ''  # Will be populated if there's a reason line
                })
            # Look for "Reason:" or "Time:" lines that belong to the previous recommendation
            elif stripped.startswith(('Reason:', 'Time:', 'From:', 'To:')) and recommendations:
                # Add as second line to the most recent recommendation
                reason_line = '  ' + stripped  # Indent slightly

                # Limit to reasonable width
                if len(reason_line) > 100:
                    reason_line = reason_line[:97] + "..."

                # Only keep the first reason/time line (max 2 lines total)
                if not recommendations[-1]['line2']:
                    recommendations[-1]['line2'] = reason_line

        self.debug_log(f"Parsed {len(recommendations)} recommendations")
        return recommendations

    async def run(self):
        """Main event loop"""
        # Initial fetch
        success = await self.fetch_events(self.time_filter, self.time_min, self.time_max)
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

            # Check if recommendations task completed (runs every loop iteration)
            # Set flag to redraw on next iteration instead of drawing immediately
            recommendations_completed = False
            if self.recommendations_task and self.recommendations_task.done():
                try:
                    recommendations = self.recommendations_task.result()
                    if recommendations:
                        self.debug_log(f"Got recommendations text: {len(recommendations)} chars")
                        self.recommendations_text = recommendations
                        self.recommendations_list = self.parse_recommendations(recommendations)
                        self.debug_log(f"Parsed into {len(self.recommendations_list)} items")

                        # Show recommendations section even if list is empty (will show "no recommendations" message)
                        self.show_recommendations = True

                        if self.recommendations_list:
                            self.stop_loading(f"✅ {len(self.recommendations_list)} recommendations")
                        else:
                            self.stop_loading("✅ No recommendations needed")
                    else:
                        self.stop_loading("")  # Error message already set by get_recommendations
                    self.recommendations_task = None
                    recommendations_completed = True
                except asyncio.CancelledError:
                    # Task was cancelled (user navigated to different period)
                    self.debug_log("Recommendations task was cancelled")
                    self.recommendations_task = None
                    self.stop_loading("")
                except Exception as e:
                    self.status_message = f"❌ Error: {str(e)}"
                    self.stop_loading("")
                    self.recommendations_task = None
                    recommendations_completed = True

            # Skip key processing if no key was pressed, but still redraw if recommendations completed
            if key == -1:
                # Redraw if recommendations just completed
                if recommendations_completed:
                    self.draw()
                continue

            # Track if we need to redraw
            needs_redraw = True

            # Also redraw if recommendations completed
            if recommendations_completed:
                needs_redraw = True

            if key == ord('q'):
                break
            elif key == ord('r'):
                await self.run_with_spinner(
                    self.fetch_events(self.time_filter, self.time_min, self.time_max),
                    "Refreshing...",
                    "✅ Refreshed!"
                )
                # Ensure cursor is still within bounds after refresh
                if self.current_row >= len(self.events):
                    self.current_row = max(0, len(self.events) - 1)
                # Redraw full screen to show new events
                needs_redraw = True
            elif key in [curses.KEY_UP, curses.KEY_DOWN]:
                # Don't navigate if attendee details are showing
                if not self.show_attendee_details:
                    self.handle_navigation(key)
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                # Enter key - toggle attendee details
                if self.show_attendee_details:
                    # Close the overlay
                    self.show_attendee_details = False
                    self.attendee_details_event = None
                else:
                    # Show attendee details for current event
                    if self.events and self.current_row < len(self.events):
                        event = self.events[self.current_row]
                        # Only show if event has attendees and is not an available slot
                        if not event.is_available and event.attendees:
                            self.show_attendee_details = True
                            self.attendee_details_event = event
                        else:
                            self.status_message = "No attendees for this event"
                            needs_redraw = False
            elif key == 27:  # ESC key
                # Close attendee details if showing
                if self.show_attendee_details:
                    self.show_attendee_details = False
                    self.attendee_details_event = None
                else:
                    needs_redraw = False
            elif key == curses.KEY_LEFT:
                # Navigate to previous time period
                self.navigate_time_period(-1)
                await self.run_with_spinner(
                    self.fetch_events(self.time_filter, self.time_min, self.time_max),
                    "Loading previous period...",
                    "✅ Loaded!"
                )
                self.current_row = 0
                self.scroll_offset = 0
                # Redraw full screen to show new events
                needs_redraw = True
            elif key == curses.KEY_RIGHT:
                # Navigate to next time period
                self.navigate_time_period(1)
                await self.run_with_spinner(
                    self.fetch_events(self.time_filter, self.time_min, self.time_max),
                    "Loading next period...",
                    "✅ Loaded!"
                )
                self.current_row = 0
                self.scroll_offset = 0
                # Redraw full screen to show new events
                needs_redraw = True
            elif key == ord('a'):
                await self.handle_rsvp('accepted')
            elif key == ord('t'):
                await self.handle_rsvp('tentative')
            elif key == ord('d'):
                # Check if current event is a focus time - if so, delete it
                if self.events and self.current_row < len(self.events):
                    event = self.events[self.current_row]
                    if event.event_type == 'focusTime':
                        await self.run_with_spinner(
                            self.delete_focus_time(),
                            "Deleting focus time...",
                            None  # delete_focus_time sets its own success message
                        )
                        # Redraw full screen to show deletion
                        needs_redraw = True
                    else:
                        await self.handle_rsvp('declined')
                else:
                    await self.handle_rsvp('declined')
            elif key == ord('f'):
                await self.run_with_spinner(
                    self.create_focus_time(),
                    "Creating focus time..."
                    # success_msg=None (default) - create_focus_time sets its own success message
                )
                # Redraw full screen to show new focus time event
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
