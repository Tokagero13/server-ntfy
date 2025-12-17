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
        resp = requests.get(url, timeout=config.REQUEST_TIMEOUT)
        return resp.status_code
    except Exception as e:
        logger.debug(f"Primary attempt failed for {url}: {e}")

        # Если URL использует HTTPS, пробуем HTTP
        if url.startswith("https://"):
            http_url = url.replace("https://", "http://", 1)
            try:
                logger.info(f"Trying HTTP fallback for {url} -> {http_url}")
                resp = requests.get(http_url, timeout=config.REQUEST_TIMEOUT)
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


def check_endpoints_loop():
    """Основной цикл проверки эндпоинтов"""
    logger.info("Starting endpoint monitoring loop")

    while True:
        try:
            current_settings = get_settings()
            check_interval = int(
                current_settings.get("check_interval", config.CHECK_INTERVAL)
            )
            logger.info(
                f"Monitoring settings: check_interval={check_interval}, notify_every_minutes={current_settings.get('notify_every_minutes', config.NOTIFY_EVERY_MINUTES)}, request_timeout={config.REQUEST_TIMEOUT}, double_check_delay={config.DOUBLE_CHECK_DELAY}"
            )

            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, url, last_status, last_notified, is_down FROM endpoints"
                )
                endpoints = cur.fetchall()

                for endpoint in endpoints:
                    endpoint_id = endpoint["id"]
                    url = endpoint["url"]
                    was_down = endpoint["is_down"]
                    last_notified = endpoint["last_notified"]
                    now_utc = datetime.now(timezone.utc)
                    now_iso = now_utc.isoformat()

                    current_status = check_endpoint_status_with_fallback(url)
                    is_currently_down = current_status != 200

                    # Сначала обновляем только время последней проверки и статус ответа
                    cur.execute(
                        "UPDATE endpoints SET last_status = ?, last_checked = ? WHERE id = ?",
                        (current_status, now_iso, endpoint_id),
                    )

                    # Сценарий 1: Эндпоинт восстановился
                    if not is_currently_down and was_down:
                        logger.info(f"Endpoint {url} has recovered.")
                        message = f"[OK] RECOVERED: {url} is back online (status: {current_status})\n\nDashboard: {config.DASHBOARD_URL}"
                        send_notifications(message, url, endpoint_id)
                        # Обновляем статус и время уведомления
                        cur.execute(
                            "UPDATE endpoints SET is_down = ?, last_notified = ? WHERE id = ?",
                            (False, now_iso, endpoint_id),
                        )

                    # Сценарий 2: Эндпоинт упал (и это новое падение)
                    elif is_currently_down and not was_down:
                        logger.warning(
                            f"Endpoint {url} appears to be down. Performing double check..."
                        )
                        time.sleep(config.DOUBLE_CHECK_DELAY)
                        status_after_delay = check_endpoint_status_with_fallback(url)

                        # Обновляем last_status после второй проверки
                        cur.execute(
                            "UPDATE endpoints SET last_status = ? WHERE id = ?",
                            (status_after_delay, endpoint_id),
                        )

                        if status_after_delay != 200:
                            logger.error(
                                f"Endpoint {url} is confirmed DOWN after double check."
                            )
                            # Только теперь обновляем статус is_down в БД
                            cur.execute(
                                "UPDATE endpoints SET is_down = ? WHERE id = ?",
                                (True, endpoint_id),
                            )
                            if should_send_down_notification(
                                last_notified, now_utc, current_settings
                            ):
                                message = f"[ALERT] {url} is DOWN (status: {status_after_delay})\n\nDashboard: {config.DASHBOARD_URL}"
                                send_notifications(message, url, endpoint_id)
                                update_notification_time(cur, endpoint_id, now_iso)
                        else:
                            logger.info(
                                f"Endpoint {url} recovered during double check. No notification sent."
                            )
                            # Статус is_down не меняем, он остается False

                    # Сценарий 3: Эндпоинт все еще лежит
                    elif is_currently_down and was_down:
                        if should_send_down_notification(
                            last_notified, now_utc, current_settings
                        ):
                            logger.warning(f"Endpoint {url} is STILL DOWN.")
                            message = f"[WARNING] STILL DOWN: {url} remains unavailable (status: {current_status})\n\nDashboard: {config.DASHBOARD_URL}"
                            send_notifications(message, url, endpoint_id)
                            update_notification_time(cur, endpoint_id, now_iso)

                conn.commit()
                logger.debug(f"Checked {len(endpoints)} endpoints")

        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)

        time.sleep(check_interval)
