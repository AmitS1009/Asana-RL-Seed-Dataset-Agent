from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    details: dict[str, Any]


def _q(conn: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    cur = conn.execute(sql, params)
    return cur.fetchone()[0]


def _table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "organizations",
        "teams",
        "users",
        "team_memberships",
        "projects",
        "sections",
        "tasks",
        "subtasks",
        "comments",
        "tags",
        "task_tags",
        "custom_field_definitions",
        "project_custom_fields",
        "custom_field_values",
        "attachments",
    ]
    out: dict[str, int] = {}
    for t in tables:
        out[t] = int(_q(conn, f"SELECT COUNT(*) FROM {t}"))
    return out


def run_sanity_checks(db_path: str) -> dict[str, Any]:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        counts = _table_counts(conn)

        results: list[CheckResult] = []

        # Relational integrity quick probes.
        bad_task_section = int(
            _q(
                conn,
                """
                SELECT COUNT(*)
                FROM tasks t
                LEFT JOIN sections s ON s.section_id = t.section_id
                WHERE s.section_id IS NULL
                """,
            )
        )
        results.append(
            CheckResult(
                name="tasks_have_valid_sections",
                ok=bad_task_section == 0,
                details={"invalid_task_section_rows": bad_task_section},
            )
        )

        bad_subtask_parent = int(
            _q(
                conn,
                """
                SELECT COUNT(*)
                FROM subtasks st
                LEFT JOIN tasks t ON t.task_id = st.parent_task_id
                WHERE t.task_id IS NULL
                """,
            )
        )
        results.append(
            CheckResult(
                name="subtasks_have_valid_parent",
                ok=bad_subtask_parent == 0,
                details={"invalid_subtask_parent_rows": bad_subtask_parent},
            )
        )

        # Temporal consistency: completed_at should be non-null iff completed=1.
        completed_mismatch = int(
            _q(
                conn,
                """
                SELECT COUNT(*)
                FROM tasks
                WHERE (completed = 1 AND completed_at IS NULL)
                   OR (completed = 0 AND completed_at IS NOT NULL)
                """,
            )
        )
        results.append(
            CheckResult(
                name="task_completed_fields_consistent",
                ok=completed_mismatch == 0,
                details={"mismatch_rows": completed_mismatch},
            )
        )

        # Distribution checks.
        unassigned = int(_q(conn, "SELECT COUNT(*) FROM tasks WHERE assignee_user_id IS NULL"))
        total_tasks = counts.get("tasks", 0) or 1
        unassigned_pct = unassigned / total_tasks

        results.append(
            CheckResult(
                name="unassigned_rate_reasonable",
                ok=0.08 <= unassigned_pct <= 0.25,
                details={"unassigned": unassigned, "total_tasks": total_tasks, "unassigned_pct": unassigned_pct},
            )
        )

        no_due = int(_q(conn, "SELECT COUNT(*) FROM tasks WHERE due_date IS NULL"))
        no_due_pct = no_due / total_tasks
        results.append(
            CheckResult(
                name="no_due_date_rate_reasonable",
                ok=0.05 <= no_due_pct <= 0.25,
                details={"no_due": no_due, "total_tasks": total_tasks, "no_due_pct": no_due_pct},
            )
        )

        overdue = int(_q(conn, "SELECT COUNT(*) FROM tasks WHERE due_date IS NOT NULL AND due_date < date('now') AND completed = 0"))
        overdue_pct = overdue / total_tasks
        results.append(
            CheckResult(
                name="overdue_open_tasks_exist",
                ok=overdue > 0,
                details={"overdue_open": overdue, "overdue_open_pct": overdue_pct},
            )
        )

        # Custom field value coverage.
        cfv_total = counts.get("custom_field_values", 0) or 1
        cfv_per_task = cfv_total / total_tasks
        results.append(
            CheckResult(
                name="custom_fields_present",
                ok=cfv_total > 0 and cfv_per_task >= 0.6,
                details={"custom_field_values": cfv_total, "tasks": total_tasks, "cfv_per_task": cfv_per_task},
            )
        )

        # Comments density.
        comments_total = counts.get("comments", 0) or 0
        comments_per_task = comments_total / total_tasks
        results.append(
            CheckResult(
                name="comments_density_reasonable",
                ok=0.15 <= comments_per_task <= 1.5,
                details={"comments": comments_total, "tasks": total_tasks, "comments_per_task": comments_per_task},
            )
        )

        # Attachments density.
        attachments_total = counts.get("attachments", 0) or 0
        attachments_per_task = attachments_total / total_tasks
        results.append(
            CheckResult(
                name="attachments_density_reasonable",
                ok=0.01 <= attachments_per_task <= 0.20,
                details={"attachments": attachments_total, "tasks": total_tasks, "attachments_per_task": attachments_per_task},
            )
        )

        return {
            "counts": counts,
            "checks": [
                {"name": r.name, "ok": r.ok, "details": r.details}
                for r in results
            ],
        }
    finally:
        conn.close()


def main() -> None:
    import os

    db_path = os.getenv("DB_PATH", "output/asana_simulation.sqlite")
    report = run_sanity_checks(db_path)

    out_dir = Path("output")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sanity_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Print a compact summary.
    ok = all(c["ok"] for c in report["checks"])
    print(f"Sanity report written to {out_path}")
    print(f"All checks OK: {ok}")


if __name__ == "__main__":
    main()
