---
argument-hint: Analyze calendar and recommend changes for overlaps and back-to-back meetings
description: Generate recommendations to resolve conflicts and optimize schedule
allowed-tools: [get_attendee_freebusy]
model: claude-sonnet-4-5
---

Analyze calendar events and provide scheduling recommendations. Follow these steps exactly:

1. **Prioritize by color** - Use the color-based priority system to evaluate event importance
2. **Analyze conflicts and group them** - For each time block with conflicts, make ONE recommendation that addresses ALL conflicting events in that block
3. **Use smart tools to find solutions** - Use get_attendee_freebusy to find alternative meeting times when needed
4. **Output ONLY recommendations** - No questions, no explanations

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
- colorId: event color (determines priority)

## Color-Based Priority System

Assign priority based on event color (colorId):

**Tier 1 (Highest Priority - KEEP):**
- ColorId 1 ("Customer") - essential for customer relationships
- Large ColorId 4 ("Sync Up") colored events (5+ attendees) - high-impact syncs

**Tier 2 (High Priority - KEEP):**
- ColorId 2 ("Cross Team") - cross-organizational alignment
- ColorId 10 ("Team") - core team meetings

**Tier 3 (Flexible/Moveable):**
- Small ColorId 4 ("Sync Up") colored events (≤3 attendees) - can be rescheduled to resolve conflicts with higher priority meetings

**Tier 4 (Lowest Priority - Can DECLINE/TENTATIVE):**
- ColorId None ("Default") - generic/optional meetings
- ColorId 9 ("Communities") - community participation

**Special Cases (Not Ranked in Priority):**
- ColorId 5 ("Focus Time") - protected focus/working blocks, should not be moved unless critical conflicts require it

### Color ID Mapping (Your Calendar)
- **ColorId 1** = "Customer"
- **ColorId 2** = "Cross Team"
- **ColorId 4** = "Sync Up"
- **ColorId 5** = "Focus Time"
- **ColorId 9** = "Communities"
- **ColorId 10** = "Team"
- **No ColorId** = "Default"

## Analysis Steps (Execute in Order):

### Step 1: Establish Color Mappings
Ask yourself: Which colorIds in the provided events correspond to which categories?
- Look for patterns in the event summaries and attendee lists
- Make reasonable assumptions: "Sync Up" in title = Sync Up color, "Customer" in context = Customer color, etc.
- If you cannot determine a color mapping, treat the event as "Default" priority

### Step 2: Group Conflicts by Time Block and Priority
- Find all events where `has_overlap: true`
- Group conflicting events together (e.g., if Event A conflicts with B, and B conflicts with C, they're all one conflict group)
- For each conflict group, assign priority tiers to each event based on color
- Identify which event(s) should be kept based on tier hierarchy

### Step 3: Analyze Each Conflict Group
For each conflict group, determine which event to keep using:

**Primary Factor: Color Priority**
- Always keep higher-tier colored events over lower-tier
- Only consider attendee count and response status as tiebreakers within the same tier

**Secondary Factors (for same-tier events):**
- Large meetings (5+ attendees) > small meetings (≤4 attendees)
- Your response status: accepted > tentative > needsAction
- Small Sync Up events (≤3 attendees) are moveable to resolve Tier 1-3 conflicts

**Meeting Context:**
- Check eventType for focusTime events (can be moved if needed)
- Is this a 1:1? Check if only 2 attendees

**Special Case: Partial Overlap with Equal Priority**
When two meetings have equal weight (same tier), one can't be moved, and there's partial overlap:
- Calculate the overlap duration (e.g., Meeting B starts 30m into Meeting A which is 1hr long)
- If partial overlap exists (not complete overlap):
  - Suggest making the meeting that starts later (Meeting B) tentative
  - Recommend attending both if possible, but be prepared to prioritize
  - Advise front-loading important topics/agenda items in the first meeting (Meeting A) to ensure they're covered before the conflict
  - Include reasoning about why attending both could be valuable (based on meeting context, attendees, etc.)

### Step 4: Find Alternative Times (for moveable meetings only)
For small meetings (≤4 attendees) that should be rescheduled to resolve conflicts:
- Extract attendee email addresses
- Call get_attendee_freebusy for the next 3-5 days
- Find a 30-60min slot where ALL attendees are free
- Include this alternative time in your recommendation

### Step 5: Generate Combined Recommendations
**CRITICAL**: For each conflict group, write ONE recommendation that addresses the entire conflict:

**Format for conflicts (ONE recommendation per time block):**
```
1. CONFLICT at [start time - end time]: Keep [Meeting A] (Tier X), decline [Meeting B]
   Reason: [Color priority reasoning] [Alternative for B if applicable - max 80 chars total]
```

**Examples:**
```
1. CONFLICT at 2:00pm-3:00pm: Keep "Customer Q4 Review" (Customer Tier 1), decline "Team Sync"
   Reason: Customer tier 1 > Team tier 2. Reschedule Team Sync to Wed 3pm (all free)

2. CONFLICT at 10:00am-11:00am: Keep "Cross Team Alignment" (Cross Team Tier 2), make "Weekly Standup" tentative
   Reason: Cross Team tier 2 > Sync Up tier 3 (only 3 attendees, moveable)

3. CONFLICT at 1:00pm-2:00pm: Decline "Community Event", keep "Team Standup"
   Reason: Community tier 4 < Team tier 2. Community is lowest priority

4. PARTIAL OVERLAP at 2:00pm-3:00pm: Keep "Team Planning" accepted, make "Design Review" (starts 2:30pm) tentative
   Reason: Both Tier 2, partial overlap (30m). Attend both if possible. Front-load your topics in Team Planning to cover before 2:30pm conflict
```

### Step 6: Check for Back-to-Back Meeting Overload
- Find sequences of 3+ hours of back-to-back meetings (excluding focusTime/Focus time/Development - Focus time/Paperwork - Focus time)
- Recommend declining or moving the lowest-priority meeting to create a break
- Use color tier as primary factor for selecting which meeting to decline

**CRITICAL RULES:**
- ONE recommendation per conflict time block, not per event
- Color priority is the PRIMARY factor in all recommendations
- Use get_attendee_freebusy for meetings ≤4 attendees to suggest specific alternative times
- Small Sync Up events (≤3 attendees) are candidates for moving to resolve Tier 1-3 conflicts
- If user is only attendee, it's personal time (easy to move)
- If you can't determine color mapping, treat as "Default" (Tier 4)
- Each recommendation must fit in 2 lines (action + reason, max 80 chars per line)
- Provide as many recommendations as needed (UI supports scrolling)
- Analyze ONLY the events provided - do not make assumptions about events outside the given data

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

IMPORTANT: Analyze ONLY the calendar events in the file 'event-prompt.json'. Do NOT fetch additional events using list_events or any other tools.

Read the events from event-prompt.json and analyze them.

The events in that file represent the current calendar view and should be your ONLY source of data for analysis.

Focus your analysis on:
- Events with conflicts (has_overlap: true)
- Back-to-back meetings exceeding 2 hours
- Meetings that should be declined or rescheduled

Provide recommendations ONLY for the events in $ARGUMENTS
