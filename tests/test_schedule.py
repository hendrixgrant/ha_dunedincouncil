"""Tests for the pure schedule logic. Run with: pytest tests/"""

import importlib.util
from datetime import date
from pathlib import Path

_path = Path(__file__).parent.parent / "custom_components" / "dunedin_council" / "schedule.py"
_spec = importlib.util.spec_from_file_location("schedule", _path)
s = importlib.util.module_from_spec(_spec)
import sys; sys.modules["schedule"] = s  # dataclass needs the module registered
_spec.loader.exec_module(s)

# Wed 18 Nov 2026 is in a "blue" week (anchor = Monday 16 Nov 2026).
ANCHOR = date(2026, 11, 16)


def nc(today, weekday, cadence, anchor_type=s.BLUE, anchor=ANCHOR, tertiary=False):
    return s.next_collection(today, weekday, cadence, anchor, anchor_type, tertiary)


def test_easter_dates():
    assert s.easter_sunday(2026) == date(2026, 4, 5)
    assert s.easter_sunday(2027) == date(2027, 3, 28)
    assert s.easter_sunday(2025) == date(2025, 4, 20)


def test_weekly_and_fortnightly_on_collection_day():
    today = date(2026, 11, 18)  # Wednesday, blue week
    assert nc(today, 3, s.WEEKLY) == today
    assert nc(today, 3, s.BLUE) == today
    assert nc(today, 3, s.YELLOW) == date(2026, 11, 25)


def test_alternation_continues_forward():
    # Anchor week (16 Nov) is blue. Week of 23 Nov is yellow, 30 Nov is blue again.
    today = date(2026, 11, 26)  # Thursday after the 25th's collection
    assert nc(today, 3, s.YELLOW) == date(2026, 12, 9)   # yellow weeks: 25 Nov, 9 Dec
    assert nc(today, 3, s.BLUE) == date(2026, 12, 2)     # blue weeks: 18 Nov, 2 Dec
    assert nc(date(2026, 12, 3), 3, s.BLUE) == date(2026, 12, 16)


def test_yellow_week_anchor():
    today = date(2026, 11, 18)
    assert nc(today, 3, s.YELLOW, anchor_type=s.YELLOW) == today
    assert nc(today, 3, s.BLUE, anchor_type=s.YELLOW) == date(2026, 11, 25)


def test_day_already_passed_this_week():
    today = date(2026, 11, 20)  # Friday; Wednesday collection already happened
    assert nc(today, 3, s.WEEKLY) == date(2026, 11, 25)
    assert nc(today, 3, s.BLUE) == date(2026, 12, 2)
    assert nc(today, 3, s.YELLOW) == date(2026, 11, 25)


def test_christmas_new_year_shift_to_saturday():
    # Christmas 2026 and New Year's Day 2027 are both Fridays.
    assert nc(date(2026, 12, 21), 5, s.WEEKLY) == date(2026, 12, 26)
    assert nc(date(2026, 12, 28), 5, s.WEEKLY) == date(2027, 1, 2)
    # A Wednesday collection that week is unaffected.
    assert nc(date(2026, 12, 21), 3, s.WEEKLY) == date(2026, 12, 23)


def test_good_friday_2027():
    assert s.is_no_collection_day(date(2027, 3, 26))
    assert nc(date(2027, 3, 24), 5, s.WEEKLY, anchor_type=None) == date(2027, 3, 27)
    # On Good Friday itself the bins are still upcoming (Saturday)
    assert nc(date(2027, 3, 26), 5, s.WEEKLY) == date(2027, 3, 27)


def test_holiday_on_weekend_not_shifted():
    # Christmas 2027 is a Saturday
    assert not s.is_no_collection_day(date(2027, 12, 25))


def test_shifted_week_parity_uses_nominal_week():
    # Friday collection. The week of 21 Dec 2026 is 5 weeks after the blue anchor
    # week, so it's a YELLOW week: yellow bin shifts from Fri 25 Dec to Sat 26 Dec,
    # and the blue-week bins don't go out until the following week.
    assert nc(date(2026, 12, 21), 5, s.YELLOW) == date(2026, 12, 26)
    assert nc(date(2026, 12, 21), 5, s.BLUE) == date(2027, 1, 2)


def test_tertiary_all_weekly_even_without_anchor():
    assert nc(date(2026, 11, 18), 2, s.YELLOW, anchor_type=None, tertiary=True) == date(2026, 11, 24)
    assert nc(date(2026, 11, 18), 2, s.BLUE, anchor_type=None, tertiary=True) == date(2026, 11, 24)


def test_unknown_week_returns_none_for_fortnightly_only():
    assert nc(date(2026, 11, 18), 3, s.BLUE, anchor_type=None) is None
    assert nc(date(2026, 11, 18), 3, s.WEEKLY, anchor_type=None) == date(2026, 11, 18)


def test_no_collection_property():
    assert nc(date(2026, 11, 18), None, s.WEEKLY) is None
    assert nc(date(2026, 11, 18), 0, s.WEEKLY) is None


def test_parse_week_type():
    assert s.parse_week_type("b") == s.BLUE
    assert s.parse_week_type("Y") == s.YELLOW
    assert s.parse_week_type("b", swap=True) == s.YELLOW
    assert s.parse_week_type("x") is None
    assert s.parse_week_type(None) is None


def test_summary_groups_bins_on_soonest_date():
    d, bins = s.next_collection_summary(date(2026, 11, 18), 3, ANCHOR, s.BLUE)
    assert d == date(2026, 11, 18)
    assert {b.key for b in bins} == {"food_garden", "rubbish", "glass"}
    d, bins = s.next_collection_summary(date(2026, 11, 19), 3, ANCHOR, s.BLUE)
    assert d == date(2026, 11, 25)
    assert {b.key for b in bins} == {"food_garden", "recycling"}
