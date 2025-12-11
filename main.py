"""
Endpoint Watchdog - HTTP/HTTPS endpoint monitoring service.

This application monitors HTTP endpoints and sends notifications via NTFY and Telegram
when endpoints go down or recover. Includes graceful shutdown support.
"""
import logging
import signal
import sys

from flask import Flask
from flask_restx import Api

from app.models.api_models import register_models
from app.routes.endpoints import create_endpoints_namespace
from app.routes.notifications import create_notifications_namespace
from app.services.monitor import start_monitoring, stop_monitoring
from app.utils.config import INDEX_PAGE, NTFY_SERVER, NTFY_TOPIC, PORT, URL
from app.utils.database import close_db_connections, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Flask application
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Flask-RESTX API configuration
api = Api(
    app,
    version="1.0.0",
    title="Endpoints Monitor API",
    description="API for endpoint monitoring with NTFY and Telegram notifications",
    doc="/docs/",
    prefix="/api",
    ordered=True,
    validate=True,
)

# Register API models
models = register_models(api)

# Create and register namespaces
endpoints_ns = create_endpoints_namespace(api, models)
notifications_ns = create_notifications_namespace(api, models)
api.add_namespace(endpoints_ns)
api.add_namespace(notifications_ns)


# Main page route
@app.route('/')
def index():
    """Serve the main dashboard page."""
    with open(INDEX_PAGE, 'r', encoding='utf-8') as f:
        template = f.read()

    template = template.replace('{ntfy_server}', NTFY_SERVER)
    template = template.replace('{topic}', NTFY_TOPIC)

    return template


# CORS middleware
@app.after_request
def after_request(response):
    """Add CORS headers to all responses."""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# Global reference to monitor thread
monitor_thread = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")

    # Stop monitoring thread
    stop_monitoring(monitor_thread, timeout=10)

    # Close database connections
    close_db_connections()

    logger.info("Shutdown complete")
    sys.exit(0)


def main():
    """Main entry point with graceful shutdown support."""
    global monitor_thread

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Docker/systemd stop

    logger.info("Initializing Endpoint Watchdog...")

    # Initialize database
    init_db()

    # Start monitoring thread
    monitor_thread = start_monitoring()

    # Start Flask server
    logger.info(f"Starting Flask server on {URL}:{PORT}")
    try:
        app.run(host=URL, port=PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
