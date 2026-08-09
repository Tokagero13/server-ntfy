# -*- coding: utf-8 -*-
"""Repository for the ``settings`` key/value table.

The legacy ``app.db.get_settings`` shim is intentionally left alone; a
follow-up task will migrate callers to :func:`get_all` here.
"""

from __future__ import annotations

from ..db import get_db_connection


def get_all() -> dict[str, str]:
    """Return every settings row as a ``{key: value}`` dict.

    Returns:
        A dict of all persisted settings; empty if the table has no rows.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in cur.fetchall()}


def update(key: str, value: str) -> str:
    """Upsert a single setting.

    Args:
        key: Setting name (primary key in the table).
        value: New value (stored as text).

    Returns:
        The upserted ``key``.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()
        return key
