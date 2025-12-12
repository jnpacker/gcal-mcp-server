# Interactive Calendar TUI

A text-based interactive calendar application that uses the Google Calendar MCP Server to fetch and manage your calendar events.

## Features

- **Interactive Table View**: View all your calendar events in a clean, terminal-based table
- **Flexible Display Modes**: Switch between single day and two-day views with mini calendar navigation
- **Keyboard Navigation**: Navigate through events and days using arrow keys
- **RSVP Management**: Quickly accept, decline, or mark events as tentative
- **Focus Time Creation**: Create focus time blocks with customizable duration on available time slots
- **Overlap Detection**: Visually highlights overlapping events with color coding and event IDs
- **Smart Refresh**: Reload current period (1 or 2 days) from Google Calendar on demand
- **AI-Powered Recommendations**: Automatic background analysis with conflict resolution and optimization suggestions
- **Available Time Slots**: Visual indicators (green/grey boxes) showing free time during your workday

## Installation

1. Make sure the Google Calendar MCP Server is built:
   ```bash
   make build
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Testing

Run the comprehensive test suite to validate all calendar TUI features:

```bash
cd calender
python3 test_calendar_tui.py
```

The test suite validates:
- ✅ MCP server connection
- ✅ Calendar event features (RSVP status, event types)
- ✅ Location event filtering (one per day)
- ✅ Column alignment (with and without clock emoji)
- ✅ Cursor positioning (auto-position at current event)
- ✅ Meeting link display (short g.co/meet/ format)
- ✅ Available time slot rendering (green/grey boxes)

All tests should pass before using the calendar TUI in production.

## Usage

Run the calendar TUI:
```bash
./calendar_tui.py
```

### Command Line Options

- `--timezone`: Set your timezone (default: `America/New_York`)
  ```bash
  ./calendar_tui.py --timezone America/Los_Angeles
  ```

- `--filter`: Choose time filter (default: `today`)
  ```bash
  ./calendar_tui.py --filter this_week
  ```
  Options: `today`, `this_week`, `next_week`

- `--server-path`: Specify custom path to gcal-mcp-server binary
  ```bash
  ./calendar_tui.py --server-path /path/to/gcal-mcp-server
  ```

## Keyboard Controls

### Normal Mode

| Key | Action |
|-----|--------|
| `↑` / `↓` | Navigate up/down through events |
| `←` / `→` | Navigate to previous/next weekday |
| `1` | Switch to single day view (shows current day only) |
| `2` | Switch to two-day view (shows current day + tomorrow) |
| `Enter` | Show attendee details (if event has attendees) |
| `a` | Accept selected event |
| `t` | Mark event as tentative |
| `d` | Decline selected event (or delete focus time) |
| `-` | Toggle showing/hiding declined events |
| `f` | Create focus time blocks on available slots |
| `r` | Show AI-powered recommendations for current period |
| `R` | **Refresh current period** - Reload events from Google Calendar for the displayed day(s) |
| `q` | Quit application |

### Display Modes

The calendar supports two view modes that affect what events are displayed:

- **Single Day (1)**: Shows only the current viewing day
- **Two Day (2)**: Shows current viewing day plus the next day

The display mode is shown in the header and affects:
- Which days are highlighted in the mini calendar (white background)
- The date range shown in the header
- What gets refreshed when you press `R`

### Refresh vs Recommendations

- **Refresh (`R`)**: Reloads event data from Google Calendar for the current period
  - In single day mode: refreshes current day only
  - In two-day mode: refreshes current day + next day
  - Shows spinner with "Refreshing today..." or "Refreshing today + tomorrow..."
  - Use this to sync latest changes from Google Calendar

- **Recommendations (`r`)**: Shows AI-powered suggestions for your calendar
  - Analyzes conflicts, back-to-back meetings, and scheduling patterns
  - Generates actionable recommendations
  - Cached per view - reuse if you return to the same period

## Attendee Details

Press `Enter` on any event with attendees to view detailed RSVP status:

### Interactive Attendee Overlay
- **Visual Status Bar**: Color-coded bar chart showing acceptance breakdown
  - 🟩 Green: Accepted
  - 🟥 Red: Declined
  - 🟨 Yellow: Tentative
  - ⬜ Grey: No response
- **Summary Stats**: Total count with breakdown by status (✅/❌/⏳/❓)
- **Grouped Attendee List**: Attendees organized by their response status
  - Shows "You" indicator for your own entry
  - Displays name for each attendee
  - Color-coded by status
- **Easy Close**: Press `Enter` or `ESC` to close the overlay

### What You'll See
```
╔════════════════════════════════════════════════════════╗
║        Attendees for Team Sync Meeting                 ║
║                                                         ║
║  Total: 12 | ✅ 8 | ❌ 2 | ⏳ 1 | ❓ 1                  ║
║   ████████████████████░░░░                             ║
║─────────────────────────────────────────────────────────║
║  ✅ Accepted (8)                                        ║
║    • Alice Johnson                                      ║
║    • Bob Smith (You)                                    ║
║    • ...                                                ║
║  ⏳ Tentative (1)                                       ║
║    • Charlie Davis                                      ║
║  ❓ No Response (1)                                     ║
║    • Diana Prince                                       ║
║  ❌ Declined (2)                                        ║
║    • Eve Anderson                                       ║
║    • Frank Miller                                       ║
╚════════════════════════════════════════════════════════╝
```

## AI-Powered Recommendations

Calendar recommendations are automatically generated in the background whenever you refresh or navigate to a different time period. The system analyzes:

### Conflict Resolution
- **Overlapping meetings**: Identifies which events conflict and suggests which to decline based on:
  - Meeting size (<4 participants = easier to reschedule)
  - Historical patterns (if you've declined similar meetings before)
  - Attendee acceptance rates

### Back-to-Back Meeting Optimization
- Detects meeting blocks exceeding 2 hours
- Suggests breaks to prevent burnout
- Recommends which meetings could be shortened or rescheduled

### Historical Analysis
- Reviews last 2 weeks of calendar data
- Identifies recurring meetings you frequently decline
- Suggests permanent changes for better scheduling patterns

### Smart Prioritization
The recommendation engine prioritizes:
1. **Critical overlaps** - where you physically can't attend both
2. **Energy preservation** - breaking up long meeting blocks (>2hr)
3. **Focus time creation** - finding opportunities for deep work (9am-12pm preferred)
4. **Meeting significance** - respecting meetings where you're a key participant (>4 attendees or organizer)

### How It Works
1. Recommendations are automatically fetched in the background when you:
   - Start the application
   - Manually refresh the calendar (press `R`)
   - Navigate to a different day or period (arrow keys, `1`, `2`)
   - After RSVP changes, focus time creation/deletion
2. While Claude analyzes your calendar, you can continue working:
   - Navigate through events
   - Accept/decline meetings
   - Create focus time blocks
   - Change display modes
3. When analysis completes, a 💡 lightbulb indicator appears in the footer
4. Press `r` to view recommendations in a modal overlay
5. Recommendations are cached per view - if you return to the same day/mode, press `r` to see them instantly

**Note**: The recommendations are for review only. You can use the suggested actions (decline specific meetings, create focus time, etc.) to manually optimize your schedule.

## How Claude Code Integration Works

The calendar TUI integrates with Claude Code CLI to provide AI-powered calendar analysis. Here's how the interaction happens:

### Technical Architecture

```
Calendar TUI (Python/Curses)
    │
    ├─── On refresh/navigation
    │
    ├──> Serialize current events to JSON temp file
    │
    └──> subprocess(['claude', '/recommend', 'Analyze /tmp/events.json'])
         │
         │ Claude Code CLI executes:
         │   1. Loads .claude/commands/recommend.md
         │   2. Reads the event data from the provided JSON file
         │   3. Analyzes with Claude AI (Haiku 4.5 model)
         │   4. Generates structured recommendations
         │   5. NO MCP calls needed - uses provided data
         │
         └──> Returns text output to TUI
              │
              ├──> TUI parses recommendations
              │
              └──> TUI displays inline below events
```

### The Process Step-by-Step

1. **User presses `l`**: The TUI captures this key press in the event loop

2. **Subprocess call**: The TUI executes this command:
   ```python
   subprocess.run(
       ['claude', '/recommend'],
       cwd='/home/jpacker/workspace_git/gcal-mcp-server',
       capture_output=True,
       text=True,
       timeout=30
   )
   ```

3. **Claude Code CLI runs**:
   - Looks for `.claude/commands/recommend.md` slash command
   - Reads the prompt template with instructions
   - Executes the prompt using the Claude AI model specified in the frontmatter (`claude-haiku-4-5`)

4. **MCP Server interaction**:
   - Claude Code has access to the `gcal-mcp-server` MCP tools
   - Uses `list_events` to fetch today's events with overlap detection
   - Fetches last 2 weeks of events to analyze historical patterns
   - All calendar data comes through the MCP protocol

5. **AI Analysis**: Claude AI processes:
   - Event conflicts and overlaps
   - Back-to-back meeting patterns
   - Meeting sizes (participant counts)
   - Historical decline patterns
   - Available time gaps

6. **Output returned**:
   - Claude Code's `stdout` contains the formatted recommendations
   - TUI captures this text and displays it in the overlay

### Key Files Involved

- **`.claude/commands/recommend.md`**: Slash command definition with prompt
- **`.claude/settings.local.json`**: Permissions for MCP tools and slash commands
- **`calendar_tui.py:get_recommendations()`**: Python method that calls Claude CLI
- **`gcal-mcp-server`**: MCP server providing calendar data access

### Why This Design?

This architecture allows:
- **Separation of concerns**: TUI handles display, Claude Code handles AI analysis
- **Flexibility**: Can modify prompts in `.claude/commands/recommend.md` without changing Python code
- **MCP integration**: Leverages existing Google Calendar MCP server
- **Powerful AI**: Uses Claude 3.5 Haiku's reasoning capabilities
- **No API keys needed in TUI**: Claude Code handles authentication

## Visual Indicators

### Mini Calendar Header
The top of the screen shows a compact 3-week calendar view:
- **Green background (🟩)**: Today's date
- **White background (⬜)**: Currently viewing day(s)
  - Single day mode: highlights one day
  - Two-day mode: highlights current day and next day
- **White text**: Days with loaded calendar data
- **Dim text**: Days not yet loaded
- **Brackets `[...]`**: Previous and next weeks (navigate with arrow keys)

Example:
```
               📅 Interactive Calendar
       Monday, December 09 - Tuesday, December 10, 2025
[Mo Tu We Th Fr] Mo Tu We Th Fr [Mo Tu We Th Fr]
                 ^^    ^^
           (highlighted = viewing these two days)
```

### Current Time Indicator
- `🕐` - Clock emoji appears before the currently active event title
- On startup, the cursor automatically positions at the current or next event
- On refresh (press `R`), the cursor stays in place

### RSVP Status
- `✅` - Accepted
- `❌` - Declined
- `⏳` - Tentative
- `❓` - No response yet
- `📋` - Task
- `🎧` - Focus time
- `🏠` - Working from home
- `🏢` - Working from office
- `📍` - Custom location

### Available Time Slots
Available time slots are automatically detected during your workday (9am-5pm by default):
- **🟩 Green boxes**: Available time during core hours (9am-5pm)
- **⬛ Grey boxes**: Available time outside core hours
- Each box represents 30 minutes
- Shown as "🟩🟩🟩 Available" in the event list
- Press `f` on an available slot to create focus time

Available slots appear:
- Between meetings (gaps of 30+ minutes)
- Before first meeting of the day
- After last meeting of the day (if before 5pm)
- Only on days with loaded calendar data

### Meeting Links
- Google Meet links display as short meeting IDs (e.g., `kmv-cnxe-buy`)
- This prevents truncation and keeps the display clean
- The full URL is preserved internally
- Meeting IDs are shown in blue for easy identification

### Color Coding
- **White background** - Currently selected event
- **Green text** - Accepted events
- **Red text** - Declined events
- **Yellow text** - Tentative events and Focus time blocks
- **Orange text** - Task events
- **Cyan text** - Events with overlaps

### Overlap Detection
When events overlap, you'll see:
- `⚠️ OVERLAP` indicator in the overlap column
- Event IDs of overlapping events shown in brackets on the right (e.g., `[evt1,evt2,evt3]`)
- Color-coded highlighting to draw attention

## How Overlap Detection Works

The application uses a novel approach to visualize overlapping events:

1. **Automatic Detection**: The MCP server detects overlaps when fetching events
2. **Visual Warning**: Overlapping events show a warning icon in the table
3. **ID Cross-Reference**: Each overlapping event displays the IDs of events it conflicts with
4. **Color Highlighting**: Overlapping events are highlighted in cyan for easy identification

This makes it easy to:
- Spot scheduling conflicts at a glance
- Identify which specific events are conflicting
- Decide which events to decline or adjust

## Focus Time Blocks

Focus time is a special event type that:
- Automatically declines new conflicting invitations
- Sets your chat status to "Do Not Disturb"
- Helps you block out time for deep work
- Identified by 🎧 headphone emoji

### Creating Focus Time
1. Navigate to an available time slot (shown with 🟩 green boxes or ⬛ grey boxes)
2. Press `f` to instantly create focus time for that slot
3. The focus time event appears immediately while saving to Google Calendar in the background

**Duration Logic:**
- Slots ≤40 minutes: Creates "Paperwork - Focus time"
- Slots >40 minutes: Creates "Development - Focus time"

### Deleting Focus Time
1. Navigate to a focus time event (marked with 🎧)
2. Press `d` to delete it
3. The event is removed immediately while deleting from Google Calendar in the background

**Note:** Only available time slots can be converted to focus time. Declined events are treated as free time and don't block available slots.

## Requirements

- Python 3.8+
- MCP Python SDK (`mcp` package)
- Google Calendar MCP Server (included in this repository)
- Valid Google Calendar credentials (`credentials.json` and `token.json`)

## Troubleshooting

### "Failed to fetch events"
- Ensure the gcal-mcp-server binary is built: `make build`
- Check that credentials.json and token.json exist in the repository root
- Verify your timezone is correctly set

### "MCP SDK not installed"
- Install the required package: `pip install mcp`

### Terminal display issues
- Ensure your terminal supports color (most modern terminals do)
- Try resizing your terminal if the table doesn't fit

## Architecture

The application consists of three main components:

1. **CalendarEvent**: Data model for calendar events with overlap detection
2. **MCPClient**: Async client for communicating with the MCP server
3. **CalendarTUI**: Curses-based terminal interface with keyboard handling

The app uses:
- Python's `curses` library for terminal UI
- `asyncio` for async/await pattern
- MCP Python SDK for server communication
- JSON-RPC over stdio for MCP protocol

## License

Copyright 2024 Red Hat, Inc.

Licensed under the Apache License, Version 2.0
