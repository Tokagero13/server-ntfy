"""API routes for notification logs."""
import logging
import math

from flask import request
from flask_restx import Namespace, Resource

from app.utils.database import get_db_connection

logger = logging.getLogger(__name__)


def create_notifications_namespace(api, models):
    """Create and configure the notifications namespace."""
    ns = Namespace("endpoints", description="Notification logs operations")

    @ns.route("/notifications")
    class NotificationList(Resource):
        @ns.doc("list_notification_logs")
        @ns.marshal_with(models["paginated_notification"])
        def get(self):
            """Get notification logs with pagination, sorting, and filtering."""
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", 25, type=int)
            sort_by = request.args.get("sort_by", "timestamp", type=str)
            order = request.args.get("order", "desc", type=str)
            search = request.args.get("search", "", type=str)
            endpoint_filter = request.args.get("endpoint_filter", "", type=str)
            status_filter = request.args.get("status_filter", "", type=str)

            # Validate sort field
            if sort_by != "timestamp":
                sort_by = "timestamp"

            # Validate sort order
            if order.lower() not in ["asc", "desc"]:
                order = "desc"

            offset = (page - 1) * per_page

            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()

                    base_query = "FROM notification_logs"
                    count_query = "SELECT COUNT(*) as total "
                    data_query = "SELECT id, timestamp, endpoint_url, message, status "

                    params = []
                    where_conditions = []

                    # Exact endpoint filter
                    if endpoint_filter:
                        where_conditions.append("endpoint_url = ?")
                        params.append(endpoint_filter)

                    # Status filter
                    if status_filter:
                        where_conditions.append("status = ?")
                        params.append(status_filter)

                    # Search in endpoint_url and message
                    if search:
                        where_conditions.append("(endpoint_url LIKE ? OR message LIKE ?)")
                        search_param = f"%{search}%"
                        params.extend([search_param, search_param])

                    where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                    # Count total items
                    count_params = params.copy()
                    cur.execute(count_query + base_query + where_clause, count_params)
                    total_items = cur.fetchone()["total"]
                    total_pages = math.ceil(total_items / per_page)

                    # Fetch data
                    full_data_query = (
                        data_query
                        + base_query
                        + where_clause
                        + f" ORDER BY {sort_by} {order.upper()} LIMIT ? OFFSET ?"
                    )
                    params.extend([per_page, offset])

                    cur.execute(full_data_query, params)
                    rows = cur.fetchall()

                    return {
                        "logs": [dict(row) for row in rows],
                        "total_pages": total_pages,
                        "current_page": page,
                        "total_items": total_items,
                    }

            except Exception as e:
                logger.error(f"Error listing notification logs: {e}")
                ns.abort(500, "Internal server error")

    return ns
