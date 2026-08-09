# -*- coding: utf-8 -*-
"""Repository for the ``endpoint_subscriptions`` table.

Owns all SQL for per-chat subscriptions to endpoint status changes.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from ..db import get_db_connection


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a subscription row into a plain dict with a Python bool."""
    return {
        "id": row["id"],
        "endpoint_id": row["endpoint_id"],
        "chat_id": row["chat_id"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
    }


def list_subscriptions_for_endpoint(endpoint_id: int) -> list[dict[str, Any]]:
    """Return every subscription targeting the given endpoint.

    Args:
        endpoint_id: Endpoint whose subscriptions to fetch.

    Returns:
        A list of subscription dicts (possibly empty).
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, endpoint_id, chat_id, enabled, created_at "
            "FROM endpoint_subscriptions WHERE endpoint_id = ?",
            (endpoint_id,),
        )
        return [_row_to_dict(row) for row in cur.fetchall()]


def list_subscriptions_for_chat(chat_id: str) -> list[dict[str, Any]]:
    """Return every subscription for a Telegram chat, joined with endpoint info.

    Args:
        chat_id: Telegram chat identifier (string form).

    Returns:
        A list of dicts containing the flat subscription fields plus a
        nested ``endpoint`` dict with ``id``, ``name``, ``url``, and
        ``is_down``.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT es.id, es.enabled, es.created_at,
                   es.endpoint_id, es.chat_id,
                   e.name AS endpoint_name, e.url AS endpoint_url,
                   e.is_down AS endpoint_is_down
              FROM endpoint_subscriptions es
              JOIN endpoints e ON es.endpoint_id = e.id
             WHERE es.chat_id = ?
             ORDER BY e.name, e.url
            """,
            (chat_id,),
        )
        rows = cur.fetchall()

    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "endpoint_id": row["endpoint_id"],
                "chat_id": row["chat_id"],
                "enabled": bool(row["enabled"]),
                "created_at": row["created_at"],
                "endpoint": {
                    "id": row["endpoint_id"],
                    "name": row["endpoint_name"],
                    "url": row["endpoint_url"],
                    "is_down": bool(row["endpoint_is_down"]),
                },
            }
        )
    return result


def get_subscription(subscription_id: int) -> dict[str, Any] | None:
    """Fetch a single subscription by id.

    Args:
        subscription_id: Primary key.

    Returns:
        The subscription dict, or ``None`` if no row matches.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, endpoint_id, chat_id, enabled, created_at "
            "FROM endpoint_subscriptions WHERE id = ?",
            (subscription_id,),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


def create_subscription(
    endpoint_id: int, chat_id: str, enabled: bool = True
) -> int:
    """Insert a new subscription with the current UTC timestamp.

    Args:
        endpoint_id: Endpoint the chat wants to be notified about.
        chat_id: Telegram chat identifier.
        enabled: Whether the subscription starts active.

    Returns:
        The auto-generated primary key of the new subscription.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO endpoint_subscriptions "
            "(endpoint_id, chat_id, enabled, created_at) "
            "VALUES (?, ?, ?, ?)",
            (endpoint_id, chat_id, enabled, now_iso),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def toggle_subscription(subscription_id: int) -> int | None:
    """Flip the ``enabled`` flag of a subscription.

    Args:
        subscription_id: Primary key.

    Returns:
        ``subscription_id`` on success, ``None`` if it does not exist.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT enabled FROM endpoint_subscriptions WHERE id = ?",
            (subscription_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cur.execute(
            "UPDATE endpoint_subscriptions SET enabled = ? WHERE id = ?",
            (not bool(row["enabled"]), subscription_id),
        )
        conn.commit()
        return subscription_id


def delete_subscription(subscription_id: int) -> int | None:
    """Delete a subscription by id.

    Args:
        subscription_id: Primary key.

    Returns:
        ``subscription_id`` on success, ``None`` if it does not exist.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM endpoint_subscriptions WHERE id = ?",
            (subscription_id,),
        )
        if cur.rowcount == 0:
            return None
        conn.commit()
        return subscription_id


def get_enabled_chat_ids_for_endpoint(endpoint_id: int) -> list[str]:
    """Return the chat ids currently enabled for the given endpoint.

    Args:
        endpoint_id: Endpoint whose active subscribers to look up.

    Returns:
        A list of chat id strings; empty if no active subscriptions exist.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT chat_id FROM endpoint_subscriptions "
            "WHERE endpoint_id = ? AND enabled = 1",
            (endpoint_id,),
        )
        return [row["chat_id"] for row in cur.fetchall()]
