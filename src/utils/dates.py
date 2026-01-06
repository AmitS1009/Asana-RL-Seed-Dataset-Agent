from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import math
import random


UTC = timezone.utc


@dataclass(frozen=True)
class TimeWindow:
    start: datetime
    end: datetime


def now_utc() -> datetime:
    return datetime.now(tz=UTC)


def window_last_days(days: int, end: datetime | None = None) -> TimeWindow:
    e = end or now_utc()
    return TimeWindow(start=e - timedelta(days=days), end=e)


def random_datetime(rng: random.Random, tw: TimeWindow) -> datetime:
    delta = (tw.end - tw.start).total_seconds()
    t = rng.random() * delta
    return tw.start + timedelta(seconds=t)


def random_workday_datetime(rng: random.Random, tw: TimeWindow) -> datetime:
    # Bias creation toward Mon-Wed and working hours.
    for _ in range(40):
        dt = random_datetime(rng, tw)
        weekday = dt.weekday()  # 0=Mon
        if weekday <= 2:
            p = 0.75
        elif weekday == 3:
            p = 0.55
        elif weekday == 4:
            p = 0.45
        else:
            p = 0.15
        if rng.random() > p:
            continue

        hour = dt.hour
        if 8 <= hour <= 19:
            return dt
    return random_datetime(rng, tw)


def iso(dt: datetime | date | None) -> str | None:
    if dt is None:
        return None
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.isoformat()
    return dt.astimezone(UTC).isoformat(timespec="seconds")


def clamp_dt(dt: datetime, tw: TimeWindow) -> datetime:
    if dt < tw.start:
        return tw.start
    if dt > tw.end:
        return tw.end
    return dt


def add_business_days(d: date, days: int) -> date:
    step = 1 if days >= 0 else -1
    remaining = abs(days)
    cur = d
    while remaining > 0:
        cur = cur + timedelta(days=step)
        if cur.weekday() < 5:
            remaining -= 1
    return cur


def adjust_to_weekday(d: date, rng: random.Random, prefer_weekday_prob: float = 0.85) -> date:
    if d.weekday() < 5:
        return d
    if rng.random() > prefer_weekday_prob:
        return d
    if d.weekday() == 5:
        return d + timedelta(days=2)
    return d + timedelta(days=1)


def due_date_distribution(rng: random.Random, created: date, horizon_days: int = 120) -> date | None:
    # 10% no due date.
    if rng.random() < 0.10:
        return None

    # 5% overdue.
    if rng.random() < 0.05:
        overdue_days = int(max(1, rng.lognormvariate(1.2, 0.6)))
        return created - timedelta(days=min(overdue_days, 30))

    r = rng.random()
    if r < 0.25:
        offset = rng.randint(1, 7)
    elif r < 0.65:
        offset = rng.randint(8, 30)
    elif r < 0.85:
        offset = rng.randint(31, 90)
    else:
        offset = rng.randint(91, horizon_days)
    return created + timedelta(days=offset)


def completion_timestamp(rng: random.Random, created_at: datetime, tw: TimeWindow) -> datetime:
    # Cycle-time: log-normal-ish days; clamp to now.
    days = max(0.15, rng.lognormvariate(1.35, 0.75))
    dt = created_at + timedelta(days=days)
    return clamp_dt(dt, tw)


def updated_timestamp(rng: random.Random, created_at: datetime, tw: TimeWindow) -> datetime:
    # Most tasks get a few updates; keep after creation.
    hours = max(0.1, rng.lognormvariate(2.2, 0.9))
    dt = created_at + timedelta(hours=hours)
    return clamp_dt(dt, tw)
