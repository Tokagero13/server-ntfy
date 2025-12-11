# -*- coding: utf-8 -*-
from flask_restx import fields

def add_models_to_api(api):
    """Добавляет все модели данных в экземпляр API."""

    endpoint_model = api.model(
        "Endpoint",
        {
            "id": fields.Integer(readOnly=True, description="Уникальный идентификатор"),
            "name": fields.String(description="Название эндпоинта"),
            "url": fields.String(required=True, description="URL для мониторинга"),
            "last_status": fields.Integer(description="Последний HTTP статус код"),
            "last_checked": fields.String(description="Время последней проверки"),
            "last_notified": fields.String(description="Время последнего уведомления"),
            "is_down": fields.Boolean(description="Статус: недоступен ли эндпоинт"),
        },
    )

    endpoint_create_model = api.model(
        "EndpointCreate",
        {
            "name": fields.String(description="Название эндпоинта"),
            "url": fields.String(required=True, description="URL для мониторинга")
        },
    )

    status_model = api.model(
        "Status",
        {
            "status": fields.String(description="Статус сервиса"),
            "endpoints_count": fields.Integer(description="Количество эндпоинтов"),
            "check_interval_seconds": fields.Integer(
                description="Интервал проверки в секундах"
            ),
            "notification_interval_minutes": fields.Integer(
                description="Интервал уведомлений в минутах"
            ),
            "api_base": fields.String(description="API Base URL"),
            "dashboard_url": fields.String(description="Dashboard URL"),
        },
    )

    error_model = api.model(
        "Error", {"error": fields.String(description="Описание ошибки")}
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

    subscription_model = api.model(
        "Subscription",
        {
            "id": fields.Integer(readOnly=True, description="Идентификатор подписки"),
            "endpoint_id": fields.Integer(description="ID эндпоинта"),
            "chat_id": fields.String(description="Telegram Chat ID"),
            "enabled": fields.Boolean(description="Статус подписки"),
            "created_at": fields.String(description="Время создания"),
        },
    )

    subscription_create_model = api.model(
        "SubscriptionCreate",
        {
            "chat_id": fields.String(required=True, description="Telegram Chat ID"),
            "enabled": fields.Boolean(default=True, description="Статус подписки"),
        },
    )

    discovery_request_model = api.model(
        "DiscoveryRequest",
        {
            "timeout_minutes": fields.Integer(default=10, description="Время жизни кода в минутах"),
        },
    )

    discovery_response_model = api.model(
        "DiscoveryResponse",
        {
            "discovery_code": fields.String(description="Код для отправки боту"),
            "expires_at": fields.String(description="Время истечения кода"),
            "instructions": fields.String(description="Инструкция для пользователя"),
        },
    )

    discovery_status_model = api.model(
        "DiscoveryStatus",
        {
            "status": fields.String(description="pending, completed, expired"),
            "chat_id": fields.String(description="Обнаруженный Chat ID"),
            "username": fields.String(description="Username пользователя"),
            "first_name": fields.String(description="Имя пользователя"),
            "last_name": fields.String(description="Фамилия пользователя"),
        },
    )

    settings_model = api.model(
        "Settings",
        {
            "check_interval": fields.Integer(description="Интервал проверки в секундах"),
            "notify_every_minutes": fields.Integer(description="Интервал уведомлений в минутах"),
        },
    )

    return {
        "endpoint": endpoint_model,
        "endpoint_create": endpoint_create_model,
        "status": status_model,
        "error": error_model,
        "notification_log": notification_log_model,
        "paginated_notification": paginated_notification_model,
        "subscription": subscription_model,
        "subscription_create": subscription_create_model,
        "discovery_request": discovery_request_model,
        "discovery_response": discovery_response_model,
        "discovery_status": discovery_status_model,
        "settings": settings_model,
    }