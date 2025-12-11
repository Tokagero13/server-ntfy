"""Notification services for NTFY and Telegram."""
import logging
from datetime import datetime, timezone

import requests

from app.utils.config import (
    NTFY_SERVER,
    NTFY_TOPIC,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)
from app.utils.database import get_db_connection

logger = logging.getLogger(__name__)


def send_telegram_notification(message: str, endpoint_url: str) -> bool:
    """Send notification via Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    try:
        telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        resp = requests.post(telegram_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info(f"Telegram notification sent: {message}")
            return True
        else:
            logger.warning(
                f"Telegram notification failed with status {resp.status_code}: {resp.text}"
            )
            return False
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False


def send_ntfy_notification(topic: str, message: str, endpoint_url: str) -> None:
    """Send notification via NTFY and Telegram, log to database."""
    # Send via NTFY
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    ntfy_success = False
    try:
        resp = requests.post(url, data=message.encode("utf-8"), timeout=5)
        if resp.status_code == 200:
            logger.info(f"NTFY notification sent: {message}")
            ntfy_success = True
        else:
            logger.warning(
                f"NTFY notification failed with status {resp.status_code}: {message}"
            )
    except Exception as e:
        logger.error(f"Failed to send NTFY notification: {e}")

    # Send via Telegram
    telegram_success = send_telegram_notification(message, endpoint_url)

    # Notification succeeds if at least one channel works
    log_status = "sent" if (ntfy_success or telegram_success) else "failed"

    # Log to database
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
