# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime, timedelta, timezone

import requests

from .. import config
from ..db import get_db_connection, get_settings
from .notifications import send_notifications

logger = logging.getLogger(__name__)


def check_endpoint_status_with_fallback(url: str) -> int:
    """Проверка статуса эндпоинта с автоматическим fallback с HTTPS на HTTP"""
    # Сначала пробуем оригинальный URL
    try:
        resp = requests.get(url, timeout=5)
        return resp.status_code
    except Exception as e:
        logger.debug(f"Primary attempt failed for {url}: {e}")

        # Если URL использует HTTPS, пробуем HTTP
        if url.startswith("https://"):
            http_url = url.replace("https://", "http://", 1)
            try:
                logger.info(f"Trying HTTP fallback for {url} -> {http_url}")
                resp = requests.get(http_url, timeout=5)
                logger.info(f"HTTP fallback successful for {http_url}")
                return resp.status_code
            except Exception as e2:
                logger.debug(f"HTTP fallback also failed for {http_url}: {e2}")

        return 0


def should_send_down_notification(
    last_notified: str, now_utc: datetime, settings: dict
) -> bool:
    """Проверяет, можно ли отправить уведомление о падении"""
    if not last_notified:
        return True

    try:
        last_notif_dt = datetime.fromisoformat(last_notified)
        time_diff = now_utc - last_notif_dt
        notify_interval = int(
            settings.get("notify_every_minutes", config.NOTIFY_EVERY_MINUTES)
        )
        return time_diff > timedelta(minutes=notify_interval)
    except Exception:
        return True


def update_notification_time(
    cur: requests.structures.CaseInsensitiveDict, endpoint_id: int, now_iso: str
) -> None:
    """Обновляет время последнего уведомления"""
    cur.execute(
        "UPDATE endpoints SET last_notified = ? WHERE id = ?",
        (now_iso, endpoint_id),
    )


def check_notification_needed(
    current_status: int,
    last_status: int,
    was_down: bool,
    last_notified: str,
    now_utc: datetime,
    url: str,
    endpoint_id: int,
    settings: dict,
) -> bool:
    """Определяет, нужно ли отправлять уведомление (only HTTP 200 is acceptable)"""
    is_down = current_status != 200
    is_recovered = was_down and not is_down
    just_went_down = not was_down and is_down

    # Уведомление о восстановлении
    if is_recovered:
        message = f"[OK] RECOVERED: {url} is back online (status: {current_status})\n\nDashboard: {config.DASHBOARD_URL}"
        send_notifications(message, url, endpoint_id)
        return True

    # Уведомление о падении (с учетом интервала)
    if is_down and should_send_down_notification(last_notified, now_utc, settings):
        if just_went_down:
            message = f"[ALERT] {url} is DOWN\n\nDashboard: {config.DASHBOARD_URL}"
            send_notifications(message, url, endpoint_id)
        else:
            message = f"[WARNING] STILL DOWN: {url} remains unavailable\n\nDashboard: {config.DASHBOARD_URL}"
            send_notifications(message, url, endpoint_id)
        return True

    return False


def check_endpoints_loop():
    """Основной цикл проверки эндпоинтов"""
    logger.info("Starting endpoint monitoring loop")

    while True:
        try:
            # Получаем актуальные настройки на каждой итерации
            current_settings = get_settings()
            check_interval = int(
                current_settings.get("check_interval", config.CHECK_INTERVAL)
            )

            # Дебаг-логирование для диагностики
            logger.info(
                f"Monitoring settings: check_interval={check_interval}, notify_every_minutes={current_settings.get('notify_every_minutes', config.NOTIFY_EVERY_MINUTES)}"
            )

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
                    current_status = check_endpoint_status_with_fallback(url)
                    now_utc = datetime.now(timezone.utc)
                    now_iso = now_utc.isoformat()

                    # Обновляем статус в БД (only HTTP 200 is acceptable)
                    is_currently_down = current_status != 200
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
                        endpoint_id,
                        current_settings,  # Передаем настройки
                    )

                    if should_notify:
                        update_notification_time(cur, endpoint_id, now_iso)

                conn.commit()
                logger.debug(f"Checked {len(rows)} endpoints")

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")

        # Используем интервал из настроек
        time.sleep(check_interval)
