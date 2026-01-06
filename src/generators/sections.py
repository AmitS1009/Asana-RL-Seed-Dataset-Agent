from __future__ import annotations

from dataclasses import dataclass

from utils.randomness import build_rng

from utils.corpora import PROJECT_TEMPLATES
from utils.dates import iso, now_utc
from utils.ids import gid
from utils.db import bulk_insert


@dataclass(frozen=True)
class Section:
    section_id: str
    project_id: str
    name: str
    position: int
    created_at: str


def generate_sections(conn, cfg, projects) -> list[Section]:
    rng = build_rng(cfg.seed + 39)
    created_at = iso(now_utc())
    sections: list[Section] = []

    for p in projects:
        template = PROJECT_TEMPLATES.get(p.project_type, ["To Do", "In Progress", "Done"])
        for idx, name in enumerate(template):
            s = Section(section_id=gid(), project_id=p.project_id, name=name, position=idx, created_at=created_at)
            sections.append(s)

        # Some projects add extra sections.
        if p.project_type in {"marketing_campaign", "content_calendar", "ops_initiative", "product_roadmap"}:
            extra_candidates = ["Legal Review", "Design", "Blocked", "Stakeholder Review", "Waiting on Input"]
            n_extra = rng.choices([0, 1, 2], weights=[0.55, 0.35, 0.10], k=1)[0]
            extras = rng.sample(extra_candidates, k=n_extra) if n_extra > 0 else []
            for offset, e in enumerate(extras, start=0):
                sections.append(
                    Section(
                        section_id=gid(),
                        project_id=p.project_id,
                        name=e,
                        position=len(template) + offset,
                        created_at=created_at,
                    )
                )

    bulk_insert(
        conn,
        "sections",
        ["section_id", "project_id", "name", "position", "created_at"],
        [(s.section_id, s.project_id, s.name, s.position, s.created_at) for s in sections],
    )

    return sections
