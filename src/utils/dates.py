# Shared date-dimension helpers for Step 3. The fact grain across every
# source is weekly, anchored to Sunday (matching Google Trends' own "Week"
# column, e.g. 2023-01-01 is a Sunday) — these helpers keep that grain
# consistent everywhere a raw timestamp gets turned into a date_id.

from datetime import date, timedelta

import pandas as pd

MIN_DATE = date(2023, 1, 1)
MAX_DATE = date(2026, 12, 31)


# Step 1: snap any date to the Monday-Sunday week it falls in, returning the
# Sunday. weekday() gives Mon=0..Sun=6, so (weekday + 1) % 7 counts how many
# days back to the most recent Sunday (Sunday itself -> 0 days back).
def to_week_start(a_date):

    days_since_sunday = (a_date.weekday() + 1) % 7

    return a_date - timedelta(days=days_since_sunday)


# Step 2: turn a date into the dimension's surrogate key. YYYYMMDD as an int
# (e.g. 2023-01-01 -> 20230101) sorts and joins like a normal integer key
# while staying human-readable when you eyeball the fact tables.
def date_id_for(a_date):

    return int(a_date.strftime("%Y%m%d"))


# Step 3: generate one row per week and attach the calendar attributes fact
# tables will group/filter by, so no fact table needs its own date math.
def build_date_dimension(start=MIN_DATE, end=MAX_DATE):

    # 3a. Anchor the range to a Sunday so every week is a full 7-day bucket,
    # even if `start` itself lands mid-week.
    first_sunday = to_week_start(start)

    # 3b. Walk forward 7 days at a time, collecting every week start up to
    # `end`, to cover the whole project window (2023-2026) with no gaps.
    weeks = []
    current = first_sunday

    while current <= end:
        weeks.append(current)
        current = current + timedelta(days=7)

    # 3c. Derive month/quarter/year per week for easy grouping later (e.g.
    # "interest by quarter") without recomputing it in every query.
    return pd.DataFrame({
        "date_id": [date_id_for(week) for week in weeks],
        "date": weeks,
        "month": [week.month for week in weeks],
        "quarter": [(week.month - 1) // 3 + 1 for week in weeks],
        "year": [week.year for week in weeks],
    })
