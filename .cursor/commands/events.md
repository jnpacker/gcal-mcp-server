
List events for the requested day in a compact markdown table with precise formatting and smart annotations.

Requirements:
- Use the system `date` command to extract the current date and time to base the request on.
- Use the list_events tool to retrieve events. Declined events are excluded by default; if the user asks to see declined, include them and apply strikethrough formatting.
- Each event in 'list_events' includes a **Has Overlap:** field, add the ⚠️ prefix to the Time cell for each conflicting event whether declined or not.
- Number events sequentially in the first column (#). Add an arrow (➤) in the # column for the event currently in progress. Append ⏰ after the event name for the current event.
- Business hours: 9:00 AM – 5:00 PM for available slot calculations. Only list slots of 30 minutes or longer.
- Columns: # | Day | Time | Event | 📬 | Attendees | Link
- Status emoji in 📬 column: ✅ accepted | ⏳ maybe/tentative | ❓ no response | 🎧 for focus time. For working location, show 🏠 (Home) or 🏢 (Office) in the 📬 column.
- Attendees column: Show attendee count (e.g., "5 attendees"). When all attendees except you have declined, append ❌ to the count (e.g., "2 attendees ❌").
- Link column: always include the meeting link when available; do not include physical locations here. If a meeting link exists, show only a markdown link like [Meet](URL).
- Show available time slots between meetings, enumerated A1, A2, etc. Use 🟩 blocks where each 🟩 equals 30 minutes.
- When calculating available time slots, declined events (where I have declined) are treated as free time and do not block availability.
- After the table, include a Conflicts section. Only report conflicts for events where the API returned **Has Overlap: true**. Reference events by their row numbers and show the overlapping time window when available. Do not independently calculate overlaps based on time windows - trust the API's detection. If no events have Has Overlap: true, state: "Conflicts: None".
- **Smart Meeting Suggestions**: When displaying events, analyze attendee responses and provide actionable suggestions:
  - For meetings with 1-2 total attendees where all other attendees have declined (❌), suggest either declining the meeting or deleting the event
  - For meetings with 3+ attendees where more than 75% have declined, suggest reaching out to the organizer about rescheduling
  - Include these suggestions in a "Suggestions" section after the Conflicts section. (Do not display suggestions that don't actually have a recommendation)

Example output:

📅 Events for Today (DAY, MONTH DAY_NUMBER):

Use a table with these columns:
| # | Day | Time | Event | 📬 | Attendees | Link |
|---|---|---|---|---|---|---|

📊 Total: 5 events | 3 available time slots | Current time: HH:MM PM ⏰
Status: ✅ Accepted | ⏳ Maybe/Tentative | ❓ No Response | 🎧 Focus time | ⚠️  Conflict

Conflicts:
- (#)-(#) [HH:MM-HH:MM] Description of the two conflicting events

Suggestions:
- (#) Make a suggest of what to change, if your suggestion does actually contain a change, don't show it.
