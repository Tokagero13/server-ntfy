# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timezone

import requests

from .. import config
from ..db import get_db_connection
from .group_notifications import send_group_notification

logger = logging.getLogger(__name__)


def get_endpoint_subscriptions(endpoint_id: int) -> list:
    """Получает список подписок для эндпоинта"""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT chat_id FROM endpoint_subscriptions
                WHERE endpoint_id = ? AND enabled = 1
            """,
                (endpoint_id,),
            )
            return [row[0] for row in cur.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get endpoint subscriptions: {e}")
        return []


def send_telegram_notification(
    message: str, endpoint_url: str, endpoint_id: int = None
) -> bool:
    """Отправка уведомления через Telegram Bot API с поддержкой подписок"""
    if not config.TELEGRAM_BOT_TOKEN:
        return False

    # Получаем индивидуальные подписки для эндпоинта
    individual_chats = []
    if endpoint_id:
        individual_chats = get_endpoint_subscriptions(endpoint_id)

    # Объединяем все чаты для отправки
    configured_chats = [
        int(chat_id.strip())
        for chat_id in config.TELEGRAM_CHAT_ID.split(",")
        if chat_id.strip()
    ]
    target_chats = list(set(individual_chats + configured_chats))

    if not target_chats:
        logger.warning("No target chats for Telegram notification")
        return False

    success_count = 0
    telegram_url = (
        f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    for chat_id in target_chats:
        try:
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            if config.TELEGRAM_MESSAGE_THREAD_ID:
                payload["message_thread_id"] = int(config.TELEGRAM_MESSAGE_THREAD_ID)

            resp = requests.post(telegram_url, json=payload, timeout=10)
            if resp.status_code == 200:
                logger.info(
                    f"Telegram notification sent to chat_id {chat_id}"
                    + (
                        f" (thread {config.TELEGRAM_MESSAGE_THREAD_ID})"
                        if config.TELEGRAM_MESSAGE_THREAD_ID
                        else ""
                    )
                    + f": {message}"
                )
                success_count += 1
            else:
                logger.warning(
                    f"Telegram notification to {chat_id} failed with status {resp.status_code}: {resp.text}"
                )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification to {chat_id}: {e}")

    return success_count > 0


def send_ntfy_notification(message: str) -> bool:
    """Отправка уведомления через ntfy"""
    if not config.NTFY_ENABLED:
        return False

    url = f"{config.NTFY_SERVER}/{config.NTFY_TOPIC}"
    try:
        resp = requests.post(url, data=message.encode("utf-8"), timeout=5)
        if resp.status_code == 200:
            logger.info(f"NTFY notification sent: {message}")
            return True
        else:
            logger.warning(
                f"NTFY notification failed with status {resp.status_code}: {message}"
            )
            return False
    except Exception as e:
        logger.error(f"Failed to send NTFY notification: {e}")
        return False


def send_group_telegram_notification(message: str, endpoint_url: str) -> bool:
    """Отправка уведомления в групповой чат через python-telegram-bot"""
    if not config.TELEGRAM_GROUP_ENABLED:
        return False

    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not configured for group notifications")
        return False

    if not config.TELEGRAM_GROUP_CHAT_ID:
        logger.warning("TELEGRAM_GROUP_CHAT_ID not configured for group notifications")
        return False

    try:
        success = send_group_notification(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_GROUP_CHAT_ID,
            message=message,
            endpoint_url=endpoint_url,
            thread_id=config.TELEGRAM_GROUP_THREAD_ID,
        )

        if success:
            logger.info(f"Group notification sent successfully: {message[:50]}...")
        else:
            logger.warning("Group notification failed to send")

        return success

    except Exception as e:
        logger.error(f"Error sending group notification: {e}")
        return False


def send_notifications(message: str, endpoint_url: str, endpoint_id: int = None):
    """Диспетчер уведомлений, который отправляет сообщения по включенным каналам."""
    # NTFY уведомления
    ntfy_success = False
    if config.NTFY_ENABLED:
        ntfy_success = send_ntfy_notification(message)

    # Индивидуальные Telegram уведомления (через requests API)
    telegram_success = False
    if config.TELEGRAM_ENABLED:
        telegram_success = send_telegram_notification(
            message, endpoint_url, endpoint_id
        )

    # Групповые Telegram уведомления (через python-telegram-bot)
    group_success = False
    if config.TELEGRAM_GROUP_ENABLED:
        group_success = send_group_telegram_notification(message, endpoint_url)

    # Логирование в БД
    any_success = any([ntfy_success, telegram_success, group_success])
    log_status = "sent" if any_success else "failed"

    # Добавляем информацию о каналах в лог
    channels_info = []
    if config.NTFY_ENABLED:
        channels_info.append(f"NTFY: {'✓' if ntfy_success else '✗'}")
    if config.TELEGRAM_ENABLED:
        channels_info.append(f"Telegram: {'✓' if telegram_success else '✗'}")
    if config.TELEGRAM_GROUP_ENABLED:
        channels_info.append(f"Group: {'✓' if group_success else '✗'}")

    channels_status = (
        " | ".join(channels_info) if channels_info else "No channels enabled"
    )
    logger.info(f"Notification dispatch complete: {channels_status}")

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notification_logs (timestamp, endpoint_url, message, status) VALUES (?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(),
                    endpoint_url,
                    message,
                    log_status,
                ),
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log notification: {e}")
