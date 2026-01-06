from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import random
import json

from utils.corpora import ENG_AREAS, PRODUCT_AREAS, MARKETING_CAMPAIGNS, OPS_INITIATIVES
from utils.dates import (
    adjust_to_weekday,
    completion_timestamp,
    due_date_distribution,
    iso,
    now_utc,
    random_workday_datetime,
    updated_timestamp,
    window_last_days,
)
from utils.ids import gid
from utils.randomness import build_rng
from utils.db import bulk_insert
from utils.llm_groq import build_groq_from_env, GroqText


@dataclass(frozen=True)
class TasksContext:
    task_ids: list[str]
    subtask_ids: list[str]


def _pick_creator(
    rng: random.Random,
    users_by_team: dict[str, list[str]],
    team_id: str,
    user_role: dict[str, str],
    all_user_ids: list[str],
) -> str:
    pool = users_by_team.get(team_id, []) or all_user_ids
    # Bias creators toward managers/directors for enterprise workflows.
    if rng.random() < 0.60:
        mgrs = [uid for uid in pool if user_role.get(uid) in {"manager", "director", "executive"}]
        if mgrs:
            return rng.choice(mgrs)
    return rng.choice(pool)


def _pick_assignee(
    rng: random.Random,
    users_by_team: dict[str, list[str]],
    team_id: str,
    all_user_ids: list[str],
    load: dict[str, int],
) -> str | None:
    # ~15% unassigned.
    if rng.random() < 0.15:
        return None
    pool = users_by_team.get(team_id, [])
    if not pool:
        pool = all_user_ids
    if not pool:
        return None

    # Workload-aware selection via "power of 3" sampling.
    k = 3 if len(pool) >= 3 else len(pool)
    candidates = rng.sample(pool, k=k)
    chosen = min(candidates, key=lambda uid: load.get(uid, 0))
    load[chosen] = load.get(chosen, 0) + 1
    return chosen


def _task_name_heuristic(rng: random.Random, project_type: str) -> str:
    if project_type in {"sprint", "bug_triage"}:
        area = rng.choice(ENG_AREAS)
        verb = rng.choice(["Fix", "Improve", "Refactor", "Add", "Remove", "Investigate", "Harden", "Optimize"])
        obj = rng.choice(
            [
                "token refresh",
                "billing invoice export",
                "search indexing",
                "notifications retry logic",
                "permission checks",
                "API rate limit handling",
                "mobile deeplinks",
                "dashboard query performance",
            ]
        )
        detail = rng.choice(["edge cases", "time zones", "idempotency", "null handling", "pagination", "audit logging"])
        return f"{area}: {verb} {obj} ({detail})"

    if project_type == "product_roadmap":
        area = rng.choice(PRODUCT_AREAS)
        deliverable = rng.choice(["PRD", "Beta plan", "Launch checklist", "Pricing proposal", "Stakeholder review"])
        return f"{area}: {deliverable}"

    if project_type in {"marketing_campaign", "content_calendar"}:
        camp = rng.choice(MARKETING_CAMPAIGNS)
        deliverable = rng.choice(["Landing page", "Email sequence", "Webinar deck", "Ad creative", "Blog post", "Case study"])
        return f"{camp} - {deliverable}"

    if project_type in {"ops_initiative", "sales_enablement"}:
        ini = rng.choice(OPS_INITIATIVES)
        deliverable = rng.choice(["Runbook update", "Audit evidence", "Process doc", "Workflow automation", "Stakeholder sign-off"])
        return f"{ini}: {deliverable}"

    return f"Task {rng.randint(1000, 9999)}"


def _task_description(rng: random.Random, project_type: str) -> str | None:
    r = rng.random()
    if r < 0.20:
        return None
    if r < 0.70:
        return rng.choice(
            [
                "Please align on scope and post updates in-thread.",
                "Capture requirements, edge cases, and rollout plan.",
                "Ensure this is tracked end-to-end with clear owners.",
                "Add relevant links and keep status updated.",
            ]
        )

    bullets = [
        "- Context:",
        "- Goals:",
        "- Out of scope:",
        "- Rollout / risks:",
        "- Links:",
    ]
    return "\n".join(bullets)


def _maybe_llm_enrich_text(
    cfg,
    groq: GroqText,
    base_name: str,
    base_desc: str | None,
    project_name: str,
) -> tuple[str, str | None]:
    if not cfg.use_llm_text or not groq.enabled:
        return base_name, base_desc

    system = "You generate realistic Asana task titles and descriptions for an enterprise B2B SaaS company. Keep it concise and realistic."
    user = (
        f"Project: {project_name}\n"
        f"Base task title: {base_name}\n\n"
        "Return JSON with keys: title, description.\n"
        "Constraints:\n"
        "- Title: 4-12 words, no trailing period\n"
        "- Description: either empty, 1-3 sentences, or short bullets\n"
        "- Avoid generic placeholders like 'Task 1'\n"
    )

    try:
        text = groq.complete(system=system, user=user, temperature=0.7, max_tokens=250)
    except Exception:
        return base_name, base_desc

    try:
        payload = json.loads(text)
        title = str(payload.get("title") or base_name).strip()
        desc = payload.get("description")
        if desc is not None:
            desc = str(desc).strip()
            if desc == "":
                desc = None
        return title, desc
    except Exception:
        return base_name, base_desc


def _value_for_custom_field(rng: random.Random, cf) -> tuple[str | None, float | None, str | None]:
    # Returns (value_text, value_number, value_enum)
    if cf.field_type == "enum":
        if not cf.enum_options_json:
            return None, None, None
        try:
            options = json.loads(cf.enum_options_json)
        except Exception:
            options = []
        if not options:
            return None, None, None
        return None, None, str(rng.choice(options))

    if cf.field_type == "number":
        lname = cf.name.lower()
        if "story" in lname:
            return None, float(rng.choice([0.5, 1, 2, 3, 5, 8, 13])), None
        if "effort" in lname or "hour" in lname:
            return None, round(rng.lognormvariate(1.1, 0.7), 1), None
        if "confidence" in lname:
            return None, round(rng.uniform(0.3, 0.95), 2), None
        return None, round(rng.uniform(1, 10), 1), None

    # text
    lname = cf.name.lower()
    if "release" in lname:
        return rng.choice(["R-2026.02", "R-2026.03", "R-2026.04", "TBD", "Post-launch"]), None, None
    if "owner" in lname:
        return rng.choice(["Platform", "Growth", "Enterprise", "Security", "GTM Ops"]), None, None
    return rng.choice(["TBD", "" if rng.random() < 0.5 else "Follow up"]), None, None


def generate_tasks_and_subtasks(
    conn,
    cfg,
    org,
    teams,
    users,
    projects,
    sections,
    tags,
    custom_fields_ctx,
) -> TasksContext:
    rng = build_rng(cfg.seed + 47)
    tw = window_last_days(cfg.history_days, end=now_utc())

    groq = build_groq_from_env()

    # Build team->users mapping from actual team_memberships.
    team_to_users: dict[str, list[str]] = {t.team_id: [] for t in teams}
    cur = conn.execute("SELECT team_id, user_id FROM team_memberships WHERE left_at IS NULL")
    for team_id, user_id in cur.fetchall():
        team_to_users.setdefault(team_id, []).append(user_id)

    all_user_ids = [u.user_id for u in users]
    user_role = {u.user_id: u.role for u in users}
    load: dict[str, int] = {}

    # Map custom_field_id -> definition for correct typing.
    cf_by_id = {cf.custom_field_id: cf for cf in custom_fields_ctx.fields}

    # Sections by project.
    proj_to_sections: dict[str, list[str]] = {}
    for s in sections:
        proj_to_sections.setdefault(s.project_id, []).append(s.section_id)

    # Tags pool.
    tag_ids = [t.tag_id for t in tags]

    task_rows = []
    subtask_rows = []
    task_tag_rows = []
    cf_value_rows = []

    task_ids: list[str] = []
    subtask_ids: list[str] = []

    for p in projects:
        sec_ids = proj_to_sections.get(p.project_id, [])
        if not sec_ids:
            continue

        # Project task volume: log-normal around avg.
        n_tasks = max(10, int(rng.lognormvariate(5.2, 0.35)))
        # scale toward configured average
        n_tasks = int(0.6 * n_tasks + 0.4 * cfg.avg_tasks_per_project)
        n_tasks = max(40, min(n_tasks, 900))

        # Completion baseline varies by project type.
        if p.project_type == "sprint":
            completion_rate = rng.uniform(0.70, 0.85)
        elif p.project_type == "bug_triage":
            completion_rate = rng.uniform(0.60, 0.75)
        elif p.project_type in {"marketing_campaign", "sales_enablement"}:
            completion_rate = rng.uniform(0.55, 0.75)
        elif p.project_type == "ops_initiative":
            completion_rate = rng.uniform(0.45, 0.65)
        else:
            completion_rate = rng.uniform(0.40, 0.60)

        for _ in range(n_tasks):
            task_id = gid()
            section_id = rng.choice(sec_ids)

            creator = _pick_creator(rng, team_to_users, p.owner_team_id, user_role, all_user_ids)
            assignee = _pick_assignee(rng, team_to_users, p.owner_team_id, all_user_ids, load)

            created_at_dt = random_workday_datetime(rng, tw)
            updated_at_dt = updated_timestamp(rng, created_at_dt, tw)

            created_date = created_at_dt.date()
            if p.project_type == "sprint":
                due = (
                    adjust_to_weekday(created_date + timedelta(days=rng.randint(7, 14)), rng)
                    if rng.random() < 0.92
                    else None
                )
            else:
                due = due_date_distribution(rng, created_date)
            if due is not None:
                due = adjust_to_weekday(due, rng)

            # Start date sometimes.
            start_date = None
            if rng.random() < 0.35:
                start_date = created_date

            # Completion probability increases with age.
            age_days = (tw.end - created_at_dt).days
            age_boost = min(0.20, max(0.0, (age_days - 7) / 120.0))
            completed = 1 if rng.random() < min(0.98, completion_rate + age_boost) else 0

            completed_at = None
            if completed:
                completed_at = completion_timestamp(rng, created_at_dt, tw)

            base_name = _task_name_heuristic(rng, p.project_type)
            base_desc = _task_description(rng, p.project_type)
            name, desc = _maybe_llm_enrich_text(cfg, groq, base_name, base_desc, p.name)

            task_rows.append(
                (
                    task_id,
                    p.project_id,
                    section_id,
                    name,
                    desc,
                    creator,
                    assignee,
                    iso(created_at_dt),
                    iso(updated_at_dt),
                    iso(start_date),
                    iso(due),
                    completed,
                    iso(completed_at) if completed_at else None,
                )
            )
            task_ids.append(task_id)

            # Tags: most tasks have 0-2.
            if rng.random() < 0.55:
                for _ in range(rng.choices([1, 2, 3], weights=[0.65, 0.25, 0.10], k=1)[0]):
                    tag_id = rng.choice(tag_ids)
                    task_tag_rows.append((task_id, None, tag_id, iso(created_at_dt)))

            # Custom field values per project.
            cf_ids = custom_fields_ctx.project_to_fields.get(p.project_id, [])
            for cf_id in cf_ids:
                # Some values left blank.
                if rng.random() < 0.12:
                    continue

                cf = cf_by_id.get(cf_id)
                if cf is None:
                    continue

                value_text, value_number, value_enum = _value_for_custom_field(rng, cf)

                # Introduce sparsity and noise: some tasks keep only status filled.
                if cf.name != "Status" and rng.random() < 0.20:
                    continue

                # Avoid storing empty strings.
                if value_text is not None and value_text.strip() == "":
                    value_text = None

                if value_text is None and value_number is None and value_enum is None:
                    continue

                cf_value_rows.append(
                    (gid(), cf_id, task_id, None, value_text, value_number, value_enum, iso(created_at_dt))
                )

            # Subtasks: 35% of tasks have subtasks; 1-5 each.
            if rng.random() < 0.35:
                n_sub = rng.choices([1, 2, 3, 4, 5], weights=[0.35, 0.30, 0.20, 0.10, 0.05], k=1)[0]
                for _ in range(n_sub):
                    sid = gid()
                    sub_name = rng.choice(
                        [
                            "Write test cases",
                            "Update documentation",
                            "Add monitoring",
                            "QA verification",
                            "Create rollout plan",
                            "Stakeholder review",
                            "Fix linting / formatting",
                            "Backfill data",
                        ]
                    )
                    sub_desc = None if rng.random() < 0.65 else "Keep this small and link relevant PRs."
                    sub_created_at = updated_at_dt
                    sub_updated_at = updated_timestamp(rng, sub_created_at, tw)

                    sub_due = None
                    if due is not None and rng.random() < 0.65:
                        sub_due = due

                    sub_completed = 1 if completed and rng.random() < 0.85 else (1 if rng.random() < completion_rate * 0.6 else 0)
                    sub_completed_at = None
                    if sub_completed:
                        sub_completed_at = completion_timestamp(rng, sub_created_at, tw)

                    sub_assignee = assignee if rng.random() < 0.70 else _pick_assignee(
                        rng, team_to_users, p.owner_team_id, all_user_ids, load
                    )

                    subtask_rows.append(
                        (
                            sid,
                            task_id,
                            sub_name,
                            sub_desc,
                            creator,
                            sub_assignee,
                            iso(sub_created_at),
                            iso(sub_updated_at),
                            iso(sub_due),
                            sub_completed,
                            iso(sub_completed_at) if sub_completed_at else None,
                        )
                    )
                    subtask_ids.append(sid)

                    if rng.random() < 0.35:
                        tag_id = rng.choice(tag_ids)
                        task_tag_rows.append((None, sid, tag_id, iso(sub_created_at)))

    bulk_insert(
        conn,
        "tasks",
        [
            "task_id",
            "project_id",
            "section_id",
            "name",
            "description",
            "creator_user_id",
            "assignee_user_id",
            "created_at",
            "updated_at",
            "start_date",
            "due_date",
            "completed",
            "completed_at",
        ],
        task_rows,
        chunk_size=8000,
    )

    bulk_insert(
        conn,
        "subtasks",
        [
            "subtask_id",
            "parent_task_id",
            "name",
            "description",
            "creator_user_id",
            "assignee_user_id",
            "created_at",
            "updated_at",
            "due_date",
            "completed",
            "completed_at",
        ],
        subtask_rows,
        chunk_size=8000,
    )

    bulk_insert(
        conn,
        "task_tags",
        ["task_id", "subtask_id", "tag_id", "added_at"],
        task_tag_rows,
        chunk_size=10000,
    )

    bulk_insert(
        conn,
        "custom_field_values",
        [
            "custom_field_value_id",
            "custom_field_id",
            "task_id",
            "subtask_id",
            "value_text",
            "value_number",
            "value_enum",
            "created_at",
        ],
        cf_value_rows,
        chunk_size=10000,
    )

    return TasksContext(task_ids=task_ids, subtask_ids=subtask_ids)
