# -*- coding: utf-8 -*-
import asyncio
import threading

from app import create_app, run_background_tasks

app = create_app()

if __name__ == "__main__":

    async def main():
        loop = asyncio.get_running_loop()

        # Запускаем Flask в отдельном потоке
        flask_task = loop.create_task(
            asyncio.to_thread(
                app.run,
                host=app.config["URL"],
                port=app.config["PORT"],
                debug=True,
                use_reloader=False,
            )
        )

        # Запускаем фоновые задачи
        background_tasks = await run_background_tasks()

        # Ожидаем завершения всех задач
        try:
            await asyncio.gather(flask_task, *background_tasks)
        except asyncio.CancelledError:
            app.logger.info("Main task cancelled.")

    async def shutdown(loop: asyncio.AbstractEventLoop, tasks: list):
        app.logger.info("Shutting down...")

        # Диагностика: какие потоки и задачи активны во время shutdown
        active_threads = [f"{t.name}(daemon={t.daemon})" for t in threading.enumerate()]
        app.logger.info(
            f"Shutdown: active threads before cancellation: {active_threads}"
        )
        app.logger.info(f"Shutdown: asyncio tasks to cancel: {len(tasks)}")

        # Отменяем все задачи
        for task in tasks:
            if hasattr(
                task, "stop"
            ):  # Для Telegram App (не срабатывает для asyncio.Task)
                app.logger.info(
                    f"Shutdown: calling stop() on task-like object {task!r}"
                )
                await task.stop()
            else:
                app.logger.info(f"Shutdown: cancelling asyncio task {task!r}")
                task.cancel()

        # Собираем отмененные задачи
        app.logger.info("Shutdown: awaiting cancelled tasks with asyncio.gather")
        await asyncio.gather(*tasks, return_exceptions=True)

        loop.stop()

    def handle_exception(loop, context):
        # context["message"] будет "unhandled exception"
        msg = context.get("exception", context["message"])
        app.logger.error(f"Caught exception: {msg}")
        app.logger.info("Shutting down event loop...")
        asyncio.create_task(shutdown(loop, asyncio.all_tasks(loop)))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.set_exception_handler(handle_exception)

    try:
        loop.create_task(main())
        loop.run_forever()
    except KeyboardInterrupt:
        app.logger.info("Keyboard interrupt received.")
    finally:
        tasks = asyncio.all_tasks(loop)
        loop.run_until_complete(shutdown(loop, tasks))
        loop.close()
        app.logger.info("Shutdown complete.")
