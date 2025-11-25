---
argument-hint: Analyze calendar and recommend changes for overlaps and back-to-back meetings
description: Generate recommendations to resolve conflicts and optimize schedule
allowed-tools: [get_attendee_freebusy, list_events]
model: claude-sonnet-4-5
---

Analyze calendar events and provide scheduling recommendations. Follow these steps exactly:

1. Analyze the events
2. Output ONLY recommendations in the specified format

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
- Events that break up long back-to-back blocks (>3hr)
- Check the exact same timeslot in the previous week to see the users status choice, and use this to help make a recommendation

**Your analysis steps:**
1. Find all events where `has_overlap: true`, but ignore if two meeting in a conflict has 1 accept and the rest tentative
2. For each overlap, recommend which event to decline/reschedule
3. Check for long back-to-back meeting blocks (>2 hours, excluding focusTime)
4. Output recommendations in the format below

**CRITICAL RULES:**
- If any events have `has_overlap: true`, you MUST provide recommendations
- Do NOT say "schedule looks good" if overlaps exist
- Output ONLY the recommendations, NO questions, NO explanations about the process
-
**Output format** (2 lines per recommendation):
```
1. DECLINE: [Event Title] at [time]
   Reason: [One sentence - max 80 chars]

2. RESCHEDULE: [Event Title] at [time]
   Reason: [One sentence - max 80 chars]
3. TENTATIVE: [Event Title] at [time]
   Reason: [One sentence - max 80 chars]
2. ACCEPT: [Event Title] at [time]
   Reason: [One sentence - max 80 chars]

```

**Prioritization** (when choosing which event to decline):
- Smaller meetings (<4 attendees) are easier to reschedule
- Meetings where you're tentative vs accepted
- Focus time can be moved more easily than meetings with many people

NO event IDs in output. If truly no issues: "No recommendations - schedule looks good"
