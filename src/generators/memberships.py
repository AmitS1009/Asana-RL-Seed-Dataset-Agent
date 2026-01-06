from __future__ import annotations

from datetime import timedelta
import random

from utils.dates import iso, now_utc, window_last_days, random_workday_datetime
from utils.randomness import build_rng
from utils.db import bulk_insert


def generate_team_memberships(conn, cfg, teams, users) -> None:
    rng = build_rng(cfg.seed + 31)
    tw = window_last_days(cfg.history_days, end=now_utc())

    # Map department -> candidate teams based on prefix match.
    dept_to_teams: dict[str, list[str]] = {}
    for t in teams:
        prefix = t.name.split(" ")[0]
        dept_to_teams.setdefault(prefix, []).append(t.team_id)

    rows = []

    # Choose one team as primary by department, plus optional cross-functional membership.
    for u in users:
        if u.deactivated_at is not None and rng.random() < 0.70:
            # still might have historical membership
            pass

        candidate = dept_to_teams.get(u.department, [])
        if not candidate:
            candidate = [rng.choice(teams).team_id]

        primary_team_id = rng.choice(candidate)
        joined_at = random_workday_datetime(rng, tw)
        left_at = None
        if u.deactivated_at is not None and rng.random() < 0.60:
            left_at = u.deactivated_at

        is_admin = 1 if (u.role in {"manager", "director", "executive"} and rng.random() < 0.22) else 0
        rows.append((primary_team_id, u.user_id, is_admin, iso(joined_at), left_at))

        # Optional secondary membership.
        if rng.random() < 0.18:
            other_team = rng.choice(teams).team_id
            if other_team != primary_team_id:
                rows.append((other_team, u.user_id, 0, iso(joined_at + timedelta(days=rng.randint(1, 14))), left_at))

    bulk_insert(
        conn,
        "team_memberships",
        ["team_id", "user_id", "is_team_admin", "joined_at", "left_at"],
        rows,
    )
