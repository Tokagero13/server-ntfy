# Endpoint Monitoring

This application monitors HTTP(S) endpoints and sends notifications via [ntfy.sh](https://ntfy.sh/) and Telegram.

## Features

- Periodic health checks for arbitrary HTTP(S) endpoints
- Configurable check interval and notification throttling
- Notifications via ntfy topics and Telegram bot
- Simple web dashboard (HTML/JS) for endpoint status
- REST API with documentation powered by Flask-RESTx

## Project structure

The project is organized as a Python package `app` for better modularity and maintainability.

```
.
├── app/
│   ├── api/                  # Flask-RESTx endpoint modules
│   │   ├── __init__.py
│   │   ├── endpoints.py
│   │   ├── notifications.py
│   │   ├── settings.py
│   │   └── telegram.py
│   ├── core/                 # Core business logic
│   │   ├── __init__.py
│   │   ├── monitoring.py     # Endpoint check logic
│   │   ├── notifications.py  # Notification sending logic
│   │   └── telegram_bot.py   # Telegram bot logic
│   ├── db.py                 # SQLite database helpers
│   ├── __init__.py           # Flask application factory
│   ├── config.py             # Centralized configuration
│   └── models.py             # Flask-RESTx API models
├── static/                   # Static files (HTML, CSS, JS)
├── templates/                # Templates (if used)
├── .env                      # Environment variables
├── example.env               # Example .env file
├── gunicorn.conf.py          # Gunicorn configuration
├── run.py                    # Local development script
├── wsgi.py                   # Entry point for WSGI servers
├── requirements.txt          # Project dependencies
└── README.md                 # This file
```

Key entry points and files:

- [`run.py`](run.py) – local development entry point (debug + background tasks)
- [`wsgi.py`](wsgi.py) – WSGI/ASGI entry point for production
- [`gunicorn.conf.py`](gunicorn.conf.py) – sample Gunicorn configuration
- [`requirements.txt`](requirements.txt) – Python dependencies
- [`example.env`](example.env) – example environment configuration
- [`index2.html`](index2.html) – default dashboard page (served from `static/`)

## Installation and run

### 1. Install dependencies

Use Python 3.10+ and install the required packages with pip:

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root (you can copy it from [`example.env`](example.env)) and set the required variables:

```dotenv
# .env
DB_PATH=endpoints.db              # SQLite database file
CHECK_INTERVAL=10                 # Check interval in seconds
NOTIFY_EVERY_MINUTES=2            # Minimum minutes between notifications for the same endpoint
INDEX_PAGE=index2.html            # Dashboard HTML file

# NTFY
NTFY_SERVER=https://ntfy.sh       # ntfy server URL
NTFY_TOPIC=my_monitor_topic       # ntfy topic name
NTFY_ENABLED=True                 # Enable/disable ntfy notifications

# Telegram
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_TELEGRAM_CHAT_ID      # Can be discovered via the API
TELEGRAM_ENABLED=True                        # Enable/disable Telegram notifications
TELEGRAM_DISCOVERY_ENABLED=True              # Allow automatic chat ID discovery
TELEGRAM_DISCOVERY_TIMEOUT=600               # Discovery timeout in seconds
TELEGRAM_BOT_USERNAME=YourMonitorBot         # Bot username

# App URL / port
URL=0.0.0.0
PORT=5000
# API_BASE and DASHBOARD_URL are generated automatically if not specified
```

Only a subset of these variables is strictly required (for example, ntfy or Telegram blocks can be disabled by setting `*_ENABLED=False`), but the above example shows a typical configuration.

### 3. Run the application

#### Local development (with hot reload)

Use [`run.py`](run.py). This script starts Flask in debug mode and also runs background tasks (monitoring, Telegram bot):

```bash
python run.py
```

The app will reload automatically when you change Python files.

#### Production (Gunicorn / Uvicorn)

Use [`wsgi.py`](wsgi.py) as the entry point. Gunicorn (recommended for Linux/macOS) or Uvicorn (recommended for Windows) will start the application and background tasks in separate threads.

**Run with Gunicorn (Linux/macOS):**

```bash
# Use configuration from gunicorn.conf.py
gunicorn -c gunicorn.conf.py wsgi:application

# Or run directly
gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:application
```

**Run with Uvicorn (Windows / cross-platform):**

```bash
# Basic run (recommended for Windows)
uvicorn wsgi:application --host 0.0.0.0 --port 5000

# For scaling on Windows, use a process manager like PM2 (see its docs)
# Do NOT use --workers > 1 with Uvicorn on Windows due to socket issues.
```

### 4. Accessing the application

Once started, the application is available at:

- Web UI: `http://<YOUR_URL>:<YOUR_PORT>/`
- API docs: `http://<YOUR_URL>:<YOUR_PORT>/api/docs`

The exact dashboard page is controlled by `INDEX_PAGE` in your `.env` file (by default [`index2.html`](index2.html)).

## Telegram notifications

The application can send notifications to Telegram, both to individual chats and to group chats.

### 1. Basic (individual) Telegram notifications

To enable basic Telegram notifications (direct messages to a user or a private/group chat), configure the following variables in your `.env`:

```dotenv
# Telegram basic notifications
TELEGRAM_ENABLED=True
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_TELEGRAM_CHAT_ID
```

- `TELEGRAM_BOT_TOKEN` – bot token obtained from @BotFather.
- `TELEGRAM_CHAT_ID` – chat ID where messages will be sent. You can use a user ID (for direct messages) or a chat/group ID (for group chats).

If `TELEGRAM_ENABLED=False`, Telegram notifications are disabled (only ntfy or other channels will be used).

> The application can automatically discover `TELEGRAM_CHAT_ID` if `TELEGRAM_DISCOVERY_ENABLED=True` and the bot is running. Discovery is limited by `TELEGRAM_DISCOVERY_TIMEOUT` (in seconds).

Typical configuration:

```dotenv
TELEGRAM_ENABLED=True
TELEGRAM_DISCOVERY_ENABLED=True
TELEGRAM_DISCOVERY_TIMEOUT=600
TELEGRAM_BOT_USERNAME=YourMonitorBot
```

With this setup, you can start the bot, send it a message from the desired chat, and let the application discover the chat ID.

### 2. Telegram group notifications

In addition to basic Telegram notifications, the system supports dedicated **group notifications** for Telegram channels and groups (including forum-style groups with topics).

This is configured separately so you can:

- send standard alerts to a private chat, and
- simultaneously send more detailed alerts to a group used by your team.

#### 2.1. Bot and group setup

1. Create a bot via @BotFather and obtain the bot token.
2. Add the bot to the target group.
3. Make the bot an administrator with permission to send messages.

#### 2.2. Getting the group chat ID

To get the (negative) group chat ID:

1. Add the bot [@userinfobot](https://t.me/userinfobot) to the group.
2. Send `/start` in the group.
3. `@userinfobot` will print the group info, including the `chat_id`.
4. The group ID should be negative, for example `-1003075012272`.

#### 2.3. Getting a topic (thread) ID for forum groups (optional)

If your group is configured as a forum with topics:

1. Open the topic where you want to receive notifications.
2. Copy the link to the topic.
3. The topic ID is the number after `_` in the URL. For example, `https://t.me/c/1003075012272/1` → topic ID: `1`.

You can then use this ID as `TELEGRAM_GROUP_THREAD_ID`.

#### 2.4. Environment variables for group notifications

Add the following variables to your `.env`:

```dotenv
# Telegram bot token (same bot as used for basic notifications)
TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

# Group notifications
TELEGRAM_GROUP_ENABLED=True
TELEGRAM_GROUP_CHAT_ID=-1003075012272
TELEGRAM_GROUP_THREAD_ID=1    # optional, for forum topics
```

Parameters:

| Variable                    | Description                             | Required | Example          |
|----------------------------|-----------------------------------------|----------|------------------|
| `TELEGRAM_BOT_TOKEN`       | Bot token from @BotFather               | ✅       | `1234:AAH...`    |
| `TELEGRAM_GROUP_ENABLED`   | Enable/disable group notifications      | ✅       | `True`           |
| `TELEGRAM_GROUP_CHAT_ID`   | Group chat ID (negative)                | ✅       | `-1003075012272` |
| `TELEGRAM_GROUP_THREAD_ID` | Topic/thread ID for forum-style groups | ❌       | `1`              |

To disable group notifications only:

```dotenv
TELEGRAM_GROUP_ENABLED=False
```

### 3. How it works in the application

When an endpoint check fails (or recovers), the application calls its internal notification dispatcher, which sends messages to all configured channels:

- ntfy (if `NTFY_ENABLED=True`),
- basic Telegram notifications (if `TELEGRAM_ENABLED=True`),
- Telegram group notifications (if `TELEGRAM_GROUP_ENABLED=True`).

Messages sent to groups are formatted with:

- an emoji indicator,
- a bold header,
- HTML formatting,
- a clickable link to the failing endpoint.

A typical group alert may look like:

```text
🔔 Monitoring group alert

❌ Endpoint https://api.example.com/health is unavailable
Status: 500 Internal Server Error
Time: 2024-12-12 12:25:43 UTC

🔗 https://api.example.com/health
```

### 4. Troubleshooting Telegram setup

If the bot cannot send messages:

1. **Check bot permissions**
   - Is the bot added to the group?
   - Does the bot have permission to send messages?

2. **Check configuration**
   - Is `TELEGRAM_GROUP_ENABLED` set to `True`?
   - Is `TELEGRAM_GROUP_CHAT_ID` negative and correct?
   - Is `TELEGRAM_BOT_TOKEN` valid?

3. **Check topic (if used)**
   - Does the topic exist?
   - Is `TELEGRAM_GROUP_THREAD_ID` correct?

For more detailed examples and architecture diagrams, see [`docs/telegram-group-notifications.md`](docs/telegram-group-notifications.md).

### 5. Testing (optional)

Basic tests are located in [`test_group_notifications.py`](test_group_notifications.py). To run them:

```bash
python -m pytest -q
```

### 6. Server configuration

See [`gunicorn.conf.py`](gunicorn.conf.py) for Gunicorn settings and tuning options (workers, timeouts, logging, etc.).

---

This README describes the current project structure, environment variables, and unified instructions for running the application in development and production.
