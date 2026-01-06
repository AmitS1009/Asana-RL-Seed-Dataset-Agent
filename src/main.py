from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from utils.config import load_config
from utils import db

from generators.organization import generate_organization
from generators.teams import generate_teams
from generators.users import generate_users
from generators.memberships import generate_team_memberships
from generators.projects import generate_projects
from generators.sections import generate_sections
from generators.tags import generate_tags
from generators.custom_fields import generate_custom_fields
from generators.tasks import generate_tasks_and_subtasks
from generators.comments import generate_comments
from generators.attachments import generate_attachments


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    load_dotenv()
    cfg = load_config()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    db_path = Path(cfg.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_sql = _read_text(Path(__file__).resolve().parent.parent / "schema.sql")

    if db_path.exists():
        db_path.unlink()

    conn = db.connect(str(db_path))
    try:
        logging.info("Creating schema")
        db.execute_script(conn, schema_sql)

        logging.info("Generating organization")
        org = generate_organization(conn, cfg)

        logging.info("Generating teams")
        teams = generate_teams(conn, cfg, org)

        logging.info("Generating users")
        users = generate_users(conn, cfg, org, teams)

        logging.info("Generating team memberships")
        generate_team_memberships(conn, cfg, teams, users)

        logging.info("Generating projects")
        projects = generate_projects(conn, cfg, org, teams, users)

        logging.info("Generating sections")
        sections = generate_sections(conn, cfg, projects)

        logging.info("Generating tags")
        tags = generate_tags(conn, cfg, org)

        logging.info("Generating custom fields")
        custom_fields = generate_custom_fields(conn, cfg, org, projects)

        logging.info("Generating tasks + subtasks + task-tags + custom-field-values")
        tasks_ctx = generate_tasks_and_subtasks(
            conn,
            cfg,
            org,
            teams,
            users,
            projects,
            sections,
            tags,
            custom_fields,
        )

        logging.info("Generating comments")
        generate_comments(conn, cfg, users, tasks_ctx)

        logging.info("Generating attachments")
        generate_attachments(conn, cfg, users, tasks_ctx)

        conn.commit()
        logging.info("Done. DB written to %s", db_path)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
