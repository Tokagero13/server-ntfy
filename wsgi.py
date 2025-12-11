# -*- coding: utf-8 -*-
import asyncio
import threading

from uvicorn.middleware.wsgi import WSGIMiddleware

from app import create_app, run_background_tasks

# Создаем приложение
application = create_app()


# Запускаем фоновые задачи в отдельных потоках
# Этот код выполнится один раз при запуске Gunicorn
def start_background_tasks_sync():
    asyncio.run(run_background_tasks())


if __name__ != "__main__":
    background_task_thread = threading.Thread(
        target=start_background_tasks_sync, daemon=True
    )
    background_task_thread.start()

# ASGI-обёртка над Flask-приложением для uvicorn
asgi_app = WSGIMiddleware(application)
