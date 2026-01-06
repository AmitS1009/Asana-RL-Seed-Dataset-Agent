from __future__ import annotations

from dataclasses import dataclass
import random

from utils.corpora import TAG_COLORS
from utils.dates import iso, now_utc
from utils.ids import gid
from utils.randomness import build_rng
from utils.db import bulk_insert


@dataclass(frozen=True)
class Tag:
    tag_id: str
    organization_id: str
    name: str
    color: str
    created_at: str


def generate_tags(conn, cfg, org) -> list[Tag]:
    rng = build_rng(cfg.seed + 41)
    created_at = iso(now_utc())

    names = [
        "urgent",
        "blocked",
        "needs-review",
        "customer-reported",
        "tech-debt",
        "security",
        "compliance",
        "performance",
        "feature-flag",
        "migration",
        "experiment",
        "launch",
        "analytics",
        "partner",
        "copy-review",
        "design-needed",
        "legal-review",
        "stakeholder-align",
        "ops",
        "automation",
    ]

    # Expand with plausible topical tags.
    while len(names) < 90:
        names.append(rng.choice(["q1", "q2", "q3", "q4"]) + "-" + rng.choice(["plan", "okrs", "execution", "launch"]))

    # De-dupe while preserving order.
    seen: set[str] = set()
    unique_names: list[str] = []
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        unique_names.append(n)
    names = unique_names

    tags = [
        Tag(tag_id=gid(), organization_id=org.organization_id, name=n, color=rng.choice(TAG_COLORS), created_at=created_at)
        for n in names
    ]

    bulk_insert(
        conn,
        "tags",
        ["tag_id", "organization_id", "name", "color", "created_at"],
        [(t.tag_id, t.organization_id, t.name, t.color, t.created_at) for t in tags],
    )
    return tags
