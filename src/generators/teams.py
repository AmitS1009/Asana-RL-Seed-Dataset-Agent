from __future__ import annotations

from dataclasses import dataclass
import random

from utils.corpora import DEPARTMENTS
from utils.dates import iso, now_utc
from utils.ids import gid
from utils.randomness import build_rng
from utils.db import bulk_insert


@dataclass(frozen=True)
class Team:
    team_id: str
    organization_id: str
    name: str
    team_type: str
    created_at: str


def _team_type_for_department(dept: str) -> str:
    if dept in {"Engineering", "QA", "Security", "IT", "Data"}:
        return "technical"
    if dept in {"Marketing", "Sales", "Customer Success", "RevOps"}:
        return "go_to_market"
    if dept in {"People", "Finance", "Legal", "Operations"}:
        return "business_ops"
    return "cross_functional"


def generate_teams(conn, cfg, org) -> list[Team]:
    rng = build_rng(cfg.seed + 17)

    # Team naming patterns common in enterprise Asana workspaces.
    base_names = {
        "Engineering": [
            "Platform Engineering",
            "Core Services",
            "Frontend Experience",
            "Mobile Engineering",
            "Infrastructure",
            "Integrations",
            "Data Platform",
        ],
        "Product": [
            "Product Management",
            "Growth Product",
            "Enterprise Product",
            "AI Product",
        ],
        "Design": ["Product Design", "Design Systems", "UX Research"],
        "QA": ["Quality Engineering", "Release Validation"],
        "Data": ["Analytics", "Data Science"],
        "Marketing": [
            "Demand Generation",
            "Content Marketing",
            "Product Marketing",
            "Brand & Creative",
            "Growth Marketing",
        ],
        "Sales": ["Enterprise Sales", "Mid-Market Sales", "Sales Development"],
        "Customer Success": ["Customer Success", "Solutions Engineering", "Support Operations"],
        "Operations": ["Business Operations", "Program Management Office"],
        "IT": ["IT Operations", "Corporate Systems"],
        "Security": ["Security", "GRC"],
        "People": ["People Operations", "Talent Acquisition"],
        "Finance": ["FP&A", "Accounting"],
        "Legal": ["Legal"],
        "RevOps": ["Revenue Operations"],
    }

    names: list[str] = []
    for dept in DEPARTMENTS:
        names.extend(base_names.get(dept, []))

    # Fill remaining with "pods" or "squads".
    while len(names) < cfg.teams_count:
        dept = rng.choice(DEPARTMENTS)
        suffix = rng.choice(["Pod", "Squad", "Team", "Group"]) 
        topic = rng.choice(
            [
                "Automation",
                "Enablement",
                "Ops",
                "Reporting",
                "Insights",
                "Tooling",
                "Compliance",
                "Partnerships",
                "Developer Experience",
            ]
        )
        names.append(f"{dept} {topic} {suffix}")

    names = names[: cfg.teams_count]

    teams: list[Team] = []
    created_at = iso(now_utc())
    for n in names:
        # Infer department from name prefix when possible.
        dept_guess = n.split(" ")[0]
        dept = dept_guess if dept_guess in DEPARTMENTS else rng.choice(DEPARTMENTS)
        t = Team(
            team_id=gid(),
            organization_id=org.organization_id,
            name=n,
            team_type=_team_type_for_department(dept),
            created_at=created_at,
        )
        teams.append(t)

    bulk_insert(
        conn,
        "teams",
        ["team_id", "organization_id", "name", "team_type", "created_at"],
        [(t.team_id, t.organization_id, t.name, t.team_type, t.created_at) for t in teams],
    )
    return teams
