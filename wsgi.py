"""WSGI entry point for production servers (Gunicorn, uWSGI, etc.)."""
import logging
import signal

from app.services.monitor import start_monitoring, stop_monitoring
from app.utils.database import close_db_connections, init_db
from main import app

logger = logging.getLogger(__name__)

# Initialize database
init_db()

# Start monitoring thread
monitor_thread = start_monitoring()


def cleanup_on_shutdown(signum=None, frame=None):
    """Clean up resources on shutdown."""
    logger.info("WSGI cleanup initiated")
    stop_monitoring(monitor_thread, timeout=10)
    close_db_connections()


# Register cleanup for common signals
signal.signal(signal.SIGTERM, cleanup_on_shutdown)
signal.signal(signal.SIGINT, cleanup_on_shutdown)

if __name__ == "__main__":
    app.run()
