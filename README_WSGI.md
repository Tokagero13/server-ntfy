# Использование WSGI точки входа

## Запуск через wsgi.py

Файл [`wsgi.py`](wsgi.py) является точкой входа для WSGI серверов (например, Gunicorn). Он автоматически:

1. Инициализирует базу данных
2. Запускает фоновый поток мониторинга эндпоинтов  
3. Экспортирует Flask приложение для WSGI сервера

### Запуск с Gunicorn (Linux/macOS)

```bash
# Запуск с конфигурацией из gunicorn.conf.py
gunicorn -c gunicorn.conf.py wsgi:app

# Или напрямую
gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app
```

### Запуск с Uvicorn (Windows/Cross-platform)

```bash
# Базовый запуск (рекомендуется для Windows)
uvicorn wsgi:app --host 0.0.0.0 --port 5000

# Для разработки с hot reload
uvicorn wsgi:app --host 0.0.0.0 --port 5000 --reload

# ВНИМАНИЕ: На Windows НЕ используйте --workers > 1
# Это вызывает ошибку WinError 10022
# Для масштабирования на Windows используйте PM2 с несколькими процессами
```

### Запуск через PM2

**Для Gunicorn (Linux/macOS):**
```bash
pm2 start "gunicorn wsgi:app" --name monitor-app
```

**Для Uvicorn (Windows/Cross-platform):**
```bash
# ecosystem.config.js для Windows (несколько процессов вместо workers)
{
  "name": "monitor-app",
  "script": "uvicorn",
  "args": "wsgi:app --host 0.0.0.0 --port 5000",
  "instances": 4,  // PM2 создаст 4 процесса
  "exec_mode": "cluster",
  "cwd": "/путь/к/проекту"
}

# Или прямой запуск (без workers на Windows)
pm2 start "uvicorn wsgi:app --host 0.0.0.0 --port 5000" --name monitor-app -i 4
```

### Переменные окружения

Убедитесь, что в [`.env`](.env) настроены:

- `API_BASE` - базовый URL для API
- `DASHBOARD_URL` - URL дашборда для уведомлений  
- `URL` - хост для привязки (по умолчанию localhost)

### Разработка vs Продакшен

- **Разработка**: `python main.py` (включает debug режим)
- **Продакшен Linux/macOS**: `gunicorn wsgi:app` через wsgi.py
- **Продакшен Windows**: `uvicorn wsgi:app` через wsgi.py

## Конфигурация серверов

### Gunicorn (Linux/macOS)
Настройки в [`gunicorn.conf.py`](gunicorn.conf.py):
- Привязка к `0.0.0.0:5000`
- 4 worker процесса
- Логирование в `log/gunicorn/`

### Uvicorn (Windows/Cross-platform)
Параметры командной строки:
- `--host 0.0.0.0` - принимать соединения от всех адресов
- `--port 5000` - порт для приложения
- `--reload` - автоперезагрузка при изменениях (только для разработки)

**ВАЖНО для Windows:**
- НЕ используйте `--workers` > 1 на Windows (вызывает ошибку сокетов)
- Для масштабирования используйте PM2 с параметром `instances`
- Для разработки достаточно одного процесса

## Рекомендации по платформам

- **Windows**: Используйте uvicorn (лучшая совместимость)
- **Linux/macOS**: Используйте gunicorn (более производительный для продакшена)
- **Docker**: Любой из серверов, gunicorn предпочтительнее