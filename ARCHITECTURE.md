# Architecture Documentation

## Project Structure

```
server-ntfy/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── api_models.py          # Flask-RESTX API model definitions
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── endpoints.py           # Endpoint management API routes
│   │   └── notifications.py       # Notification logs API routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── monitor.py            # Endpoint monitoring service
│   │   └── notifications.py      # NTFY and Telegram notification services
│   └── utils/
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       ├── database.py            # Database connection and initialization
│       └── validators.py          # URL validation utilities
├── static/
│   ├── components/               # Web components
│   ├── script.js                # Frontend JavaScript
│   └── style.css                # Styles
├── main.py                       # Application entry point
├── wsgi.py                       # WSGI entry point for production
├── gunicorn.conf.py              # Gunicorn configuration
├── example.env                   # Environment variables template
└── index2.html                   # Dashboard UI

## Key Features

### 1. Graceful Shutdown
- Properly handles SIGINT (Ctrl+C) and SIGTERM signals
- Monitoring thread exits cleanly without forcing termination
- Database connections are closed properly
- No daemon threads that would be killed abruptly

### 2. Modular Architecture
- **Models**: API schema definitions
- **Routes**: HTTP endpoint handlers
- **Services**: Business logic (monitoring, notifications)
- **Utils**: Shared utilities (config, database, validators)

### 3. Monitoring Service
- Thread-safe database connections
- Shutdown event for graceful termination
- Checks shutdown event before processing each endpoint
- Sleeps with shutdown checks to exit quickly

### 4. Notification System
- Dual-channel notifications (NTFY + Telegram)
- Success if at least one channel works
- Proper error handling and logging
- Rate limiting for down notifications

## Running the Application

### Development Mode
```bash
python main.py
```

### Production Mode (Gunicorn)
```bash
gunicorn -c gunicorn.conf.py wsgi:app
```

## Graceful Shutdown Flow

1. User presses Ctrl+C or sends SIGTERM
2. Signal handler catches the signal
3. Sets global shutdown event
4. Monitoring thread checks event and exits cleanly
5. Database connections are closed
6. Application exits with status 0

## Environment Variables

See `example.env` for all available configuration options.

Key variables:
- `CHECK_INTERVAL`: How often to check endpoints (seconds)
- `NOTIFY_EVERY_MINUTES`: Rate limiting for down notifications
- `TELEGRAM_BOT_TOKEN`: Optional Telegram bot token
- `TELEGRAM_CHAT_ID`: Optional Telegram chat ID

## Code Quality Improvements

- ✅ Removed all commented-out code
- ✅ Clean imports (no unused imports)
- ✅ Proper logging instead of print statements
- ✅ Type hints where appropriate
- ✅ Docstrings for all modules and functions
- ✅ No global state except for shutdown coordination
- ✅ Thread-safe database access
