import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Создаем директории для логов если их нет
log_dir = "log/gunicorn"
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

# Используем переменные окружения
URL = os.getenv('URL', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

bind = f"{URL}:{PORT}"
workers = 1
worker_class = "sync"  # or "gevent" for async
loglevel = "info"
errorlog = "log/gunicorn/error.log"
accesslog = "log/gunicorn/access.log"
