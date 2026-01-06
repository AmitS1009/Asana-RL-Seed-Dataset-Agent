from __future__ import annotations

import uuid


def gid() -> str:
    # Asana uses string GIDs; we simulate via UUIDv4.
    return str(uuid.uuid4())
