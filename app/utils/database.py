"""Database connection and initialization utilities."""
import logging
import sqlite3
import threading
from contextlib import contextmanager

from app.utils.config import DB_PATH

logger = logging.getLogger(__name__)

# Thread-local storage for database connections
local_storage = threading.local()


@contextmanager
def get_db_connection():
    """Context manager for thread-safe database connections."""
    if not hasattr(local_storage, "connection"):
        try:
            local_storage.connection = sqlite3.connect(
                DB_PATH, timeout=20.0, check_same_thread=False
            )
            local_storage.connection.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    conn = local_storage.connection
    try:
        yield conn
    except Exception as e:
        logger.error(f"Database operation error: {e}")
        raise


def init_db():
    """Initialize the database schema."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            # Create endpoints table
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

            # Check and add missing columns
            cur.execute("PRAGMA table_info(endpoints)")
            columns = [column[1] for column in cur.fetchall()]

            if "is_down" not in columns:
                logger.info("Adding is_down column to endpoints table")
                cur.execute(
                    "ALTER TABLE endpoints ADD COLUMN is_down BOOLEAN DEFAULT FALSE"
                )

            if "name" not in columns:
                logger.info("Adding name column to endpoints table")
                cur.execute("ALTER TABLE endpoints ADD COLUMN name TEXT")

            # Create unique index
            try:
                cur.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_endpoints_url ON endpoints(url)"
                )
            except Exception as e:
                logger.warning(f"Could not create unique index: {e}")

            # Create notification_logs table
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


def close_db_connections():
    """Close all database connections for the current thread."""
    if hasattr(local_storage, "connection"):
        try:
            local_storage.connection.close()
            delattr(local_storage, "connection")
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
