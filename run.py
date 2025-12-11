# -*- coding: utf-8 -*-
import asyncio

from app import create_app, run_background_tasks

app = create_app()

if __name__ == "__main__":

    async def main():
        # Запускаем Flask в отдельном потоке, управляемом asyncio
        loop = asyncio.get_event_loop()
        flask_task = loop.create_task(
            asyncio.to_thread(
                app.run,
                host=app.config["URL"],
                port=app.config["PORT"],
                debug=True,
                use_reloader=False,
            )
        )

        # Запускаем остальные асинхронные задачи
        await run_background_tasks()

        # Ждем завершения задачи Flask (бесконечно)
        await flask_task

    loop = asyncio.get_event_loop()
    main_task = loop.create_task(main())

    try:
        loop.run_until_complete(main_task)
    except KeyboardInterrupt:
        app.logger.info("Shutting down...")
    finally:
        # Корректное завершение всех задач
        tasks = [t for t in asyncio.all_tasks(loop) if t is not main_task]
        for task in tasks:
            task.cancel()

        # Собираем все задачи для ожидания их отмены
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.close()
        app.logger.info("Shutdown complete.")
