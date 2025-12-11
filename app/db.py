# -*- coding: utf-8 -*-
import sqlite3
import threading
import logging
from contextlib import contextmanager
from . import config

logger = logging.getLogger(__name__)

# Создаем thread-local хранилище для соединений с БД
local_storage = threading.local()

@contextmanager
def get_db_connection():
    """Контекстный менеджер для безопасной работы с БД, использующий thread-local соединения."""
    # Проверяем, есть ли уже соединение для этого потока
    if not hasattr(local_storage, "connection"):
        try:
            # Создаем новое соединение, если его нет
            local_storage.connection = sqlite3.connect(config.DB_PATH, timeout=20.0, check_same_thread=False)
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

            # Создаем таблицу для подписок на уведомления по эндпоинтам
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS endpoint_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint_id INTEGER NOT NULL,
                    chat_id TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (endpoint_id) REFERENCES endpoints (id) ON DELETE CASCADE,
                    UNIQUE(endpoint_id, chat_id)
                )
                """
            )

            # Создаем таблицу для обнаружения Chat ID через Telegram
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_discovery (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discovery_code TEXT UNIQUE NOT NULL,
                    chat_id TEXT,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )

            # Создаем таблицу для настроек
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            
            # Устанавливаем значения по умолчанию, если их нет
            cur.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                ("check_interval", str(config.CHECK_INTERVAL)),
            )
            cur.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                ("notify_every_minutes", str(config.NOTIFY_EVERY_MINUTES)),
            )

            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

def get_settings() -> dict:
    """Получает все настройки из БД"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, value FROM settings")
            rows = cur.fetchall()
            return {row["key"]: row["value"] for row in rows}
    except Exception as e:
        logger.error(f"Failed to get settings: {e}")
        # Возвращаем значения по умолчанию в случае ошибки
        return {
            "check_interval": str(config.CHECK_INTERVAL),
            "notify_every_minutes": str(config.NOTIFY_EVERY_MINUTES),
        }