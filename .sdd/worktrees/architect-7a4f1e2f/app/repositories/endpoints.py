# -*- coding: utf-8 -*-
"""Repository for the ``endpoints`` table.

Centralizes every SQL statement that reads or writes the ``endpoints``
table so callers can stay database-agnostic. All functions return plain
dicts and translate ``sqlite3`` integrity errors into a small typed
exception hierarchy.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from ..db import get_db_connection


class RepositoryError(Exception):
    """Base class for errors raised by the repositories package."""


class EndpointNotFound(RepositoryError):
    """Raised when the requested endpoint id does not exist."""

    def __init__(self, endpoint_id: int) -> None:
        super().__init__(f"Endpoint with id={endpoint_id} not found")
        self.endpoint_id = endpoint_id


class EndpointAlreadyExists(RepositoryError):
    """Raised when create/update would violate the unique URL constraint."""

    def __init__(self, url: str) -> None:
        super().__init__(f"Endpoint with url={url!r} already exists")
        self.url = url


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a ``sqlite3.Row`` from the endpoints table into a plain dict."""
    return {
        "id": row["id"],
        "name": row["name"],
        "url": row["url"],
        "last_status": row["last_status"],
        "last_checked": row["last_checked"],
        "last_notified": row["last_notified"],
        "is_down": bool(row["is_down"]),
    }


def list_endpoints() -> list[dict[str, Any]]:
    """Return every endpoint as a list of dicts.

    Returns:
        A list of endpoint dicts; empty when the table has no rows.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, url, last_status, last_checked, last_notified, is_down "
            "FROM endpoints"
        )
        return [_row_to_dict(row) for row in cur.fetchall()]


def get_endpoint(endpoint_id: int) -> dict[str, Any] | None:
    """Fetch a single endpoint by id.

    Args:
        endpoint_id: Primary key of the endpoint.

    Returns:
        The endpoint dict, or ``None`` if no row matches.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, url, last_status, last_checked, last_notified, is_down "
            "FROM endpoints WHERE id = ?",
            (endpoint_id,),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row else None


def create_endpoint(name: str, url: str) -> int:
    """Insert a new endpoint.

    Args:
        name: Human-friendly label (may be empty).
        url: Full URL to monitor. Must be unique across the table.

    Returns:
        The auto-generated primary key of the new row.

    Raises:
        EndpointAlreadyExists: When ``url`` collides with an existing endpoint.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO endpoints "
                "(name, url, last_status, last_checked, last_notified, is_down) "
                "VALUES (?, ?, NULL, NULL, NULL, FALSE)",
                (name, url),
            )
        except sqlite3.IntegrityError as exc:
            raise EndpointAlreadyExists(url) from exc
        conn.commit()
        return int(cur.lastrowid or 0)


def update_endpoint(endpoint_id: int, name: str, url: str) -> int:
    """Update the ``name`` and ``url`` of an existing endpoint.

    Args:
        endpoint_id: Primary key of the endpoint to update.
        name: New label.
        url: New URL.

    Returns:
        The updated endpoint id.

    Raises:
        EndpointNotFound: When no endpoint has the given id.
        EndpointAlreadyExists: When ``url`` collides with another endpoint.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE endpoints SET name = ?, url = ? WHERE id = ?",
                (name, url, endpoint_id),
            )
        except sqlite3.IntegrityError as exc:
            raise EndpointAlreadyExists(url) from exc
        if cur.rowcount == 0:
            raise EndpointNotFound(endpoint_id)
        conn.commit()
        return endpoint_id


def delete_endpoint(endpoint_id: int) -> int:
    """Delete an endpoint by id.

    Args:
        endpoint_id: Primary key of the endpoint to delete.

    Returns:
        The deleted endpoint id.

    Raises:
        EndpointNotFound: When no endpoint has the given id.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM endpoints WHERE id = ?", (endpoint_id,))
        if cur.rowcount == 0:
            raise EndpointNotFound(endpoint_id)
        conn.commit()
        return endpoint_id


def update_status(endpoint_id: int, status: int, checked_at: str) -> int | None:
    """Record the latest observed HTTP status and check timestamp.

    Args:
        endpoint_id: Primary key of the endpoint.
        status: Last observed HTTP status code (``0`` if unreachable).
        checked_at: ISO-8601 timestamp of the probe.

    Returns:
        ``endpoint_id`` if the update affected a row, otherwise ``None``.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE endpoints SET last_status = ?, last_checked = ? WHERE id = ?",
            (status, checked_at, endpoint_id),
        )
        if cur.rowcount == 0:
            return None
        conn.commit()
        return endpoint_id


def mark_down(endpoint_id: int, notified_at: str) -> int | None:
    """Flag an endpoint as down and stamp the outgoing notification time.

    Args:
        endpoint_id: Primary key of the endpoint.
        notified_at: ISO-8601 timestamp of the outgoing notification.

    Returns:
        ``endpoint_id`` if the update affected a row, otherwise ``None``.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE endpoints SET is_down = ?, last_notified = ? WHERE id = ?",
            (True, notified_at, endpoint_id),
        )
        if cur.rowcount == 0:
            return None
        conn.commit()
        return endpoint_id


def mark_up(endpoint_id: int, notified_at: str) -> int | None:
    """Flag an endpoint as recovered and stamp the recovery notification time.

    Args:
        endpoint_id: Primary key of the endpoint.
        notified_at: ISO-8601 timestamp of the recovery notification.

    Returns:
        ``endpoint_id`` if the update affected a row, otherwise ``None``.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE endpoints SET is_down = ?, last_notified = ? WHERE id = ?",
            (False, notified_at, endpoint_id),
        )
        if cur.rowcount == 0:
            return None
        conn.commit()
        return endpoint_id


def update_notified(endpoint_id: int, notified_at: str) -> int | None:
    """Update only the ``last_notified`` timestamp of an endpoint.

    Used when re-notifying about a still-down endpoint without changing
    its ``is_down`` flag.

    Args:
        endpoint_id: Primary key of the endpoint.
        notified_at: ISO-8601 timestamp of the outgoing notification.

    Returns:
        ``endpoint_id`` if the update affected a row, otherwise ``None``.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE endpoints SET last_notified = ? WHERE id = ?",
            (notified_at, endpoint_id),
        )
        if cur.rowcount == 0:
            return None
        conn.commit()
        return endpoint_id
