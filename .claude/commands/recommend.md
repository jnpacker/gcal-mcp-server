---
argument-hint: Analyze calendar and recommend changes for overlaps and back-to-back meetings
description: Generate recommendations to resolve conflicts and optimize schedule
allowed-tools: [Read]
model: claude-sonnet-4-5
---

Analyze calendar events and provide scheduling recommendations. Follow these steps exactly:

1. Extract the file path from the user's message
2. Use Read tool to load the JSON file
3. Analyze the events
4. Output ONLY recommendations in the specified format

DO NOT ask questions. DO NOT request clarification. Analyze the provided data and give recommendations.

The JSON structure is: `{"events": [...], "count": N}`

Each event has these fields:
- summary: event title
- start/end: time range
- has_overlap: true if conflicts with other events
- overlapping_event_ids: list of conflicting event IDs
- attendees: list of attendees with responseStatus
- eventType: "default", "focusTime", or "workingLocation"

What to look for:
- Events with `has_overlap: true` (these are CRITICAL conflicts - MUST be addressed)
- Back-to-back meetings exceeding 2 hours without breaks
  - **Important**: Events with `eventType: "focusTime"` are BREAKS, not meetings
  - Focus time blocks interrupt contiguous meeting sequences
  - Example: Meeting 9-10am + Focus 10-11am + Meeting 11-12pm = two 1hr blocks, NOT 3hr
- Meeting attendee counts
- Events that should be declined, rescheduled, or shortened

Prioritization criteria (recommend declining/rescheduling):
- Meetings with <4 participants (easier to reschedule)
- Meetings where most attendees have already declined
- Events that break up long back-to-back blocks (>2hr)
- Meetings during back-to-back stretches exceeding 2 hours

**Your analysis steps:**
1. Use the Read tool to read the JSON file (path is in user's message)
2. Find all events where `has_overlap: true`
3. For each overlap, recommend which event to decline/reschedule
4. Check for long back-to-back meeting blocks (>2 hours, excluding focusTime)
5. Output recommendations in the format below

**CRITICAL RULES:**
- If any events have `has_overlap: true`, you MUST provide recommendations
- Do NOT say "schedule looks good" if overlaps exist
- Output ONLY the recommendations, NO questions, NO explanations about the process
- If you cannot read the file, output: "Error: Could not read events file"

**Output format** (2 lines per recommendation):
```
1. DECLINE: [Event Title] at [time]
   Reason: [One sentence - max 80 chars]

2. RESCHEDULE: [Event Title] at [time]
   Reason: [One sentence - max 80 chars]
```

**Prioritization** (when choosing which event to decline):
- Smaller meetings (<4 attendees) are easier to reschedule
- Meetings where you're tentative vs accepted
- Focus time can be moved more easily than meetings with many people

NO event IDs in output. If truly no issues: "No recommendations - schedule looks good"
