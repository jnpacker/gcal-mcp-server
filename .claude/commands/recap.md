---
argument-hint: Event ID or name of a recurring meeting
description: Fetches Gemini notes from the previous occurrence and inserts a condensed recap into the next occurrence's description
allowed-tools: [get_meeting_context, edit_event, list_events]
model: claude-sonnet-4-6
---

Generate a condensed "previous meeting recap" and insert it into the next occurrence of a recurring meeting.

Steps:
1. If the user provided a name (not an ID), use list_events with a broad time range to find the event and extract its ID. Use output_format=json to get the raw event IDs.
2. Call get_meeting_context with the event_id to retrieve:
   - The Gemini notes from the most recent past occurrence (previous_notes_content)
   - The next_occurrence_id and next_occurrence_time
3. If next_occurrence_id is empty, inform the user that no upcoming occurrence was found and show the recap only (do not call edit_event).
4. Generate a condensed recap from the notes. Target ~150 words, readable in 30 seconds. Format exactly as:

--- Previous Meeting Recap ([Month Day, Year]) ---
Decisions:
• [key decision or outcome — max 4 bullets, be specific]

Action Items:
• [[Owner]] [what they need to do] — include both explicit assignments and implied follow-ups
• ...
----------------------------------------------------

5. The recap must stand alone — someone who missed the meeting should understand the state after reading it.
6. Call edit_event with:
   - event_id: the next_occurrence_id
   - description: the recap text. If the existing event description is non-empty, append two newlines then the existing description after the recap block.
7. Confirm to the user: show the recap, the date of the occurrence it was pulled from, and the date of the occurrence that was updated.
