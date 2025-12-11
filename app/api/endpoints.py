# -*- coding: utf-8 -*-
import logging
import math
import sqlite3
from urllib.parse import urlparse

from flask import request
from flask_restx import Namespace, Resource

from ..db import get_db_connection
from ..models import add_models_to_api

logger = logging.getLogger(__name__)

ns = Namespace(
    "endpoints", description="Операции с эндпоинтами, уведомлениями и подписками"
)
models = add_models_to_api(ns)


def normalize_url(url: str) -> str:
    """Преобразование домена в полный URL с поддержкой портов.
    Возвращает HTTPS версию по умолчанию, HTTP fallback будет обработан в check_endpoint_status_with_fallback."""
    url = url.strip()

    # Если это уже полный URL, вернуть как есть
    if url.startswith(("http://", "https://")):
        return url

    # Для любого адреса без протокола добавляем HTTPS по умолчанию
    # Функция check_endpoint_status_with_fallback будет пробовать HTTP если HTTPS не работает
    return f"https://{url}"


def validate_url(url: str) -> bool:
    """Валидация URL или домена с поддержкой портов"""
    try:
        # Сначала нормализуем URL
        normalized = normalize_url(url)
        result = urlparse(normalized)

        # Проверяем, что есть схема и домен
        if not all([result.scheme, result.netloc]):
            return False

        # Проверяем корректность схемы
        if result.scheme not in ["http", "https"]:
            return False

        # Разбираем netloc для проверки порта
        netloc = result.netloc
        if ":" in netloc:
            hostname, port_str = netloc.rsplit(":", 1)
            try:
                port = int(port_str)
                # Проверяем корректность порта
                if not (1 <= port <= 65535):
                    return False
            except ValueError:
                return False
        else:
            hostname = netloc

        # Улучшенная проверка IPv4 адресов и доменов
        def is_valid_ipv4(ip):
            """Проверка валидности IPv4 адреса"""
            parts = ip.split(".")
            if len(parts) != 4:
                return False
            try:
                for part in parts:
                    num = int(part)
                    if not (0 <= num <= 255):
                        return False
                return True
            except ValueError:
                return False

        # Проверяем hostname
        if is_valid_ipv4(hostname):
            return True  # Валидный IPv4
        elif hostname == "localhost":
            return True  # localhost всегда валиден
        elif "." in hostname:
            # Проверяем доменное имя
            parts = hostname.split(".")
            for part in parts:
                if not part or not all(c.isalnum() or c == "-" for c in part):
                    return False
                if part.startswith("-") or part.endswith("-"):
                    return False
            return True
        else:
            return False  # Неподдерживаемый формат

    except Exception:
        return False


@ns.route("/")
class EndpointList(Resource):
    @ns.doc("list_endpoints")
    @ns.marshal_list_with(models["endpoint"])
    def get(self):
        """Получить список всех эндпоинтов"""
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
        """Создать новый эндпоинт для мониторинга"""
        try:
            data = request.json
            url = data.get("url")
            name = data.get("name", "")

            if not url:
                ns.abort(400, "URL is required")

            # Нормализуем URL (преобразуем домен в полный URL)
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
                    logger.info(
                        f"Created endpoint {endpoint_id}: {name} - {normalized_url}"
                    )
                    return {"id": endpoint_id, "name": name, "url": normalized_url}, 201
                except sqlite3.IntegrityError:
                    ns.abort(409, "URL already exists")
        except Exception as e:
            logger.error(f"Error creating endpoint: {e}")
            ns.abort(500, "Internal server error")


@ns.route("/<int:endpoint_id>")
@ns.param("endpoint_id", "Идентификатор эндпоинта")
class Endpoint(Resource):
    @ns.doc("get_endpoint")
    @ns.marshal_with(models["endpoint"])
    @ns.response(404, "Endpoint not found", models["error"])
    def get(self, endpoint_id):
        """Получить информацию о конкретном эндпоинте"""
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
        """Обновить существующий эндпоинт"""
        try:
            data = request.json
            url = data.get("url")
            name = data.get("name", "")

            if not url:
                ns.abort(400, "URL is required")

            # Нормализуем URL (преобразуем домен в полный URL)
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
                logger.info(
                    f"Updated endpoint {endpoint_id}: {name} - {normalized_url}"
                )
                return {"id": endpoint_id, "name": name, "url": normalized_url}
        except Exception as e:
            logger.error(f"Error updating endpoint {endpoint_id}: {e}")
            ns.abort(500, "Internal server error")

    @ns.doc("delete_endpoint")
    @ns.response(204, "Endpoint deleted")
    @ns.response(404, "Endpoint not found", models["error"])
    def delete(self, endpoint_id):
        """Удалить эндпоинт"""
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


@ns.route("/notifications")
class NotificationList(Resource):
    @ns.doc("list_notification_logs")
    @ns.marshal_with(models["paginated_notification"])
    def get(self):
        """Получить список логов уведомлений с пагинацией, сортировкой и фильтрацией"""
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)
        sort_by = request.args.get("sort_by", "timestamp", type=str)
        order = request.args.get("order", "desc", type=str)
        search = request.args.get("search", "", type=str)
        endpoint_filter = request.args.get("endpoint_filter", "", type=str)
        status_filter = request.args.get("status_filter", "", type=str)

        if sort_by != "timestamp":
            sort_by = "timestamp"

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

                if endpoint_filter:
                    where_conditions.append("endpoint_url = ?")
                    params.append(endpoint_filter)

                if status_filter:
                    where_conditions.append("status = ?")
                    params.append(status_filter)

                if search:
                    where_conditions.append("(endpoint_url LIKE ? OR message LIKE ?)")
                    search_param = f"%{search}%"
                    params.extend([search_param, search_param])

                where_clause = (
                    " WHERE " + " AND ".join(where_conditions)
                    if where_conditions
                    else ""
                )

                count_params = params.copy()
                cur.execute(count_query + base_query + where_clause, count_params)
                total_items = cur.fetchone()["total"]
                total_pages = math.ceil(total_items / per_page)

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


@ns.route("/<int:endpoint_id>/subscriptions")
@ns.param("endpoint_id", "Идентификатор эндпоинта")
class SubscriptionList(Resource):
    @ns.doc("get_subscriptions")
    @ns.marshal_list_with(models["subscription"])
    def get(self, endpoint_id):
        """Получить список подписок для эндпоинта"""
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, endpoint_id, chat_id, enabled, created_at FROM endpoint_subscriptions WHERE endpoint_id = ?",
                    (endpoint_id,),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting subscriptions for endpoint {endpoint_id}: {e}")
            ns.abort(500, "Internal server error")

    @ns.doc("add_subscription")
    @ns.expect(models["subscription_create"])
    @ns.marshal_with(models["subscription"], code=201)
    def post(self, endpoint_id):
        """Создать новую подписку для эндпоинта"""
        try:
            data = request.json
            chat_id = data.get("chat_id")

            if not chat_id:
                ns.abort(400, "Chat ID is required")

            with get_db_connection() as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        "INSERT INTO endpoint_subscriptions (endpoint_id, chat_id, enabled) VALUES (?, ?, ?)",
                        (endpoint_id, chat_id, True),
                    )
                    subscription_id = cur.lastrowid
                    conn.commit()

                    cur.execute(
                        "SELECT * FROM endpoint_subscriptions WHERE id = ?",
                        (subscription_id,),
                    )
                    new_subscription = cur.fetchone()

                    logger.info(
                        f"Created subscription {subscription_id} for endpoint {endpoint_id} to chat {chat_id}"
                    )
                    return dict(new_subscription), 201
                except Exception as e:
                    # Уточняем обработку ошибок, например, для дубликатов
                    if "UNIQUE constraint failed" in str(e):
                        ns.abort(
                            409,
                            f"Subscription for chat_id '{chat_id}' already exists for this endpoint.",
                        )
                    logger.error(f"Database error creating subscription: {e}")
                    ns.abort(500, "Internal server error")

        except Exception as e:
            logger.error(f"Error creating subscription for endpoint {endpoint_id}: {e}")
            ns.abort(500, "Internal server error")


@ns.route("/<int:endpoint_id>/subscriptions/<int:subscription_id>")
@ns.param("endpoint_id", "Идентификатор эндпоинта")
@ns.param("subscription_id", "Идентификатор подписки")
class Subscription(Resource):
    @ns.doc("toggle_subscription")
    @ns.marshal_with(models["subscription"])
    def patch(self, endpoint_id, subscription_id):
        """Переключить статус подписки (включить/выключить)"""
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()

                # Сначала получаем текущий статус
                cur.execute(
                    "SELECT enabled FROM endpoint_subscriptions WHERE id = ? AND endpoint_id = ?",
                    (subscription_id, endpoint_id),
                )
                subscription = cur.fetchone()
                if not subscription:
                    ns.abort(404, "Subscription not found")

                # Инвертируем статус
                new_enabled_status = not subscription["enabled"]

                cur.execute(
                    "UPDATE endpoint_subscriptions SET enabled = ? WHERE id = ? AND endpoint_id = ?",
                    (new_enabled_status, subscription_id, endpoint_id),
                )
                if cur.rowcount == 0:
                    ns.abort(404, "Subscription not found")

                conn.commit()

                cur.execute(
                    "SELECT * FROM endpoint_subscriptions WHERE id = ?",
                    (subscription_id,),
                )
                updated_subscription = cur.fetchone()

                logger.info(
                    f"Updated subscription {subscription_id} for endpoint {endpoint_id}"
                )
                return dict(updated_subscription)

        except Exception as e:
            logger.error(f"Error updating subscription {subscription_id}: {e}")
            ns.abort(500, "Internal server error")

    @ns.doc("delete_subscription")
    @ns.response(204, "Subscription deleted")
    def delete(self, endpoint_id, subscription_id):
        """Удалить подписку"""
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "DELETE FROM endpoint_subscriptions WHERE id = ? AND endpoint_id = ?",
                    (subscription_id, endpoint_id),
                )
                if cur.rowcount == 0:
                    ns.abort(404, "Subscription not found")

                conn.commit()
                logger.info(
                    f"Deleted subscription {subscription_id} from endpoint {endpoint_id}"
                )
                return "", 204
        except Exception as e:
            logger.error(f"Error deleting subscription {subscription_id}: {e}")
            ns.abort(500, "Internal server error")
