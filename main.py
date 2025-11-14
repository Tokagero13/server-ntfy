# -*- coding: utf-8 -*-
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
import os
from dotenv import load_dotenv

import requests
from flask import Flask, request, send_from_directory, render_template_string
from flask_restx import Api, Namespace, Resource, fields, reqparse
import math

load_dotenv()

DB_PATH = os.getenv('DB_PATH', 'endpoints.db')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 10))
NOTIFY_EVERY_MINUTES = int(os.getenv('NOTIFY_EVERY_MINUTES', 2))
INDEX_PAGE = os.getenv('INDEX_PAGE', 'index2.html')
NTFY_TOPIC = os.getenv('NTFY_TOPIC', 'default_topic')
NTFY_SERVER = os.getenv('NTFY_SERVER', 'https://ntfy.server')
URL = os.getenv('URL', 'localhost')
PORT = int(os.getenv('PORT', 5000))

# Правильно формируем URL с интерполяцией переменных
API_BASE = os.getenv('API_BASE', f'http://{URL}:{PORT}/api/endpoints')
DASHBOARD_URL = os.getenv('DASHBOARD_URL', f'{URL}:{PORT}')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Настройка Swagger/OpenAPI документации
api = Api(
    app,
    version="1.0.0",
    title="Endpoints Monitor API",
    description="API для мониторинга эндпоинтов с уведомлениями через ntfy",
    doc="/docs/",
    prefix="/api",
    # contact="Admin",
    # contact_email="admin@example.com",
    # license="MIT",
    # license_url="https://opensource.org/licenses/MIT",
    ordered=True,
    validate=True,
)

# Создание namespace для группировки эндпоинтов
ns = Namespace("endpoints", description="Операции с эндпоинтами мониторинга")
api.add_namespace(ns)

# Модели для документации
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


# Создаем thread-local хранилище для соединений с БД
local_storage = threading.local()

@contextmanager
def get_db_connection():
    """Контекстный менеджер для безопасной работы с БД, использующий thread-local соединения."""
    # Проверяем, есть ли уже соединение для этого потока
    if not hasattr(local_storage, "connection"):
        try:
            # Создаем новое соединение, если его нет
            local_storage.connection = sqlite3.connect(DB_PATH, timeout=20.0, check_same_thread=False)
            local_storage.connection.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    conn = local_storage.connection
    try:
        yield conn
    except Exception as e:
        # Не откатываем здесь, пусть вызывающий код решает
        logger.error(f"Database operation error: {e}")
        raise
    # Не закрываем соединение здесь, чтобы оно могло быть переиспользовано в том же потоке


def normalize_url(url: str) -> str:
    """Преобразование домена в полный URL с поддержкой портов.
    Возвращает HTTPS версию по умолчанию, HTTP fallback будет обработан в check_endpoint_status_with_fallback."""
    url = url.strip()
    
    # Если это уже полный URL, вернуть как есть
    if url.startswith(('http://', 'https://')):
        return url
    
    # Для любого адреса без протокола добавляем HTTPS по умолчанию
    # Функция check_endpoint_status_with_fallback будет пробовать HTTP если HTTPS не работает
    return f'https://{url}'

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
        if ':' in netloc:
            hostname, port_str = netloc.rsplit(':', 1)
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
            parts = ip.split('.')
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
        elif hostname == 'localhost':
            return True  # localhost всегда валиден
        elif '.' in hostname:
            # Проверяем доменное имя
            parts = hostname.split('.')
            for part in parts:
                if not part or not all(c.isalnum() or c == '-' for c in part):
                    return False
                if part.startswith('-') or part.endswith('-'):
                    return False
            return True
        else:
            return False  # Неподдерживаемый формат
            
    except Exception:
        return False


def init_db():
    """Инициализация базы данных"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            # Создаем таблицу если не существует
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS endpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    last_status INTEGER,
                    last_checked TEXT,
                    last_notified TEXT
                )
                """
            )

            # Проверяем существует ли столбец is_down
            cur.execute("PRAGMA table_info(endpoints)")
            columns = [column[1] for column in cur.fetchall()]

            if "is_down" not in columns:
                logger.info("Adding is_down column to endpoints table")
                cur.execute(
                    "ALTER TABLE endpoints ADD COLUMN is_down BOOLEAN DEFAULT FALSE"
                )

            if "name" not in columns:
                logger.info("Adding name column to endpoints table")
                cur.execute(
                    "ALTER TABLE endpoints ADD COLUMN name TEXT"
                )

            # Добавляем UNIQUE ограничение если его нет
            try:
                cur.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_endpoints_url ON endpoints(url)"
                )
            except Exception as e:
                logger.warning(f"Could not create unique index: {e}")

            # Создаем таблицу для логов уведомлений
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    endpoint_url TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL
                )
                """
            )

            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def send_ntfy_notification(topic: str, message: str, endpoint_url: str) -> None:
    """Отправка уведомления через ntfy и логирование в БД"""
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    log_status = "failed"
    try:
        resp = requests.post(url, data=message.encode("utf-8"), timeout=5)
        if resp.status_code == 200:
            logger.info(f"Notification sent: {message}")
            log_status = "sent"
        else:
            logger.warning(
                f"Notification failed with status {resp.status_code}: {message}"
            )
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
    
    # Логирование в БД
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notification_logs (timestamp, endpoint_url, message, status) VALUES (?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), endpoint_url, message, log_status),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log notification: {e}")


def check_endpoints_loop():
    """Основной цикл проверки эндпоинтов"""
    logger.info("Starting endpoint monitoring loop")

    while True:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, name, url, last_status, last_checked, last_notified, is_down FROM endpoints"
                )
                rows = cur.fetchall()

                for row in rows:
                    endpoint_id = row["id"]
                    name = row["name"]
                    url = row["url"]
                    last_status = row["last_status"]
                    last_notified = row["last_notified"]
                    was_down = row["is_down"] or False

                    # Проверяем статус эндпоинта
                    current_status = check_endpoint_status(url)
                    now_utc = datetime.now(timezone.utc)
                    now_iso = now_utc.isoformat()

                    # Обновляем статус в БД
                    is_currently_down = current_status == 0
                    cur.execute(
                        """
                        UPDATE endpoints
                        SET last_status = ?, last_checked = ?, is_down = ?
                        WHERE id = ?
                        """,
                        (current_status, now_iso, is_currently_down, endpoint_id),
                    )

                    # Логика уведомлений
                    should_notify = check_notification_needed(
                        current_status,
                        last_status,
                        was_down,
                        last_notified,
                        now_utc,
                        url,
                    )

                    if should_notify:
                        update_notification_time(cur, endpoint_id, now_iso)

                conn.commit()
                logger.debug(f"Checked {len(rows)} endpoints")

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")

        time.sleep(CHECK_INTERVAL)


def check_endpoint_status(url: str) -> int:
    """Проверка статуса одного эндпоинта с fallback HTTPS->HTTP"""
    return check_endpoint_status_with_fallback(url)

def check_endpoint_status_with_fallback(url: str) -> int:
    """Проверка статуса эндпоинта с автоматическим fallback с HTTPS на HTTP"""
    # Сначала пробуем оригинальный URL
    try:
        resp = requests.get(url, timeout=5)
        return resp.status_code
    except Exception as e:
        logger.debug(f"Primary attempt failed for {url}: {e}")
        
        # Если URL использует HTTPS, пробуем HTTP
        if url.startswith('https://'):
            http_url = url.replace('https://', 'http://', 1)
            try:
                logger.info(f"Trying HTTP fallback for {url} -> {http_url}")
                resp = requests.get(http_url, timeout=5)
                logger.info(f"HTTP fallback successful for {http_url}")
                return resp.status_code
            except Exception as e2:
                logger.debug(f"HTTP fallback also failed for {http_url}: {e2}")
        
        return 0


def check_notification_needed(
    current_status: int, last_status: int, was_down: bool, last_notified: str, now_utc: datetime, url: str
) -> bool:
    """Определяет, нужно ли отправлять уведомление"""
    is_down = current_status == 0
    is_recovered = was_down and not is_down
    just_went_down = not was_down and is_down

    # Уведомление о восстановлении
    if is_recovered:
        message = f"[OK] RECOVERED: {url} is back online (status: {current_status})\n\nDashboard: {DASHBOARD_URL}"
        send_ntfy_notification(NTFY_TOPIC, message, url)
        return True

    # Уведомление о падении (с учетом интервала)
    if is_down and should_send_down_notification(last_notified, now_utc):
        if just_went_down:
            message = f"[ALERT] {url} is DOWN\n\nDashboard: {DASHBOARD_URL}"
            send_ntfy_notification(NTFY_TOPIC, message, url)
        else:
            message = f"[WARNING] STILL DOWN: {url} remains unavailable\n\nDashboard: {DASHBOARD_URL}"
            send_ntfy_notification(NTFY_TOPIC, message, url)
        return True

    return False


def should_send_down_notification(last_notified: str, now_utc: datetime) -> bool:
    """Проверяет, можно ли отправить уведомление о падении"""
    if not last_notified:
        return True

    try:
        last_notif_dt = datetime.fromisoformat(last_notified)
        time_diff = now_utc - last_notif_dt
        return time_diff > timedelta(minutes=NOTIFY_EVERY_MINUTES)
    except Exception:
        return True


def update_notification_time(cur: sqlite3.Cursor, endpoint_id: int, now_iso: str) -> None:
    """Обновляет время последнего уведомления"""
    cur.execute(
        "UPDATE endpoints SET last_notified = ? WHERE id = ?",
        (now_iso, endpoint_id),
    )


# ---------- REST API ----------
@ns.route("/")
class EndpointList(Resource):
    @ns.doc("list_endpoints")
    @ns.marshal_list_with(endpoint_model)
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
    @ns.expect(endpoint_create_model)
    @ns.marshal_with(endpoint_model, code=201)
    @ns.response(400, "Invalid URL", error_model)
    @ns.response(409, "URL already exists", error_model)
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
                    logger.info(f"Created endpoint {endpoint_id}: {name} - {normalized_url}")
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
    @ns.marshal_with(endpoint_model)
    @ns.response(404, "Endpoint not found", error_model)
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
    @ns.expect(endpoint_create_model)
    @ns.marshal_with(endpoint_model)
    @ns.response(400, "Invalid URL", error_model)
    @ns.response(404, "Endpoint not found", error_model)
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
                logger.info(f"Updated endpoint {endpoint_id}: {name} - {normalized_url}")
                return {"id": endpoint_id, "name": name, "url": normalized_url}
        except Exception as e:
            logger.error(f"Error updating endpoint {endpoint_id}: {e}")
            ns.abort(500, "Internal server error")

    @ns.doc("delete_endpoint")
    @ns.response(204, "Endpoint deleted")
    @ns.response(404, "Endpoint not found", error_model)
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
    @ns.marshal_with(paginated_notification_model)
    def get(self):
        """Получить список логов уведомлений с пагинацией, сортировкой и фильтрацией"""
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 25, type=int)
        sort_by = request.args.get("sort_by", "timestamp", type=str)
        order = request.args.get("order", "desc", type=str)
        search = request.args.get("search", "", type=str)
        endpoint_filter = request.args.get("endpoint_filter", "", type=str)

        # Валидация полей сортировки - теперь только timestamp
        if sort_by != "timestamp":
            sort_by = "timestamp"

        # Валидация порядка сортировки
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
                where_clause = ""
                
                # Точная фильтрация по endpoint_filter (для выбора из списка)
                if endpoint_filter:
                    where_clause = " WHERE endpoint_url = ?"
                    params.append(endpoint_filter)
                # Fallback для старого search параметра (LIKE поиск)
                elif search:
                    where_clause = " WHERE endpoint_url LIKE ? OR message LIKE ?"
                    search_param = f"%{search}%"
                    params.extend([search_param, search_param])

                # Запрос для подсчета общего количества
                count_params = params.copy()
                cur.execute(count_query + base_query + where_clause, count_params)
                total_items = cur.fetchone()["total"]
                total_pages = math.ceil(total_items / per_page)

                # Запрос для получения данных
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

@ns.route("/status")
class HealthCheck(Resource):
    @ns.doc("health_check")
    @ns.marshal_with(status_model)
    def get(self):
        """Проверка статуса сервиса мониторинга"""
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


# Маршрут для главной страницы
@app.route('/')
def index():
    with open(INDEX_PAGE, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Заменяем плейсхолдеры в HTML
    template = template.replace('{ntfy_server}', NTFY_SERVER)
    template = template.replace('{topic}', NTFY_TOPIC)
    
    return template

# CORS для работы с фронтендом
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# Инициализация только при прямом запуске
if __name__ == "__main__":
    init_db()
    # Стартуем фоновый поток проверки
    t = threading.Thread(target=check_endpoints_loop, daemon=True)
    t.start()
    # Стартуем Flask для разработки
    app.run(host=URL, port=PORT, debug=True)
