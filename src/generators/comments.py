from __future__ import annotations

import random

from utils.dates import iso, now_utc, window_last_days, random_workday_datetime
from utils.ids import gid
from utils.randomness import build_rng
from utils.db import bulk_insert


def generate_comments(conn, cfg, users, tasks_ctx) -> None:
    rng = build_rng(cfg.seed + 59)
    tw = window_last_days(cfg.history_days, end=now_utc())

    user_ids = [u.user_id for u in users]

    rows = []

    # Comments on ~30% of tasks; 1-4 comments.
    for tid in tasks_ctx.task_ids:
        if rng.random() < 0.30:
            n = rng.choices([1, 2, 3, 4], weights=[0.55, 0.25, 0.15, 0.05], k=1)[0]
            for _ in range(n):
                author = rng.choice(user_ids)
                created_at = random_workday_datetime(rng, tw)
                body = rng.choice(
                    [
                        "Sharing a quick update: in progress and on track.",
                        "Flagging a dependency—waiting on access / approval.",
                        "Can you confirm expected behavior for the edge case?",
                        "I pushed a draft; please review when you have a moment.",
                        "Resolved in latest build; please validate in staging.",
                        "We should align with stakeholders before finalizing.",
                    ]
                )
                rows.append((gid(), author, tid, None, body, iso(created_at)))

    # Comments on subtasks ~15%.
    for sid in tasks_ctx.subtask_ids:
        if rng.random() < 0.15:
            n = rng.choices([1, 2], weights=[0.75, 0.25], k=1)[0]
            for _ in range(n):
                author = rng.choice(user_ids)
                created_at = random_workday_datetime(rng, tw)
                body = rng.choice(
                    [
                        "Added details above.",
                        "Done—please take a look.",
                        "Blocked on environment issue; investigating.",
                        "Will circle back after the meeting.",
                    ]
                )
                rows.append((gid(), author, None, sid, body, iso(created_at)))

    bulk_insert(
        conn,
        "comments",
        ["comment_id", "author_user_id", "task_id", "subtask_id", "body", "created_at"],
        rows,
        chunk_size=12000,
    )
