# Мониторинг эндпоинтов

Это приложение для мониторинга HTTP(S) эндпоинтов с уведомлениями через [ntfy.sh](https://ntfy.sh/) и Telegram.

## Структура проекта

Проект организован в виде пакета Python `app` для лучшей модульности и поддержки.

```
.
├── app/
│   ├── api/                  # Модули с Flask-RESTx эндпоинтами
│   │   ├── __init__.py
│   │   ├── endpoints.py
│   │   ├── notifications.py
│   │   ├── settings.py
│   │   └── telegram.py
│   ├── core/                 # Основная бизнес-логика
│   │   ├── __init__.py
│   │   ├── monitoring.py     # Логика проверки эндпоинтов
│   │   ├── notifications.py  # Логика отправки уведомлений
│   │   └── telegram_bot.py   # Логика Telegram бота
│   ├── db.py                 # Функции для работы с базой данных (SQLite)
│   ├── __init__.py           # Фабрика Flask приложения
│   ├── config.py             # Централизованная конфигурация
│   └── models.py             # Модели Flask-RESTx для API
├── static/                   # Статические файлы (HTML, CSS, JS)
├── templates/                # Шаблоны (если используются)
├── .env                      # Переменные окружения
├── example.env               # Пример файла .env
├── gunicorn.conf.py          # Конфигурация Gunicorn
├── run.py                    # Скрипт для локальной разработки
├── wsgi.py                   # Точка входа для WSGI серверов
├── requirements.txt          # Зависимости проекта
└── README.md                 # Этот файл
```

## Установка и запуск

### 1. Установка зависимостей

Установите необходимые пакеты с помощью pip:

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта (можно скопировать из `example.env`) и укажите необходимые переменные:

```dotenv
# .env
DB_PATH=endpoints.db
CHECK_INTERVAL=10
NOTIFY_EVERY_MINUTES=2
INDEX_PAGE=index2.html

# NTFY
NTFY_SERVER=https://ntfy.sh
NTFY_TOPIC=my_monitor_topic
NTFY_ENABLED=True

# Telegram
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_TELEGRAM_CHAT_ID # Может быть обнаружен через API
TELEGRAM_ENABLED=True
TELEGRAM_DISCOVERY_ENABLED=True
TELEGRAM_DISCOVERY_TIMEOUT=600 # Секунды
TELEGRAM_BOT_USERNAME=YourMonitorBot

# App URL
URL=0.0.0.0
PORT=5000
# API_BASE и DASHBOARD_URL будут сформированы автоматически, если не указаны
```

### 3. Запуск приложения

#### Для локальной разработки (с hot-reload):

Используйте `run.py`. Этот скрипт запускает Flask с отладочным режимом и фоновые задачи (мониторинг, Telegram бот).

```bash
python run.py
```

#### Для продакшена (с Gunicorn/Uvicorn):

Используйте [`wsgi.py`](wsgi.py) как точку входа. Gunicorn (рекомендуется для Linux/macOS) или Uvicorn (рекомендуется для Windows) запустят приложение и фоновые задачи в отдельных потоках.

**Запуск с Gunicorn (Linux/macOS):**

```bash
# Запуск с конфигурацией из gunicorn.conf.py
gunicorn -c gunicorn.conf.py wsgi:application

# Или напрямую
gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:application
```

**Запуск с Uvicorn (Windows/Cross-platform):**

```bash
# Базовый запуск (рекомендуется для Windows)
uvicorn wsgi:application --host 0.0.0.0 --port 5000

# Для масштабирования на Windows используйте PM2 (см. ниже)
# НЕ используйте --workers > 1 с Uvicorn на Windows из-за проблем с сокетами.
```

### 4. Доступ к приложению

После запуска приложение будет доступно по адресу `http://<YOUR_URL>:<YOUR_PORT>`.
API документация доступна по адресу `http://<YOUR_URL>:<YOUR_PORT>/api/docs`.

### 5. Конфигурация серверов

См. [`gunicorn.conf.py`](gunicorn.conf.py) для настроек Gunicorn.

---

Это обновление включает новую структуру, унифицированные инструкции по запуску для разработки и продакшена, а также обновленные переменные окружения.