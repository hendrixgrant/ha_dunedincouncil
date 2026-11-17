"""Pure-Python kerbside collection schedule logic for Dunedin City Council.

No Home Assistant imports here so it can be unit tested on its own.

How DCC's system works (as published by the council):
  * Green-lidded food scraps & garden bin: every week.
  * Red-lidded rubbish bin and blue glass bin: fortnightly, same week.
  * Yellow-lidded mixed recycling bin: fortnightly, the alternate week.
  * Tertiary (student) area: all bins every week, on Tuesdays.
  * No collection on Good Friday, Christmas Day or New Year's Day when they
    fall on a weekday; those bins are collected the following Saturday.

The council's GIS layer publishes the collection weekday and which fortnightly
week ("blue" or "yellow") the *current* week is. We anchor on that value each
time we fetch and alternate from there.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

BLUE = "blue"
YELLOW = "yellow"
WEEKLY = "weekly"

# Values seen in the GIS "CurrentWeek" field, mapped to the fortnightly week type.
WEEK_CODES = {"b": BLUE, "y": YELLOW}


@dataclass(frozen=True)
class BinDef:
    """A kerbside bin and the cadence it is collected on."""

    key: str
    name: str
    colour: str
    cadence: str  # WEEKLY, BLUE or YELLOW (which fortnightly week it goes out)
    icon: str


BINS: tuple[BinDef, ...] = (
    BinDef("food_garden", "Food scraps & garden", "green", WEEKLY, "mdi:leaf"),
    BinDef("rubbish", "Rubbish", "red", BLUE, "mdi:trash-can"),
    BinDef("glass", "Glass", "blue", BLUE, "mdi:bottle-wine"),
    BinDef("recycling", "Mixed recycling", "yellow", YELLOW, "mdi:recycle"),
)


def parse_week_type(code: str | None, swap: bool = False) -> str | None:
    """Turn the GIS CurrentWeek code into BLUE/YELLOW (or None if unrecognised)."""
    if not code:
        return None
    week_type = WEEK_CODES.get(str(code).strip().lower())
    if week_type is None:
        return None
    if swap:
        return YELLOW if week_type == BLUE else BLUE
    return week_type


def monday_of(day: date) -> date:
    """Monday of the ISO week containing ``day``."""
    return day - timedelta(days=day.weekday())


def easter_sunday(year: int) -> date:
    """Easter Sunday (anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def is_no_collection_day(day: date) -> bool:
    """True for the weekday holidays DCC doesn't collect on."""
    if day.weekday() >= 5:  # Sat/Sun: the rule only applies to weekdays
        return False
    if (day.month, day.day) in {(12, 25), (1, 1)}:
        return True
    return day == easter_sunday(day.year) - timedelta(days=2)  # Good Friday


def apply_holiday_shift(day: date) -> date:
    """Move a collection that falls on a no-collection day to the next Saturday."""
    if is_no_collection_day(day):
        return day + timedelta(days=5 - day.weekday())
    return day


def _week_type_for(day: date, anchor_monday: date, anchor_type: str) -> str:
    weeks_apart = (monday_of(day) - anchor_monday).days // 7
    if weeks_apart % 2 == 0:
        return anchor_type
    return YELLOW if anchor_type == BLUE else BLUE


def next_collection(
    today: date,
    weekday_number: int | None,
    cadence: str,
    anchor_monday: date,
    anchor_type: str | None,
    tertiary: bool = False,
) -> date | None:
    """Next collection date (today counts) for a bin.

    ``weekday_number`` is ISO style: 1 = Monday ... 7 = Sunday.
    Returns None if the property has no collection or the fortnightly week
    couldn't be determined.
    """
    if weekday_number is None or not 1 <= weekday_number <= 7:
        return None
    needs_anchor = cadence != WEEKLY and not tertiary
    if needs_anchor and anchor_type is None:
        return None

    this_monday = monday_of(today)
    for week in range(8):
        nominal = this_monday + timedelta(weeks=week, days=weekday_number - 1)
        actual = apply_holiday_shift(nominal)
        if actual < today:
            continue
        if not needs_anchor or _week_type_for(nominal, anchor_monday, anchor_type) == cadence:
            return actual
    return None


def next_collection_summary(
    today: date,
    weekday_number: int | None,
    anchor_monday: date,
    anchor_type: str | None,
    tertiary: bool = False,
) -> tuple[date, list[BinDef]] | None:
    """The soonest collection date and which bins go out on it."""
    dated = [
        (next_collection(today, weekday_number, b.cadence, anchor_monday, anchor_type, tertiary), b)
        for b in BINS
    ]
    dated = [(d, b) for d, b in dated if d is not None]
    if not dated:
        return None
    soonest = min(d for d, _ in dated)
    return soonest, [b for d, b in dated if d == soonest]
