"""Flask-RESTX API models for documentation."""
from flask_restx import fields


def register_models(api):
    """Register all API models with the Flask-RESTX API."""
    endpoint_model = api.model(
        "Endpoint",
        {
            "id": fields.Integer(readOnly=True, description="Unique identifier"),
            "name": fields.String(description="Endpoint name"),
            "url": fields.String(required=True, description="URL to monitor"),
            "last_status": fields.Integer(description="Last HTTP status code"),
            "last_checked": fields.String(description="Last check timestamp"),
            "last_notified": fields.String(description="Last notification timestamp"),
            "is_down": fields.Boolean(description="Is endpoint down"),
        },
    )

    endpoint_create_model = api.model(
        "EndpointCreate",
        {
            "name": fields.String(description="Endpoint name"),
            "url": fields.String(required=True, description="URL to monitor")
        },
    )

    status_model = api.model(
        "Status",
        {
            "status": fields.String(description="Service status"),
            "endpoints_count": fields.Integer(description="Number of endpoints"),
            "check_interval_seconds": fields.Integer(description="Check interval in seconds"),
            "notification_interval_minutes": fields.Integer(description="Notification interval in minutes"),
            "api_base": fields.String(description="API base URL"),
            "dashboard_url": fields.String(description="Dashboard URL"),
        },
    )

    error_model = api.model(
        "Error",
        {"error": fields.String(description="Error description")}
    )

    notification_log_model = api.model(
        "NotificationLog",
        {
            "id": fields.Integer(readOnly=True),
            "timestamp": fields.String(),
            "endpoint_url": fields.String(),
            "message": fields.String(),
            "status": fields.String(),
        },
    )

    paginated_notification_model = api.model(
        "PaginatedNotificationLogs",
        {
            "logs": fields.List(fields.Nested(notification_log_model)),
            "total_pages": fields.Integer(),
            "current_page": fields.Integer(),
            "total_items": fields.Integer(),
        },
    )

    return {
        "endpoint": endpoint_model,
        "endpoint_create": endpoint_create_model,
        "status": status_model,
        "error": error_model,
        "notification_log": notification_log_model,
        "paginated_notification": paginated_notification_model,
    }
