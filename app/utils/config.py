"""Configuration management for the application."""
import os
from dotenv import load_dotenv

load_dotenv()

# Database
DB_PATH = os.getenv('DB_PATH', 'endpoints.db')

# Monitoring
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 10))
NOTIFY_EVERY_MINUTES = int(os.getenv('NOTIFY_EVERY_MINUTES', 2))

# UI
INDEX_PAGE = os.getenv('INDEX_PAGE', 'index2.html')

# NTFY Service
NTFY_TOPIC = os.getenv('NTFY_TOPIC', 'default_topic')
NTFY_SERVER = os.getenv('NTFY_SERVER', 'https://ntfy.server')

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Server
URL = os.getenv('URL', 'localhost')
PORT = int(os.getenv('PORT', 5000))

# API
API_BASE = os.getenv('API_BASE', f'http://{URL}:{PORT}/api/endpoints')
DASHBOARD_URL = os.getenv('DASHBOARD_URL', f'{URL}:{PORT}')
