from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import random

from utils.corpora import (
    ENG_AREAS,
    PRODUCT_AREAS,
    MARKETING_CAMPAIGNS,
    OPS_INITIATIVES,
)
from utils.dates import iso, now_utc, window_last_days, random_workday_datetime
from utils.ids import gid
from utils.randomness import build_rng
from utils.db import bulk_insert


@dataclass(frozen=True)
class Project:
    project_id: str
    organization_id: str
    owner_team_id: str
    name: str
    project_type: str
    privacy: str
    status: str
    start_date: str | None
    due_date: str | None
    created_at: str
    archived_at: str | None
    description: str | None


def _project_type_for_team(rng: random.Random, team) -> str:
    if team.team_type == "technical":
        return rng.choices(
            ["sprint", "bug_triage", "product_roadmap", "ops_initiative"],
            weights=[0.55, 0.25, 0.15, 0.05],
            k=1,
        )[0]
    if team.team_type == "go_to_market":
        return rng.choices(
            ["marketing_campaign", "content_calendar", "sales_enablement", "ops_initiative"],
            weights=[0.45, 0.25, 0.20, 0.10],
            k=1,
        )[0]
    if team.team_type == "business_ops":
        return rng.choices(
            ["ops_initiative", "content_calendar", "sales_enablement"],
            weights=[0.65, 0.20, 0.15],
            k=1,
        )[0]
    return rng.choice(["ops_initiative", "product_roadmap", "marketing_campaign"])


def _project_name(rng: random.Random, ptype: str) -> str:
    if ptype == "sprint":
        area = rng.choice(ENG_AREAS)
        sprint = rng.randint(18, 38)
        year = rng.choice([2025, 2026])
        return f"{area} Sprint {year}-W{sprint:02d}"
    if ptype == "bug_triage":
        area = rng.choice(ENG_AREAS)
        return f"{area} Bug Triage & Fixes"
    if ptype == "product_roadmap":
        area = rng.choice(PRODUCT_AREAS)
        q = rng.choice(["Q1", "Q2", "Q3", "Q4"])
        year = rng.choice([2025, 2026])
        return f"{area} Roadmap {q} {year}"
    if ptype == "marketing_campaign":
        camp = rng.choice(MARKETING_CAMPAIGNS)
        return f"{camp} Campaign"
    if ptype == "content_calendar":
        q = rng.choice(["Q1", "Q2", "Q3", "Q4"])
        year = rng.choice([2025, 2026])
        return f"Content Calendar {q} {year}"
    if ptype == "sales_enablement":
        q = rng.choice(["Q1", "Q2", "Q3", "Q4"])
        year = rng.choice([2025, 2026])
        return f"Sales Enablement {q} {year}"
    if ptype == "ops_initiative":
        return rng.choice(OPS_INITIATIVES)
    return f"Project {rng.randint(100, 999)}"


def generate_projects(conn, cfg, org, teams, users) -> list[Project]:
    rng = build_rng(cfg.seed + 37)
    tw = window_last_days(cfg.history_days, end=now_utc())

    # Prefer managers/directors as project owners (creator-like).
    owner_users = [u for u in users if u.role in {"manager", "director", "executive"}]

    projects: list[Project] = []
    used_names: set[str] = set()
    for _ in range(cfg.projects_count):
        team = rng.choice(teams)
        ptype = _project_type_for_team(rng, team)
        name = _project_name(rng, ptype)
        if name in used_names:
            name = f"{name} ({rng.randint(2, 9)})"
        used_names.add(name)

        created_at_dt = random_workday_datetime(rng, tw)

        # Dates: sprints 2 weeks, campaigns 4-8 weeks, roadmaps 1-3 months, ops variable.
        start_date = created_at_dt.date() if rng.random() < 0.85 else None
        due_date = None
        if start_date is not None:
            if ptype == "sprint":
                due_date = start_date + timedelta(days=14)
            elif ptype == "bug_triage":
                due_date = start_date + timedelta(days=rng.randint(21, 45))
            elif ptype == "product_roadmap":
                due_date = start_date + timedelta(days=rng.randint(45, 120))
            elif ptype == "marketing_campaign":
                due_date = start_date + timedelta(days=rng.randint(28, 70))
            elif ptype == "content_calendar":
                due_date = start_date + timedelta(days=rng.randint(60, 120))
            elif ptype == "sales_enablement":
                due_date = start_date + timedelta(days=rng.randint(45, 90))
            elif ptype == "ops_initiative":
                due_date = start_date + timedelta(days=rng.randint(30, 150))

        privacy = rng.choices(["public", "private"], weights=[0.86, 0.14], k=1)[0]
        status = rng.choices(["active", "on_hold", "completed"], weights=[0.76, 0.07, 0.17], k=1)[0]

        archived_at = None
        if status == "completed" and rng.random() < 0.55:
            archived_at = iso(created_at_dt + timedelta(days=rng.randint(30, min(cfg.history_days, 180))))

        description = None
        if rng.random() < 0.65:
            description = rng.choice(
                [
                    "Tracking deliverables, owners, and dates for this workstream.",
                    "Weekly plan for execution, review, and release coordination.",
                    "Cross-functional project to align stakeholders and ship outcomes.",
                    "Central place for tasks, approvals, and launch readiness.",
                ]
            )

        p = Project(
            project_id=gid(),
            organization_id=org.organization_id,
            owner_team_id=team.team_id,
            name=name,
            project_type=ptype,
            privacy=privacy,
            status=status,
            start_date=iso(start_date),
            due_date=iso(due_date),
            created_at=iso(created_at_dt),
            archived_at=archived_at,
            description=description,
        )
        projects.append(p)

    bulk_insert(
        conn,
        "projects",
        [
            "project_id",
            "organization_id",
            "owner_team_id",
            "name",
            "project_type",
            "privacy",
            "status",
            "start_date",
            "due_date",
            "created_at",
            "archived_at",
            "description",
        ],
        [
            (
                p.project_id,
                p.organization_id,
                p.owner_team_id,
                p.name,
                p.project_type,
                p.privacy,
                p.status,
                p.start_date,
                p.due_date,
                p.created_at,
                p.archived_at,
                p.description,
            )
            for p in projects
        ],
    )
    return projects
