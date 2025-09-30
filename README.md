# Google Calendar MCP Server

A comprehensive Model Context Protocol (MCP) server that provides intelligent Google Calendar integration for AI assistants. This server enables advanced calendar management, smart event scheduling, attendee coordination, availability checking, RSVP management, and day organization through a standardized interface.

## 🚀 Latest Updates

- **Advanced RSVP Management**: Accept, decline, or mark meetings as tentative using simple commands
- **Smart Day Organization**: Automatically reorganize your calendar for optimal productivity
- **Timeline Visualization**: Gantt chart-style timeline view for better schedule visualization  
- **Intelligent Conflict Detection**: Automatic overlap detection with visual indicators
- **Enhanced AI Integration**: Comprehensive system prompts for Claude, Gemini-CLI, and Cursor
- **Attendee Availability Validation**: Mandatory free/busy checking before event creation
- **Meeting Filtering**: Smart filtering for "remaining today" events and time-based queries

## Features

### 🗓️ Event Management
- **Create Events**: Full-featured event creation with all Google Calendar options
- **Edit Events**: Update any aspect of existing events with true PATCH semantics
- **Delete Events**: Remove events with proper attendee notifications
- **Recurring Events**: Support for complex recurrence patterns
- **RSVP Management**: Accept, decline, or mark meetings as tentative using meeting numbers
- **Event Filtering**: Smart filtering for "remaining today" and time-based queries

### 👥 Attendee Management
- **Attendee Search**: Find and validate attendee email addresses
- **Free/Busy Checking**: Mandatory availability checking across multiple calendars
- **Smart Scheduling**: Automatic conflict detection and resolution
- **Availability Validation**: Pre-event creation availability verification for all attendees

### 🔧 Advanced Features
- **Google Meet Integration**: Automatic conference link generation
- **Custom Reminders**: Email and popup notifications
- **Timezone Support**: Handle multi-timezone meetings
- **Guest Permissions**: Control attendee capabilities
- **Privacy Controls**: Manage event visibility
- **Timeline Visualization**: Gantt chart-style calendar views
- **Day Organization**: Intelligent calendar reorganization for productivity
- **Conflict Detection**: Visual overlap indicators and automatic resolution

## Quick Start

### Prerequisites

- Go 1.21 or later
- Google Cloud Project with Calendar API enabled
- Google OAuth 2.0 credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd gcal-mcp-server
   ```

2. **Install dependencies**
   ```bash
   go mod tidy
   ```

3. **Build the server**
   ```bash
   go build -o gcal-mcp-server cmd/server/main.go
   ```

### Google Calendar API Setup

#### Step 1: Create Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Calendar API:
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Calendar API"
   - Click "Enable"

#### Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Set application type to "Desktop application"
4. Name your OAuth client (e.g., "Calendar MCP Server")
5. Download the credentials JSON file

#### Step 3: Configure Credentials

**Option 1: Repository Root (Recommended)**
Place your credentials file in the repository root directory:
```bash
cp path/to/downloaded/credentials.json /path/to/gcal-mcp-server/credentials.json
```

**Option 2: User Configuration Directory**
```bash
mkdir -p ~/.config/gcal-mcp-server
cp path/to/downloaded/credentials.json ~/.config/gcal-mcp-server/credentials.json
```

The server will automatically detect the repository root and use credentials from there, making it work regardless of where you launch the server from.

#### Step 4: Initial Authentication

1. Run the server for the first time:
   ```bash
   ./gcal-mcp-server
   ```

2. The server will prompt you to visit a URL for authentication
3. Complete the OAuth flow in your browser
4. The server will save your token for future use

## Configuration

### Credentials Location

The server automatically detects the repository root by looking for `go.mod` or `.git` files and uses credentials from there. This ensures the server works regardless of where you launch it from.

**Search order:**
1. Repository root: `<repo-root>/credentials.json` (automatically detected)
2. Fallback: Current working directory `./credentials.json`

### Token Storage

Authentication tokens are stored alongside credentials:
- Repository root: `<repo-root>/token.json` (automatically detected)
- Fallback: Current working directory `./token.json`

This approach ensures consistent credential access regardless of launch location.

## 🤖 AI Integration

This MCP server is designed to work seamlessly with multiple AI assistants. Each platform has specific setup instructions and capabilities.

### 📋 System Prompt Integration

The repository includes a comprehensive system prompt (`gcal-assistant-prompt.md`) that provides:
- Detailed behavioral guidelines for calendar management
- Advanced workflow instructions for RSVP management and day organization
- Response formatting templates for consistent user experience
- Error handling and validation procedures

### 🔵 Claude Code Integration

#### Configuration

Add the following to your Claude Code or Gemini CLI configuration file:

**macOS**: `.mcp.json`

```json
{
  "mcpServers": {
    "gcal-mcp-server": {
      "command": "/path/to/gcal-mcp-server",
      "args": [],
      "env": {}
    }
  }
}
```

#### Using the System Prompt with Claude

1. **Copy the system prompt**: Open `gcal-assistant-prompt.md` and copy the entire contents
2. **Apply to Claude**: Paste the system prompt content into `CLAUDE.md`
3. **Update user email**: Replace `[USER_EMAIL]` placeholders with your actual email address
4. **Start using**: Claude will now follow the comprehensive calendar management guidelines

See `CLAUDE.md` for detailed Claude-specific instructions and examples.

### 🟡 Gemini-CLI Integration

#### Using the System Prompt with Gemini CLI
1. **Copy the system prompt**: Open `gcal-assistant-prompt.md` and copy the entire contents
2. **Apply to Claude**: Paste the system prompt content into `GEMINI.md`
3. **Update user email**: Replace `[USER_EMAIL]` placeholders with your actual email address
4. **Start using**: Claude will now follow the comprehensive calendar management guidelines

See `GEMINI.md` for detailed Gemini-CLI specific instructions and examples.

### 🟣 Cursor IDE Integration

#### Configuration Steps

1. **Open Cursor Settings**: Go to Settings → Rules
2. **Create New Rule**: Click "Add Rule" 
3. **Rule Configuration**:
   - **Name**: "Google Calendar Assistant"
   - **Description**: "Comprehensive Google Calendar management with MCP server integration"
   - **Rule Type**: "System Prompt" or "Behavioral Rule"
4. **Apply System Prompt**: Copy the entire contents of `gcal-assistant-prompt.md` into the rule text area
5. **Customize**: Replace `[USER_EMAIL]` with your actual email address
6. **Save and Activate**: Save the rule and ensure it's enabled

#### MCP Server Configuration in Cursor

Add to your Cursor workspace settings (`.cursor/settings.json`):

```json
{
  "mcp.servers": {
    "gcal-mcp-server": {
      "command": "/path/to/gcal-mcp-server",
      "args": [],
      "env": {}
    }
  }
}
```

#### Using in Cursor

Once configured, you can:
- Use the integrated chat with calendar management capabilities
- Access calendar functions through the command palette
- Get intelligent suggestions for meeting scheduling
- Use RSVP management and day organization features

### 🎯 Example Usage Across All Platforms

Once configured with any AI assistant, you can use natural language commands like:

```
Create a meeting titled "Project Review" tomorrow at 2 PM for 1 hour with john@company.com and jane@company.com. Include a Google Meet link.
```

```
Check if alice@company.com and bob@company.com are available Friday between 9 AM and 5 PM.
```

```
Show me my remaining meetings for today in timeline format.
```

```
Accept meeting 3 and decline meetings 5 and 7.
```

```
Organize my day tomorrow for optimal productivity.
```

```
Reschedule the "Team Standup" event from 10 AM to 11 AM and add charlie@company.com as an attendee.
```

## Available Tools

The MCP server provides five core tools for comprehensive calendar management:

### 1. create_event

Create a new calendar event with comprehensive options and automatic availability checking.

**Required Parameters:**
- `summary`: Event title
- `start_time`: Start time (RFC3339 format)
- `end_time`: End time (RFC3339 format)

**Optional Parameters:**
- `calendar_id`: Target calendar (default: "primary")
- `description`: Event description
- `location`: Event location
- `timezone`: Event timezone (default: "UTC")
- `all_day`: All-day event flag (default: false)
- `attendees`: Array of attendee email addresses or objects with RSVP status
- `recurrence`: Recurrence rules (RRULE format)
- `visibility`: Event visibility ("default", "public", "private", "confidential")
- `send_notifications`: Send email notifications (default: true)
- `guest_can_modify`: Allow guests to modify event (default: false)
- `guest_can_invite_others`: Allow guests to invite others (default: true)
- `guest_can_see_other_guests`: Allow guests to see other guests (default: true)
- `create_meet_link`: Create Google Meet link (default: false)
- `reminders`: Custom reminder settings
- `eventType`: Event classification ("default" | "focusTime" | "workingLocation"). Default: "default".
- `workingLocation`: Only when `eventType` = "workingLocation". Object: `{ "type": "home|office|custom", "label": "<text>" }`.
- `focusTimeProperties`: Only when `eventType` = "focusTime". Object with:
  - `autoDeclineMode`: "declineOnlyNew" | "declineAll"
  - `chatStatus`: "doNotDisturb" | "available"
  - `declineMessage`: Optional custom decline message

**Enhanced Features:**
- **Automatic Availability Checking**: Validates all attendee availability before creation
- **Conflict Prevention**: Prevents double-booking by checking free/busy status
- **Smart Defaults**: Applies intelligent defaults based on meeting context

**Example:**
```json
{
  "summary": "Team Meeting",
  "start_time": "2024-01-15T10:00:00-08:00",
  "end_time": "2024-01-15T11:00:00-08:00",
  "description": "Weekly team sync meeting",
  "location": "Conference Room A",
  "attendees": ["alice@company.com", "bob@company.com"],
  "create_meet_link": true,
  "reminders": {
    "use_default": false,
    "overrides": [
      {"method": "email", "minutes": 1440},
      {"method": "popup", "minutes": 15}
    ]
  }
}
```

#### Event Type Examples

Focus Time block (auto-decline and DND):

```json
{
  "summary": "Deep Work - Roadmap Planning",
  "start_time": "2024-01-16T13:00:00-08:00",
  "end_time": "2024-01-16T15:00:00-08:00",
  "visibility": "private",
  "eventType": "focusTime",
  "focusTimeProperties": {
    "autoDeclineMode": "declineOnlyNew",
    "chatStatus": "doNotDisturb",
    "declineMessage": "I'm in focus time and will respond after."
  }
}
```

Working Location (all-day indicator):

```json
{
  "summary": "Working from Home",
  "all_day": true,
  "start_time": "2024-01-17T00:00:00-08:00",
  "end_time": "2024-01-18T00:00:00-08:00",
  "eventType": "workingLocation",
  "workingLocation": { "type": "home", "label": "Working from Home" }
}
```

### 2. edit_event

Update an existing calendar event using true PATCH semantics (only provided fields are modified).

**Required Parameters:**
- `event_id`: ID of the event to edit

**Optional Parameters:**
- All parameters from create_event (only provided parameters are updated)

Supports updating event-type specific fields: `eventType`, `workingLocation`, and `focusTimeProperties`.

**Enhanced Features:**
- **True PATCH Semantics**: Only modifies fields that are explicitly provided
- **RSVP Management**: Update attendance status using attendee objects with `response_status`
- **Attendee Format Flexibility**: Supports both legacy string arrays and enhanced object format
- **Availability Validation**: Checks attendee availability when rescheduling

**RSVP Status Values:**
- `"accepted"`: Attendee has accepted the invitation
- `"declined"`: Attendee has declined the invitation  
- `"tentative"`: Attendee has marked as maybe/tentative
- `"needsAction"`: Attendee has not yet responded (default)

**RSVP Example:**
```json
{
  "event_id": "abc123def456",
  "attendees": [{"email": "user@example.com", "response_status": "accepted"}]
}
```

### 3. delete_event

Delete a calendar event.

**Required Parameters:**
- `event_id`: ID of the event to delete

**Optional Parameters:**
- `calendar_id`: Calendar ID (default: "primary")
- `send_notifications`: Send cancellation notifications (default: true)

### 4. search_attendees

Search for potential meeting attendees with email validation.

**Required Parameters:**
- `query`: Search query (email address or name)

**Optional Parameters:**
- `max_results`: Maximum results (default: 10)
- `domain`: Limit to specific domain

**Enhanced Features:**
- **Email Format Validation**: Ensures valid email address format
- **Domain Filtering**: Supports organization-specific searches
- **Smart Suggestions**: Provides relevant attendee recommendations

### 5. get_attendee_freebusy

Check free/busy status for attendees with intelligent conflict detection.

**Required Parameters:**
- `attendee_emails`: Array of attendee email addresses
- `time_min`: Start time for query (RFC3339 format)
- `time_max`: End time for query (RFC3339 format)

**Optional Parameters:**
- `timezone`: Query timezone (default: "UTC")

**Enhanced Features:**
- **Intelligent Conflict Detection**: Accurately identifies overlapping time periods
- **Multi-timezone Support**: Handles attendees across different time zones
- **Availability Recommendations**: Suggests optimal meeting times
- **Comprehensive Analysis**: Shows busy periods and available time slots

## Time Format

All times must be in RFC3339 format:

- **With timezone**: `2024-01-15T10:00:00-08:00`
- **UTC**: `2024-01-15T18:00:00Z`
- **All-day events**: Use `00:00:00` time with appropriate date

## Recurrence Patterns

Use RRULE format for recurring events:

- **Daily**: `["RRULE:FREQ=DAILY;COUNT=10"]`
- **Weekly**: `["RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR"]`
- **Monthly**: `["RRULE:FREQ=MONTHLY;BYMONTHDAY=15"]`
- **Yearly**: `["RRULE:FREQ=YEARLY;BYMONTH=12;BYMONTHDAY=25"]`

## Development

### Project Structure

```
gcal-mcp-server/
├── cmd/server/                    # Main server entry point
├── internal/
│   ├── auth/                     # OAuth authentication
│   ├── calendar/                 # Calendar API client and tools
│   └── mcp/                      # MCP protocol implementation
├── bin/                          # Compiled binaries
├── gcal-assistant-prompt.md      # Comprehensive system prompt for AI assistants
├── CLAUDE.md                     # Claude Desktop integration guide
├── GEMINI.md                     # Gemini-CLI integration guide
├── README.md                     # Main documentation (this file)
├── Makefile                      # Build automation
├── go.mod                        # Go module dependencies
├── go.sum                        # Go module checksums
└── token.json                    # OAuth token storage (auto-generated)
```

### Key Files

- **`gcal-assistant-prompt.md`**: The comprehensive system prompt containing all behavioral guidelines, workflow instructions, and response templates for AI assistants
- **`CLAUDE.md`**: Specific instructions for integrating with Claude Desktop, including configuration and usage examples
- **`GEMINI.md`**: Complete guide for using the MCP server with Google's Gemini-CLI tool
- **`README.md`**: This file - comprehensive documentation covering installation, configuration, and usage
- **`Makefile`**: Build automation for easy compilation and deployment

### Building from Source

```bash
# Clone repository
git clone <repository-url>
cd gcal-mcp-server

# Install dependencies
go mod tidy

# Build
make build

# Run
./bin/gcal-mcp-server
```

### Testing

```bash
# Run tests
go test ./...

# Run with verbose output
go test -v ./...
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Ensure `credentials.json` is in the correct location
   - Check that Google Calendar API is enabled in your project
   - Verify OAuth consent screen is properly configured

2. **Permission Denied**
   - Make sure the OAuth client has the correct scopes
   - Check that the user has granted calendar access
   - Re-authenticate if tokens have expired

3. **Invalid Time Format**
   - Use RFC3339 format for all times
   - Include timezone information
   - Ensure end time is after start time

4. **Attendee Lookup Issues**
   - Provide full email addresses
   - Check that attendees have Google accounts
   - Verify domain restrictions if applicable

### Debug Mode

Run with debug logging:

```bash
export GCAL_DEBUG=true
./gcal-mcp-server
```

### Log Files

Server logs are written to stderr and can be captured:

```bash
./gcal-mcp-server 2> gcal-server.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Google Calendar API documentation
3. Open an issue on GitHub

## 🧠 Advanced AI Features

The Google Calendar MCP Server includes sophisticated AI-driven features that enhance calendar management:

### 🎯 Smart Event Management

- **Automatic Conflict Detection**: Visual indicators (⚠️) for overlapping meetings
- **RSVP Command Processing**: Natural language commands like "accept meeting 3" or "decline meetings 2,4,6"
- **Timeline Visualization**: Gantt chart-style views when users request "timeline" format
- **Meeting Filtering**: Smart filtering for "remaining today" events based on current time

### 📊 Intelligent Scheduling

- **Day Organization**: Automatically reorganize calendar for optimal productivity with 2-hour meeting blocks
- **Availability Validation**: Mandatory free/busy checking before any event creation
- **Meeting Immutability Rules**: Respects shared calendars and external attendee constraints
- **Break Optimization**: Ensures 1-hour breaks between meeting blocks for focused work time

### 🎨 Enhanced User Experience

- **Numbered Meeting References**: All meetings displayed with numbers for easy action commands
- **Status Visualization**: Clear attendance status indicators (✅ ❌ ⏳ ❓)
- **Strikethrough Formatting**: Declined meetings shown with crossed-out styling
- **PII Protection**: Automatic obfuscation of personal information in timeline views

### 🔄 Workflow Automation

- **Batch RSVP Operations**: Handle multiple meeting responses in single commands
- **Smart Defaults**: Context-aware default values for meeting creation
- **Notification Management**: Intelligent notification sending based on change significance
- **Error Recovery**: Graceful handling of scheduling conflicts with alternative suggestions

## 📋 System Prompt Integration

The repository includes a comprehensive system prompt (`gcal-assistant-prompt.md`) that provides:

- **Behavioral Guidelines**: Detailed instructions for calendar management workflows
- **Response Templates**: Consistent formatting for event listings, creation confirmations, and error messages
- **Advanced Features**: RSVP management, day organization, and timeline visualization instructions
- **Error Handling**: Comprehensive validation and recovery procedures

### Using the System Prompt

1. **For Claude Desktop**: Copy `gcal-assistant-prompt.md` content into your conversation
2. **For Gemini-CLI**: Use `--system-prompt "$(cat gcal-assistant-prompt.md)"`
3. **For Cursor**: Add the content as a behavioral rule in Settings → Rules
4. **Customization**: Replace `[USER_EMAIL]` with your actual email address

See the respective platform documentation:
- [CLAUDE.md](CLAUDE.md) - Claude Desktop specific instructions
- [GEMINI.md](GEMINI.md) - Gemini-CLI integration guide