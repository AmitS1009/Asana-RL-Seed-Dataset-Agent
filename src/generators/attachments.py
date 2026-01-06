from __future__ import annotations

import random

from utils.corpora import FILE_TYPES
from utils.dates import iso, now_utc, window_last_days, random_workday_datetime
from utils.ids import gid
from utils.randomness import build_rng
from utils.db import bulk_insert


def generate_attachments(conn, cfg, users, tasks_ctx) -> None:
    rng = build_rng(cfg.seed + 61)
    tw = window_last_days(cfg.history_days, end=now_utc())

    user_ids = [u.user_id for u in users]

    rows = []

    # Attachments are sparse: ~6% tasks; ~3% subtasks.
    for tid in tasks_ctx.task_ids:
        if rng.random() < 0.06:
            uploader = rng.choice(user_ids)
            created_at = random_workday_datetime(rng, tw)
            ext = rng.choice(FILE_TYPES)
            file_name = rng.choice(
                [
                    f"spec.{ext}",
                    f"requirements.{ext}",
                    f"screenshots.{ext}",
                    f"launch-checklist.{ext}",
                    f"report.{ext}",
                    f"notes.{ext}",
                ]
            )
            size = int(rng.lognormvariate(10.0, 0.8))
            url = None
            rows.append((gid(), tid, None, uploader, file_name, ext, size, iso(created_at), url))

    for sid in tasks_ctx.subtask_ids:
        if rng.random() < 0.03:
            uploader = rng.choice(user_ids)
            created_at = random_workday_datetime(rng, tw)
            ext = rng.choice(FILE_TYPES)
            file_name = rng.choice([f"evidence.{ext}", f"artifact.{ext}", f"debug.{ext}"])
            size = int(rng.lognormvariate(9.6, 0.9))
            url = None
            rows.append((gid(), None, sid, uploader, file_name, ext, size, iso(created_at), url))

    bulk_insert(
        conn,
        "attachments",
        [
            "attachment_id",
            "task_id",
            "subtask_id",
            "uploader_user_id",
            "file_name",
            "file_type",
            "file_size_bytes",
            "created_at",
            "url",
        ],
        rows,
        chunk_size=12000,
    )
