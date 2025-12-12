# -*- coding: utf-8 -*-
import asyncio
import atexit
import threading
from concurrent.futures import ThreadPoolExecutor

from uvicorn.middleware.wsgi import WSGIMiddleware

from app import create_app, run_background_tasks

# Создаем приложение
application = create_app()

# Глобальные переменные для управления фоновыми задачами
_background_loop = None
_background_thread = None
_tasks = []
_executor = ThreadPoolExecutor(max_workers=1)


def start_background_tasks_sync():
    """Запускает фоновые задачи в отдельном event loop."""
    global _background_loop, _tasks

    # Создаем новый event loop для фоновых задач
    _background_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_background_loop)

    async def run_tasks():
        try:
            # Небольшая задержка для инициализации приложения
            await asyncio.sleep(3)
            application.logger.info("Starting background tasks...")

            # Запускаем фоновые задачи
            _tasks.extend(await run_background_tasks())
            application.logger.info(f"Started {len(_tasks)} background tasks")

            # Ждем завершения всех задач
            if _tasks:
                await asyncio.gather(*_tasks, return_exceptions=True)

        except Exception as e:
            application.logger.error(f"Error in background tasks: {e}")
        finally:
            application.logger.info("Background tasks finished")

    try:
        _background_loop.run_until_complete(run_tasks())
    except Exception as e:
        application.logger.error(f"Background task loop error: {e}")
    finally:
        _background_loop.close()


def cleanup_background_tasks():
    """Очистка фоновых задач при завершении."""
    global _background_loop, _background_thread, _tasks

    if _background_loop and not _background_loop.is_closed():
        application.logger.info("Cleaning up background tasks...")

        # Отменяем все активные задачи
        for task in _tasks:
            if hasattr(task, "cancel") and not task.done():
                task.cancel()

        # Закрываем event loop
        if _background_loop.is_running():
            _background_loop.stop()
        _background_loop.close()

    if _background_thread and _background_thread.is_alive():
        _background_thread.join(timeout=5)

    _executor.shutdown(wait=False)
    application.logger.info("Background tasks cleanup complete")


# Запускаем фоновые задачи при импорте модуля (для Gunicorn)
if __name__ != "__main__":
    _background_thread = threading.Thread(
        target=start_background_tasks_sync, daemon=True, name="BackgroundTasks"
    )
    _background_thread.start()

    # Регистрируем функцию очистки при завершении
    atexit.register(cleanup_background_tasks)

    application.logger.info("Background tasks thread started")

# ASGI-обёртка над Flask-приложением для uvicorn
asgi_app = WSGIMiddleware(application)
