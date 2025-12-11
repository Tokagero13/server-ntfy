"""API routes for endpoint management."""
import logging
import sqlite3

from flask import request
from flask_restx import Namespace, Resource

from app.utils.config import API_BASE, CHECK_INTERVAL, DASHBOARD_URL, NOTIFY_EVERY_MINUTES
from app.utils.database import get_db_connection
from app.utils.validators import normalize_url, validate_url

logger = logging.getLogger(__name__)


def create_endpoints_namespace(api, models):
    """Create and configure the endpoints namespace."""
    ns = Namespace("endpoints", description="Endpoint monitoring operations")

    @ns.route("/")
    class EndpointList(Resource):
        @ns.doc("list_endpoints")
        @ns.marshal_list_with(models["endpoint"])
        def get(self):
            """Get all endpoints."""
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT id, name, url, last_status, last_checked, last_notified, is_down FROM endpoints"
                    )
                    rows = cur.fetchall()

                    data = [
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "url": row["url"],
                            "last_status": row["last_status"],
                            "last_checked": row["last_checked"],
                            "last_notified": row["last_notified"],
                            "is_down": bool(row["is_down"]),
                        }
                        for row in rows
                    ]
                    return data
            except Exception as e:
                logger.error(f"Error listing endpoints: {e}")
                ns.abort(500, "Internal server error")

        @ns.doc("create_endpoint")
        @ns.expect(models["endpoint_create"])
        @ns.marshal_with(models["endpoint"], code=201)
        @ns.response(400, "Invalid URL", models["error"])
        @ns.response(409, "URL already exists", models["error"])
        def post(self):
            """Create a new endpoint."""
            try:
                data = request.json
                url = data.get("url")
                name = data.get("name", "")

                if not url:
                    ns.abort(400, "URL is required")

                normalized_url = normalize_url(url)

                if not validate_url(normalized_url):
                    ns.abort(400, "Invalid URL or domain format")

                with get_db_connection() as conn:
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            "INSERT INTO endpoints (name, url, last_status, last_checked, last_notified, is_down) VALUES (?, ?, NULL, NULL, NULL, FALSE)",
                            (name, normalized_url),
                        )
                        endpoint_id = cur.lastrowid
                        conn.commit()
                        logger.info(f"Created endpoint {endpoint_id}: {name} - {normalized_url}")
                        return {"id": endpoint_id, "name": name, "url": normalized_url}, 201
                    except sqlite3.IntegrityError:
                        ns.abort(409, "URL already exists")
            except Exception as e:
                logger.error(f"Error creating endpoint: {e}")
                ns.abort(500, "Internal server error")

    @ns.route("/<int:endpoint_id>")
    @ns.param("endpoint_id", "Endpoint identifier")
    class Endpoint(Resource):
        @ns.doc("get_endpoint")
        @ns.marshal_with(models["endpoint"])
        @ns.response(404, "Endpoint not found", models["error"])
        def get(self, endpoint_id):
            """Get endpoint by ID."""
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT id, name, url, last_status, last_checked, last_notified, is_down FROM endpoints WHERE id = ?",
                        (endpoint_id,),
                    )
                    row = cur.fetchone()

                    if row is None:
                        ns.abort(404, "Endpoint not found")

                    data = {
                        "id": row["id"],
                        "name": row["name"],
                        "url": row["url"],
                        "last_status": row["last_status"],
                        "last_checked": row["last_checked"],
                        "last_notified": row["last_notified"],
                        "is_down": bool(row["is_down"]),
                    }
                    return data
            except Exception as e:
                logger.error(f"Error getting endpoint {endpoint_id}: {e}")
                ns.abort(500, "Internal server error")

        @ns.doc("update_endpoint")
        @ns.expect(models["endpoint_create"])
        @ns.marshal_with(models["endpoint"])
        @ns.response(400, "Invalid URL", models["error"])
        @ns.response(404, "Endpoint not found", models["error"])
        def put(self, endpoint_id):
            """Update an endpoint."""
            try:
                data = request.json
                url = data.get("url")
                name = data.get("name", "")

                if not url:
                    ns.abort(400, "URL is required")

                normalized_url = normalize_url(url)

                if not validate_url(normalized_url):
                    ns.abort(400, "Invalid URL or domain format")

                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE endpoints SET name = ?, url = ? WHERE id = ?",
                        (name, normalized_url, endpoint_id),
                    )
                    if cur.rowcount == 0:
                        ns.abort(404, "Endpoint not found")

                    conn.commit()
                    logger.info(f"Updated endpoint {endpoint_id}: {name} - {normalized_url}")
                    return {"id": endpoint_id, "name": name, "url": normalized_url}
            except Exception as e:
                logger.error(f"Error updating endpoint {endpoint_id}: {e}")
                ns.abort(500, "Internal server error")

        @ns.doc("delete_endpoint")
        @ns.response(204, "Endpoint deleted")
        @ns.response(404, "Endpoint not found", models["error"])
        def delete(self, endpoint_id):
            """Delete an endpoint."""
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM endpoints WHERE id = ?", (endpoint_id,))
                    if cur.rowcount == 0:
                        ns.abort(404, "Endpoint not found")

                    conn.commit()
                    logger.info(f"Deleted endpoint {endpoint_id}")
                    return "", 204
            except Exception as e:
                logger.error(f"Error deleting endpoint {endpoint_id}: {e}")
                ns.abort(500, "Internal server error")

    @ns.route("/status")
    class HealthCheck(Resource):
        @ns.doc("health_check")
        @ns.marshal_with(models["status"])
        def get(self):
            """Check service health status."""
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) as count FROM endpoints")
                    endpoint_count = cur.fetchone()["count"]

                    return {
                        "status": "healthy",
                        "endpoints_count": endpoint_count,
                        "check_interval_seconds": CHECK_INTERVAL,
                        "notification_interval_minutes": NOTIFY_EVERY_MINUTES,
                        "api_base": API_BASE,
                        "dashboard_url": DASHBOARD_URL,
                    }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                ns.abort(500, f"Service unhealthy: {str(e)}")

    return ns
