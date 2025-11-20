#!/usr/bin/env python3
"""Test the day filter parsing"""

from datetime import datetime, timedelta

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


# Test cases
test_cases = ['tomorrow', 'mon', 'tue', 'friday', 'today']

for test in test_cases:
    result = parse_day_filter(test)
    print(f"\n{test}:")
    print(f"  time_filter: {result[0]}")
    print(f"  time_min: {result[1]}")
    print(f"  time_max: {result[2]}")
