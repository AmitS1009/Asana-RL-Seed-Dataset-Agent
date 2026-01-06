from __future__ import annotations

from dataclasses import dataclass
import random

from utils.dates import iso, now_utc
from utils.ids import gid
from utils.randomness import build_rng
from utils.db import bulk_insert


@dataclass(frozen=True)
class Organization:
    organization_id: str
    name: str
    domain: str
    created_at: str


def generate_organization(conn, cfg) -> Organization:
    rng = build_rng(cfg.seed + 11)
    # Use a plausible B2B SaaS company name + verified domain.
    name = rng.choice(
        [
            "AsterCloud",
            "Northwind Labs",
            "BluePeak Software",
            "HelioWorks",
            "QuantaFlow",
            "NimbusForge",
        ]
    )
    domain = "astercloud.com" if name == "AsterCloud" else f"{name.lower().replace(' ', '')}.com"

    org = Organization(
        organization_id=gid(),
        name=name,
        domain=domain,
        created_at=iso(now_utc()),
    )

    bulk_insert(
        conn,
        "organizations",
        ["organization_id", "name", "domain", "created_at"],
        [(org.organization_id, org.name, org.domain, org.created_at)],
    )
    return org
