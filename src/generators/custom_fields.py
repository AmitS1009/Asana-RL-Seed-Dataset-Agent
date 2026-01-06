from __future__ import annotations

from dataclasses import dataclass
import json
import random

from utils.corpora import (
    PRIORITY_ENUM,
    STATUS_ENUM,
    CUSTOMER_IMPACT_ENUM,
    CHANNEL_ENUM,
    REGION_ENUM,
)
from utils.dates import iso, now_utc
from utils.ids import gid
from utils.randomness import build_rng
from utils.db import bulk_insert


@dataclass(frozen=True)
class CustomField:
    custom_field_id: str
    organization_id: str
    name: str
    field_type: str
    enum_options_json: str | None
    created_at: str


@dataclass(frozen=True)
class CustomFieldsContext:
    fields: list[CustomField]
    project_to_fields: dict[str, list[str]]


def generate_custom_fields(conn, cfg, org, projects) -> CustomFieldsContext:
    rng = build_rng(cfg.seed + 43)
    created_at = iso(now_utc())

    fields: list[CustomField] = []

    def add_enum(name: str, options: list[str]) -> CustomField:
        cf = CustomField(
            custom_field_id=gid(),
            organization_id=org.organization_id,
            name=name,
            field_type="enum",
            enum_options_json=json.dumps(options),
            created_at=created_at,
        )
        fields.append(cf)
        return cf

    def add_number(name: str) -> CustomField:
        cf = CustomField(
            custom_field_id=gid(),
            organization_id=org.organization_id,
            name=name,
            field_type="number",
            enum_options_json=None,
            created_at=created_at,
        )
        fields.append(cf)
        return cf

    def add_text(name: str) -> CustomField:
        cf = CustomField(
            custom_field_id=gid(),
            organization_id=org.organization_id,
            name=name,
            field_type="text",
            enum_options_json=None,
            created_at=created_at,
        )
        fields.append(cf)
        return cf

    cf_priority = add_enum("Priority", PRIORITY_ENUM)
    cf_status = add_enum("Status", STATUS_ENUM)
    cf_customer_impact = add_enum("Customer Impact", CUSTOMER_IMPACT_ENUM)
    cf_channel = add_enum("Channel", CHANNEL_ENUM)
    cf_region = add_enum("Region", REGION_ENUM)

    cf_effort = add_number("Effort (hours)")
    cf_story_points = add_number("Story Points")
    cf_confidence = add_number("Confidence")

    cf_release = add_text("Target Release")
    cf_owner_group = add_text("Owner Group")

    bulk_insert(
        conn,
        "custom_field_definitions",
        ["custom_field_id", "organization_id", "name", "field_type", "enum_options_json", "created_at"],
        [(f.custom_field_id, f.organization_id, f.name, f.field_type, f.enum_options_json, f.created_at) for f in fields],
    )

    # Attach per-project subsets.
    project_to_fields: dict[str, list[str]] = {}
    project_custom_rows = []
    for p in projects:
        chosen: list[str] = [cf_status.custom_field_id]

        if p.project_type in {"sprint", "bug_triage"}:
            chosen += [cf_priority.custom_field_id, cf_story_points.custom_field_id, cf_effort.custom_field_id]
        elif p.project_type in {"product_roadmap"}:
            chosen += [cf_priority.custom_field_id, cf_confidence.custom_field_id, cf_owner_group.custom_field_id, cf_release.custom_field_id]
        elif p.project_type in {"marketing_campaign", "content_calendar"}:
            chosen += [cf_channel.custom_field_id, cf_region.custom_field_id]
        elif p.project_type in {"ops_initiative", "sales_enablement"}:
            chosen += [cf_priority.custom_field_id, cf_owner_group.custom_field_id]

        # Customer impact is common for roadmap + bugs.
        if p.project_type in {"bug_triage", "product_roadmap"} and rng.random() < 0.75:
            chosen += [cf_customer_impact.custom_field_id]

        # De-dupe.
        chosen = list(dict.fromkeys(chosen))
        project_to_fields[p.project_id] = chosen

        for cf_id in chosen:
            is_required = 1 if (cf_id == cf_status.custom_field_id and rng.random() < 0.35) else 0
            project_custom_rows.append((p.project_id, cf_id, is_required, created_at))

    bulk_insert(
        conn,
        "project_custom_fields",
        ["project_id", "custom_field_id", "is_required", "created_at"],
        project_custom_rows,
    )

    return CustomFieldsContext(fields=fields, project_to_fields=project_to_fields)
