# -*- coding: utf-8 -*-
import os

from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Настройки базы данных
DB_PATH = os.getenv("DB_PATH", "endpoints.db")

# Настройки мониторинга
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 10))
NOTIFY_EVERY_MINUTES = int(os.getenv("NOTIFY_EVERY_MINUTES", 2))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 5))
DOUBLE_CHECK_DELAY = int(os.getenv("DOUBLE_CHECK_DELAY", 5))

# Настройки веб-интерфейса
INDEX_PAGE = os.getenv("INDEX_PAGE", "index2.html")

# Настройки NTFY
NTFY_SERVER = os.getenv("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "default_topic")
NTFY_ENABLED = os.getenv("NTFY_ENABLED", "False").lower() in ("true", "1", "t")

# Настройки Telegram (индивидуальные уведомления)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_MESSAGE_THREAD_ID = os.getenv("TELEGRAM_MESSAGE_THREAD_ID", "")
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "False").lower() in ("true", "1", "t")
TELEGRAM_DISCOVERY_ENABLED = os.getenv(
    "TELEGRAM_DISCOVERY_ENABLED", "True"
).lower() in ("true", "1", "t")
TELEGRAM_DISCOVERY_TIMEOUT = int(os.getenv("TELEGRAM_DISCOVERY_TIMEOUT", 600))
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "OqylyqTeamBot")

# Настройки Telegram (групповые уведомления)
TELEGRAM_GROUP_ENABLED = os.getenv("TELEGRAM_GROUP_ENABLED", "False").lower() in (
    "true",
    "1",
    "t",
)
TELEGRAM_GROUP_CHAT_ID = os.getenv("TELEGRAM_GROUP_CHAT_ID", "")
TELEGRAM_GROUP_THREAD_ID = os.getenv("TELEGRAM_GROUP_THREAD_ID", "")

# Настройки URL и API
URL = os.getenv("URL", "localhost")
PORT = int(os.getenv("PORT", 5000))
# Используем переменные из .env или формируем по умолчанию
API_BASE = os.getenv("API_BASE", f"http://{URL}:{PORT}/api/endpoints")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", f"http://{URL}:{PORT}")

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
