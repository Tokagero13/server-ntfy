"""Endpoint monitoring service with graceful shutdown support."""
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import requests

from app.services.notifications import send_ntfy_notification
from app.utils.config import CHECK_INTERVAL, DASHBOARD_URL, NOTIFY_EVERY_MINUTES, NTFY_TOPIC
from app.utils.database import get_db_connection

logger = logging.getLogger(__name__)

# Global shutdown event for graceful termination
shutdown_event = threading.Event()


def check_endpoint_status_with_fallback(url: str) -> int:
    """Check endpoint status with automatic HTTPS->HTTP fallback."""
    try:
        resp = requests.get(url, timeout=5)
        return resp.status_code
    except Exception as e:
        logger.debug(f"Primary attempt failed for {url}: {e}")

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


def check_endpoint_status(url: str) -> int:
    """Check status of a single endpoint."""
    return check_endpoint_status_with_fallback(url)


def should_send_down_notification(last_notified: str, now_utc: datetime) -> bool:
    """Check if down notification should be sent based on rate limiting."""
    if not last_notified:
        return True

    try:
        last_notif_dt = datetime.fromisoformat(last_notified)
        time_diff = now_utc - last_notif_dt
        return time_diff > timedelta(minutes=NOTIFY_EVERY_MINUTES)
    except Exception:
        return True


def check_notification_needed(
    current_status: int,
    last_status: int,
    was_down: bool,
    last_notified: str,
    now_utc: datetime,
    url: str,
) -> bool:
    """Determine if notification should be sent (only HTTP 200 is acceptable)."""
    is_down = current_status != 200
    is_recovered = was_down and not is_down
    just_went_down = not was_down and is_down

    # Recovery notification
    if is_recovered:
        message = f"[OK] RECOVERED: {url} is back online (status: {current_status})\n\nDashboard: {DASHBOARD_URL}"
        send_ntfy_notification(NTFY_TOPIC, message, url)
        return True

    # Down notification (with rate limiting)
    if is_down and should_send_down_notification(last_notified, now_utc):
        if just_went_down:
            message = f"[ALERT] {url} is DOWN\n\nDashboard: {DASHBOARD_URL}"
            send_ntfy_notification(NTFY_TOPIC, message, url)
        else:
            message = f"[WARNING] STILL DOWN: {url} remains unavailable\n\nDashboard: {DASHBOARD_URL}"
            send_ntfy_notification(NTFY_TOPIC, message, url)
        return True

    return False


def update_notification_time(cur, endpoint_id: int, now_iso: str) -> None:
    """Update last notification timestamp for an endpoint."""
    cur.execute(
        "UPDATE endpoints SET last_notified = ? WHERE id = ?",
        (now_iso, endpoint_id),
    )


def check_endpoints_loop():
    """Main monitoring loop with graceful shutdown support."""
    logger.info("Starting endpoint monitoring loop")

    while not shutdown_event.is_set():
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, name, url, last_status, last_checked, last_notified, is_down FROM endpoints"
                )
                rows = cur.fetchall()

                for row in rows:
                    # Check shutdown event before processing each endpoint
                    if shutdown_event.is_set():
                        logger.info("Shutdown requested, stopping endpoint checks")
                        break

                    endpoint_id = row["id"]
                    name = row["name"]
                    url = row["url"]
                    last_status = row["last_status"]
                    last_notified = row["last_notified"]
                    was_down = row["is_down"] or False

                    # Check endpoint status
                    current_status = check_endpoint_status(url)
                    now_utc = datetime.now(timezone.utc)
                    now_iso = now_utc.isoformat()

                    # Update status (only HTTP 200 is acceptable)
                    is_currently_down = current_status != 200
                    cur.execute(
                        """
                        UPDATE endpoints
                        SET last_status = ?, last_checked = ?, is_down = ?
                        WHERE id = ?
                        """,
                        (current_status, now_iso, is_currently_down, endpoint_id),
                    )

                    # Check if notification needed
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

        # Sleep with shutdown check
        for _ in range(CHECK_INTERVAL):
            if shutdown_event.is_set():
                break
            time.sleep(1)

    logger.info("Endpoint monitoring loop stopped")


def start_monitoring():
    """Start the monitoring thread."""
    monitor_thread = threading.Thread(target=check_endpoints_loop, daemon=False, name="MonitorThread")
    monitor_thread.start()
    logger.info("Monitoring thread started")
    return monitor_thread


def stop_monitoring(monitor_thread=None, timeout=10):
    """Stop the monitoring thread gracefully."""
    logger.info("Stopping monitoring thread...")
    shutdown_event.set()

    if monitor_thread and monitor_thread.is_alive():
        monitor_thread.join(timeout=timeout)
        if monitor_thread.is_alive():
            logger.warning(f"Monitoring thread did not stop within {timeout} seconds")
        else:
            logger.info("Monitoring thread stopped successfully")
