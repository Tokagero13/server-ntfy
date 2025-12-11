# -*- coding: utf-8 -*-
import asyncio
import logging
import threading

from flask import Flask, render_template_string
from flask_restx import Api

from . import config
from .api import init_api
from .core.monitoring import check_endpoints_loop
from .core.notifications import send_notifications
from .core.telegram_bot import start_telegram_bot_async
from .db import init_db
from .models import add_models_to_api

logger = logging.getLogger(__name__)


def create_app():
    """Создает и конфигурирует экземпляр Flask приложения."""
    app = Flask(__name__, static_folder="../static", static_url_path="/static")
    app.config.from_object(config)

    # Настройка логирования
    logging.basicConfig(
        level=config.LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Инициализация API
    api = Api(
        app,
        version="2.0.0",
        title="Endpoints Monitor API",
        description="Refactored API for endpoint monitoring",
        doc="/docs/",
        prefix="/api",
        validate=True,
    )

    # Добавляем модели в API
    add_models_to_api(api)

    # Инициализируем все пространства имен API
    init_api(api)

    # Инициализация БД
    with app.app_context():
        init_db()

    # Маршрут для главной страницы
    @app.route("/")
    def index():
        with open(config.INDEX_PAGE, "r", encoding="utf-8") as f:
            template = f.read()

        # Заменяем плейсхолдеры в HTML
        template = template.replace("{ntfy_server}", config.NTFY_SERVER)
        template = template.replace("{topic}", config.NTFY_TOPIC)
        template = template.replace("{api_base}", config.API_BASE)
        template = template.replace("{dashboard_url}", config.DASHBOARD_URL)
        template = template.replace(
            "{telegram_bot_username}", config.TELEGRAM_BOT_USERNAME
        )

        return render_template_string(template)

    # CORS для работы с фронтендом
    @app.after_request
    def after_request(response):
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add(
            "Access-Control-Allow-Headers", "Content-Type,Authorization"
        )
        response.headers.add(
            "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,OPTIONS"
        )
        return response

    return app


async def run_background_tasks() -> list:
    """Запускает все асинхронные фоновые задачи и возвращает список задач."""
    loop = asyncio.get_event_loop()
    tasks = []

    # Запускаем мониторинг эндпоинтов
    tasks.append(loop.create_task(asyncio.to_thread(check_endpoints_loop)))

    # Запускаем Telegram-бота, если он доступен
    if config.TELEGRAM_ENABLED and config.TELEGRAM_BOT_TOKEN:
        bot_app = await start_telegram_bot_async()
        if bot_app:
            tasks.append(bot_app)  # Добавляем приложение бота в список задач

    # Отправка приветственного сообщения при старте
    if config.NTFY_ENABLED or config.TELEGRAM_ENABLED:
        logger.info("Sending startup notification...")
        startup_message = f"✅ Monitoring service started successfully.\n\nDashboard: {config.DASHBOARD_URL}"
        send_notifications(startup_message, "system")

    return tasks
