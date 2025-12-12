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

    # Добавляем задачу для отправки приветственного сообщения
    tasks.append(loop.create_task(send_startup_notification()))

    return tasks


async def send_startup_notification():
    """Асинхронная отправка приветственного сообщения при старте."""
    # Небольшая задержка, чтобы все системы успели инициализироваться
    await asyncio.sleep(2)

    if config.NTFY_ENABLED or config.TELEGRAM_ENABLED or config.TELEGRAM_GROUP_ENABLED:
        logger.info("Sending startup notification...")

        # Формируем детальное приветственное сообщение
        startup_message = (
            f"🚀 <b>Система мониторинга запущена!</b>\n\n"
            f"✅ Сервис успешно стартовал и готов к работе\n"
            f"📊 Dashboard: {config.DASHBOARD_URL}\n"
            f"🤖 Telegram Bot: @{config.TELEGRAM_BOT_USERNAME}\n\n"
            f"<b>Активные каналы уведомлений:</b>\n"
            f"{'🔔 NTFY: включен' if config.NTFY_ENABLED else '⚪ NTFY: отключен'}\n"
            f"{'📱 Telegram (индивидуальные): включен' if config.TELEGRAM_ENABLED else '⚪ Telegram (индивидуальные): отключен'}\n"
            f"{'👥 Telegram (групповые): включен' if config.TELEGRAM_GROUP_ENABLED else '⚪ Telegram (групповые): отключен'}\n\n"
            f"Система готова к мониторингу эндпоинтов!"
        )

        # Отправляем приветственное сообщение через специальную функцию
        await asyncio.to_thread(send_startup_notifications, startup_message)
        logger.info("Startup notification sent to all active channels")
    else:
        logger.info("No notification channels enabled for startup notification")


def send_startup_notifications(message: str):
    """Отправка приветственного сообщения всем активным пользователям и каналам."""
    import requests

    from .core.notifications import (
        send_group_telegram_notification,
        send_ntfy_notification,
    )
    from .db import get_db_connection

    # NTFY уведомления
    ntfy_success = False
    if config.NTFY_ENABLED:
        ntfy_success = send_ntfy_notification(message)

    # Индивидуальные Telegram уведомления для всех подписчиков
    telegram_success = False
    if config.TELEGRAM_ENABLED:
        # Получаем всех уникальных подписчиков
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT DISTINCT chat_id FROM endpoint_subscriptions WHERE enabled = 1"
                )
                active_chats = [row[0] for row in cur.fetchall()]

                # Добавляем chat_id из конфигурации, если он настроен
                configured_chats = [
                    int(chat_id.strip())
                    for chat_id in config.TELEGRAM_CHAT_ID.split(",")
                    if chat_id.strip()
                ]

                # Объединяем все чаты
                all_chats = list(set(active_chats + configured_chats))

                if all_chats:
                    success_count = 0
                    telegram_url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"

                    for chat_id in all_chats:
                        try:
                            payload = {
                                "chat_id": chat_id,
                                "text": message,
                                "parse_mode": "HTML",
                            }
                            if config.TELEGRAM_MESSAGE_THREAD_ID:
                                payload["message_thread_id"] = int(
                                    config.TELEGRAM_MESSAGE_THREAD_ID
                                )

                            resp = requests.post(telegram_url, json=payload, timeout=10)
                            if resp.status_code == 200:
                                logger.info(
                                    f"Startup notification sent to chat_id {chat_id}"
                                )
                                success_count += 1
                            else:
                                logger.warning(
                                    f"Failed to send startup notification to {chat_id}: {resp.text}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Error sending startup notification to {chat_id}: {e}"
                            )

                    telegram_success = success_count > 0
                    logger.info(
                        f"Startup notifications sent to {success_count}/{len(all_chats)} Telegram chats"
                    )
                else:
                    logger.info(
                        "No active Telegram subscribers for startup notification"
                    )
        except Exception as e:
            logger.error(f"Failed to get active subscribers: {e}")

    # Групповые Telegram уведомления
    group_success = False
    if config.TELEGRAM_GROUP_ENABLED:
        group_success = send_group_telegram_notification(message, config.DASHBOARD_URL)

    # Логирование результата
    channels_info = []
    if config.NTFY_ENABLED:
        channels_info.append(f"NTFY: {'✓' if ntfy_success else '✗'}")
    if config.TELEGRAM_ENABLED:
        channels_info.append(f"Telegram: {'✓' if telegram_success else '✗'}")
    if config.TELEGRAM_GROUP_ENABLED:
        channels_info.append(f"Group: {'✓' if group_success else '✗'}")

    channels_status = (
        " | ".join(channels_info) if channels_info else "No channels enabled"
    )
    logger.info(f"Startup notification dispatch complete: {channels_status}")
