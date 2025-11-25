---
argument-hint: Analyze calendar and recommend changes for overlaps and back-to-back meetings
description: Generate recommendations to resolve conflicts and optimize schedule
allowed-tools: [get_attendee_freebusy, list_events]
model: claude-sonnet-4-5
---

Analyze calendar events and provide scheduling recommendations. Follow these steps exactly:

1. **Analyze conflicts and group them** - For each time block with conflicts, make ONE recommendation that addresses ALL conflicting events in that block
2. **Use smart tools to find solutions** - Use get_attendee_freebusy and list_events to inform recommendations
3. **Output ONLY recommendations** - No questions, no explanations

DO NOT ask questions. DO NOT request clarification. Analyze the provided data and give recommendations.

The JSON structure is: `{"events": [...], "count": N}`

Each event has these fields:
- id: unique event identifier
- summary: event title
- start/end: time range with dateTime
- has_overlap: true if conflicts with other events
- overlapping_event_ids: list of conflicting event IDs
- attendees: list of attendees with email, displayName, responseStatus
- eventType: "default", "focusTime", or "workingLocation"
- responseStatus: "accepted", "declined", "tentative", "needsAction"

## Analysis Steps (Execute in Order):

### Step 1: Group Conflicts by Time Block
- Find all events where `has_overlap: true`
- Group conflicting events together (e.g., if Event A conflicts with B, and B conflicts with C, they're all one conflict group)
- For each conflict group, make ONE recommendation (not one per event)

### Step 2: Analyze Each Conflict Group
For each conflict group, determine priority using these factors:

**Meeting Importance Signals:**
- Only attendee = personal task (low priority, easy to move)
- 1-4 attendees = small meeting (medium priority, can reschedule)
- 5+ attendees = large meeting (high priority, hard to reschedule)
- Most attendees declined = low importance
- Your response status: accepted > tentative > needsAction

**Use list_events to check history:**
- Call list_events for previous week (time_min = 7 days ago, time_max = today)
- Find events with same summary at same time last week
- If you declined last week, probably decline this week too
- If you accepted last week, this is probably important

**Meeting Context:**
- Is this a 1:1? Check if only 2 attendees
- Is this recurring? Look for similar events in the data
- Is this blocking focus time? Check eventType

### Step 3: Find Alternative Times (for small meetings only)
For meetings with ≤4 attendees that should be rescheduled:
- Extract attendee email addresses
- Call get_attendee_freebusy for the next 3-5 days
- Find a 30-60min slot where ALL attendees are free
- Include this alternative time in your recommendation

### Step 4: Generate Combined Recommendations
**CRITICAL**: For each conflict group, write ONE recommendation that addresses the entire conflict:

**Format for conflicts (ONE recommendation per time block):**
```
1. CONFLICT at [start time - end time]: Keep [Meeting A], decline [Meeting B]
   Reason: [Why keep A] [Alternative for B if applicable - max 80 chars total]
```

**Examples:**
```
1. CONFLICT at 2:00pm-3:00pm: Keep "Product Review" (8 attendees), decline "1:1 with John"
   Reason: Large meeting vs 1:1. Reschedule 1:1 to Wed 3pm (all free per freebusy)

2. CONFLICT at 10:00am-11:00am: Decline both "Team Sync" and "Planning", block as Focus
   Reason: You declined both last week. Use time for focus work instead

3. CONFLICT at 1:00pm-2:00pm: Keep "Client Call", make "Standup" tentative
   Reason: Client (5 attendees) > internal standup (3 attendees). Join standup if client ends early
```

### Step 5: Check for Back-to-Back Meeting Overload
- Find sequences of 3+ hours of back-to-back meetings (excluding focusTime)
- Recommend declining the least important meeting to create a break

**CRITICAL RULES:**
- ONE recommendation per conflict time block, not per event
- Always check previous week's history for recurring meetings
- Use get_attendee_freebusy for meetings ≤4 attendees to suggest specific alternative times
- If user is only attendee, it's personal time (easy to move)
- If you can't find enough context, err on the side of keeping larger meetings
- Each recommendation must fit in 2 lines (action + reason, max 80 chars per line)
- Provide as many recommendations as needed (UI supports scrolling)

**Output format:**
```
1. CONFLICT at [time]: [action]
   Reason: [why] [alternative if applicable]

2. DECLINE: [Event Title] at [time]
   Reason: [One sentence - max 80 chars]

3. RESCHEDULE: [Event Title] from [time] to [new time]
   Reason: [One sentence - max 80 chars]
```

**If truly no issues:** "No recommendations - schedule looks good"
