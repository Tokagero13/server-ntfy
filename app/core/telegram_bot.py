# -*- coding: utf-8 -*-
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from .. import config
from ..db import get_db_connection

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

_ENDPOINT_LIST_TEXT = (
    "📋 <b>Выберите эндпоинты для подписки:</b>\n\n"
    "🟢 - Онлайн\n"
    "🔴 - Офлайн\n\n"
    "Нажмите на эндпоинт, чтобы подписаться на уведомления."
)


def _build_endpoint_keyboard(endpoints: list[dict]) -> InlineKeyboardMarkup:
    keyboard = []
    for endpoint in endpoints:
        name = endpoint.get("name") or endpoint["url"]
        status_emoji = "🟢" if not endpoint.get("is_down") else "🔴"
        button_text = f"{status_emoji} {name}"
        keyboard.append(
            [
                InlineKeyboardButton(
                    button_text, callback_data=f"subscribe_{endpoint['id']}"
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton("🔄 Обновить список", callback_data="refresh_endpoints")]
    )
    return InlineKeyboardMarkup(keyboard)


def _upsert_subscription(cur, endpoint_id: int, chat_id: str) -> tuple[str, str]:
    """Look up or create/reactivate a subscription.

    Returns (status, endpoint_name) where status is one of:
    "not_found", "already", "reactivated", "created".
    Does NOT commit — callers are responsible for conn.commit().
    """
    cur.execute("SELECT name, url FROM endpoints WHERE id = ?", (endpoint_id,))
    endpoint = cur.fetchone()
    if not endpoint:
        return ("not_found", "")

    endpoint_name = endpoint["name"] or endpoint["url"]

    cur.execute(
        """
        SELECT id, enabled FROM endpoint_subscriptions
        WHERE endpoint_id = ? AND chat_id = ?
    """,
        (endpoint_id, chat_id),
    )
    existing = cur.fetchone()

    if existing:
        if existing["enabled"]:
            return ("already", endpoint_name)
        cur.execute(
            "UPDATE endpoint_subscriptions SET enabled = 1 WHERE id = ?",
            (existing["id"],),
        )
        return ("reactivated", endpoint_name)

    now_iso = datetime.now(timezone.utc).isoformat()
    cur.execute(
        """
        INSERT INTO endpoint_subscriptions (endpoint_id, chat_id, enabled, created_at)
        VALUES (?, ?, 1, ?)
    """,
        (endpoint_id, chat_id, now_iso),
    )
    return ("created", endpoint_name)


class TelegramBotHandler:
    def __init__(self, token: str):
        self.token = token
        self.application = None

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Обработчик команды /start"""
        chat_id = str(update.effective_chat.id)
        user = update.effective_user

        # Логируем информацию о пользователе для отладки
        logger.info(
            f"Start command from user {user.id} ({user.username}) in chat {chat_id}"
        )

        # Проверяем deep link параметр
        if context.args:
            payload = context.args[0]
            await self.handle_deep_link(update, context, payload)
            return

        # Обычное приветствие
        welcome_message = (
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я бот для мониторинга эндпоинтов. Вот что я умею:\n\n"
            f"🔔 /subscribe - Подписаться на уведомления\n"
            f"📋 /list - Посмотреть мои подписки\n"
            f"❌ /unsubscribe - Отписаться от уведомлений\n"
            f"📊 /status - Статус всех эндпоинтов\n"
            f"ℹ️ /help - Показать эту справку\n\n"
            f"📱 Dashboard: {config.DASHBOARD_URL}"
        )

        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)

    async def handle_deep_link(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, payload: str
    ) -> None:
        """Обработка deep link параметров"""
        chat_id = str(update.effective_chat.id)

        if payload.startswith("discover_"):
            # Обработка discovery кода
            discovery_code = payload.replace("discover_", "").upper()
            await self.process_discovery_code(update, discovery_code)

        elif payload.startswith("endpoint_"):
            # Прямая подписка на эндпоинт
            try:
                endpoint_id = int(payload.replace("endpoint_", ""))
                await self.subscribe_to_endpoint(update, endpoint_id, chat_id)
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат ссылки для эндпоинта"
                )

        else:
            await update.message.reply_text(f"❓ Неизвестный параметр: {payload}")

    async def process_discovery_code(self, update: Update, discovery_code: str) -> None:
        """Обработка кода обнаружения Chat ID"""
        chat_id = str(update.effective_chat.id)
        user = update.effective_user

        try:
            with get_db_connection() as conn:
                cur = conn.cursor()

                # Ищем активный код обнаружения
                cur.execute(
                    """
                    SELECT id FROM telegram_discovery
                    WHERE discovery_code = ? AND status = 'pending'
                    AND datetime(expires_at) > datetime('now')
                """,
                    (discovery_code,),
                )

                discovery_record = cur.fetchone()
                if not discovery_record:
                    await update.message.reply_text(
                        "❌ Код обнаружения не найден или истек.\n"
                        "Попробуйте создать новый код в веб-интерфейсе."
                    )
                    return

                # Обновляем запись с информацией о чате
                cur.execute(
                    """
                    UPDATE telegram_discovery
                    SET chat_id = ?, username = ?, first_name = ?,
                        last_name = ?, status = 'completed'
                    WHERE id = ?
                """,
                    (
                        chat_id,
                        user.username or "",
                        user.first_name or "",
                        user.last_name or "",
                        discovery_record[0],
                    ),
                )

                conn.commit()

                success_message = (
                    f"✅ <b>Chat ID обнаружен успешно!</b>\n\n"
                    f"🆔 Ваш Chat ID: <code>{chat_id}</code>\n"
                    f"👤 Пользователь: {user.first_name or 'N/A'} {user.last_name or ''}\n"
                    f"📱 Username: @{user.username or 'N/A'}\n\n"
                    f"Теперь вы можете использовать этот Chat ID для подписки на уведомления в веб-интерфейсе.\n\n"
                    f"Или используйте команду /subscribe для подписки прямо здесь!"
                )

                await update.message.reply_text(
                    success_message, parse_mode=ParseMode.HTML
                )
                logger.info(
                    f"Discovery completed for code {discovery_code}, chat_id: {chat_id}"
                )

        except Exception as e:
            logger.error(f"Error processing discovery code: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при обработке кода обнаружения. Попробуйте позже."
            )

    async def subscribe_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Команда подписки на эндпоинты"""
        endpoints = await self.get_endpoints()

        if not endpoints:
            await update.message.reply_text(
                "❌ Эндпоинты не найдены. Добавьте эндпоинты через веб-интерфейс:\n"
                f"📱 {config.DASHBOARD_URL}"
            )
            return

        reply_markup = _build_endpoint_keyboard(endpoints)
        await update.message.reply_text(
            _ENDPOINT_LIST_TEXT, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )

    async def list_subscriptions_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Показать список подписок пользователя"""
        chat_id = str(update.effective_chat.id)
        subscriptions = await self.get_user_subscriptions(chat_id)

        if not subscriptions:
            message = (
                "📭 У вас пока нет активных подписок.\n\n"
                "Используйте /subscribe для подписки на уведомления."
            )
            await update.message.reply_text(message)
            return

        message_lines = ["📋 <b>Ваши подписки:</b>\n"]

        keyboard = []
        for sub in subscriptions:
            endpoint = sub["endpoint"]
            name = endpoint.get("name") or endpoint["url"]
            status_emoji = "🟢" if not endpoint.get("is_down") else "🔴"
            sub_status = "✅" if sub["enabled"] else "⏸️"

            message_lines.append(f"{status_emoji} {sub_status} {name}")

            # Кнопка для отписки
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"❌ Отписаться от {name}",
                        callback_data=f"unsubscribe_{sub['id']}",
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        message_text = "\n".join(message_lines)

        await update.message.reply_text(
            message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )

    async def status_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Показать статус всех эндпоинтов"""
        endpoints = await self.get_endpoints()

        if not endpoints:
            await update.message.reply_text("❌ Эндпоинты не найдены.")
            return

        message_lines = ["📊 <b>Статус эндпоинтов:</b>\n"]

        online_count = 0
        offline_count = 0

        for endpoint in endpoints:
            name = endpoint.get("name") or endpoint["url"]
            if endpoint.get("is_down"):
                status_emoji = "🔴"
                status_text = "Офлайн"
                offline_count += 1
            else:
                status_emoji = "🟢"
                status_text = "Онлайн"
                online_count += 1

            last_checked = endpoint.get("last_checked", "Никогда")
            if last_checked and last_checked != "Никогда":
                try:
                    dt = datetime.fromisoformat(last_checked.replace("Z", "+00:00"))
                    last_checked = dt.strftime("%H:%M:%S")
                except:
                    pass

            message_lines.append(f"{status_emoji} <b>{name}</b> - {status_text}")
            message_lines.append(f"   Проверено: {last_checked}")

        summary = f"\n📈 <b>Итого:</b> {online_count} онлайн, {offline_count} офлайн"
        message_lines.append(summary)

        message_text = "\n".join(message_lines)
        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Справка по командам"""
        help_text = (
            "🤖 <b>Команды бота мониторинга:</b>\n\n"
            "🔔 /subscribe - Подписаться на уведомления о падении эндпоинтов\n"
            "📋 /list - Посмотреть список ваших подписок\n"
            "❌ /unsubscribe - Управление подписками (отписка)\n"
            "📊 /status - Текущий статус всех эндпоинтов\n"
            "ℹ️ /help - Показать эту справку\n\n"
            "<b>Как работают уведомления:</b>\n"
            "• Бот отправляет уведомления при падении эндпоинтов\n"
            "• Уведомления о восстановлении работы\n"
            "• Периодические напоминания о длительном падении\n\n"
            f"📱 Веб-интерфейс: {config.DASHBOARD_URL}"
        )

        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def button_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Обработчик нажатий на inline кнопки"""
        query = update.callback_query
        await query.answer()

        chat_id = str(query.from_user.id)
        data = query.data

        if data.startswith("subscribe_"):
            endpoint_id = int(data.replace("subscribe_", ""))
            await self.subscribe_to_endpoint_callback(query, endpoint_id, chat_id)

        elif data.startswith("unsubscribe_"):
            subscription_id = int(data.replace("unsubscribe_", ""))
            await self.unsubscribe_callback(query, subscription_id)

        elif data == "refresh_endpoints":
            await self.refresh_endpoints_callback(query)

    async def subscribe_to_endpoint_callback(
        self, query, endpoint_id: int, chat_id: str
    ) -> None:
        """Подписка на эндпоинт через callback"""
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                status, endpoint_name = _upsert_subscription(cur, endpoint_id, chat_id)

                if status == "not_found":
                    await query.edit_message_text("❌ Эндпоинт не найден")
                    return

                if status != "already":
                    conn.commit()

                if status == "already":
                    text = f"ℹ️ Вы уже подписаны на <b>{endpoint_name}</b>"
                elif status == "reactivated":
                    text = f"✅ Подписка на <b>{endpoint_name}</b> активирована!"
                else:
                    text = (
                        f"✅ <b>Подписка создана!</b>\n\n"
                        f"📍 Эндпоинт: <b>{endpoint_name}</b>\n"
                        f"🔔 Вы будете получать уведомления о статусе этого эндпоинта.\n\n"
                        f"Используйте /list для просмотра всех подписок."
                    )
                    logger.info(
                        f"Subscription created for chat {chat_id} to endpoint {endpoint_id}"
                    )

                await query.edit_message_text(text, parse_mode=ParseMode.HTML)

        except Exception as e:
            logger.error(f"Error subscribing to endpoint: {e}")
            await query.edit_message_text("❌ Ошибка при создании подписки")

    async def subscribe_to_endpoint(
        self, update: Update, endpoint_id: int, chat_id: str
    ) -> None:
        """Подписка на эндпоинт (для deep linking)"""
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                status, endpoint_name = _upsert_subscription(cur, endpoint_id, chat_id)

                if status == "not_found":
                    await update.message.reply_text("❌ Эндпоинт не найден")
                    return

                if status != "already":
                    conn.commit()

                if status == "already":
                    text = f"ℹ️ Вы уже подписаны на <b>{endpoint_name}</b>"
                else:
                    text = (
                        f"✅ <b>Подписка создана!</b>\n\n"
                        f"📍 Эндпоинт: <b>{endpoint_name}</b>\n"
                        f"🔔 Вы будете получать уведомления о статусе этого эндпоинта."
                    )

                await update.message.reply_text(text, parse_mode=ParseMode.HTML)

        except Exception as e:
            logger.error(f"Error subscribing to endpoint: {e}")
            await update.message.reply_text("❌ Ошибка при создании подписки")

    async def unsubscribe_callback(self, query, subscription_id: int) -> None:
        """Отписка от эндпоинта"""
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()

                # Получаем информацию о подписке
                cur.execute(
                    """
                    SELECT es.id, e.name, e.url
                    FROM endpoint_subscriptions es
                    JOIN endpoints e ON es.endpoint_id = e.id
                    WHERE es.id = ?
                """,
                    (subscription_id,),
                )

                subscription = cur.fetchone()
                if not subscription:
                    await query.edit_message_text("❌ Подписка не найдена")
                    return

                endpoint_name = subscription["name"] or subscription["url"]

                # Удаляем подписку
                cur.execute(
                    "DELETE FROM endpoint_subscriptions WHERE id = ?",
                    (subscription_id,),
                )
                conn.commit()

                await query.edit_message_text(
                    f"✅ Вы отписались от <b>{endpoint_name}</b>",
                    parse_mode=ParseMode.HTML,
                )

        except Exception as e:
            logger.error(f"Error unsubscribing: {e}")
            await query.edit_message_text("❌ Ошибка при отписке")

    async def refresh_endpoints_callback(self, query) -> None:
        """Обновление списка эндпоинтов"""
        endpoints = await self.get_endpoints()

        if not endpoints:
            await query.edit_message_text("❌ Эндпоинты не найдены")
            return

        reply_markup = _build_endpoint_keyboard(endpoints)
        await query.edit_message_text(
            _ENDPOINT_LIST_TEXT, reply_markup=reply_markup, parse_mode=ParseMode.HTML
        )

    async def get_endpoints(self) -> List[Dict]:
        """Получить список всех эндпоинтов"""
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, name, url, last_status, last_checked, is_down
                    FROM endpoints
                    ORDER BY name, url
                """)

                rows = cur.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting endpoints: {e}")
            return []

    async def get_user_subscriptions(self, chat_id: str) -> List[Dict]:
        """Получить подписки пользователя"""
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT es.id, es.enabled, es.created_at,
                           e.id as endpoint_id, e.name, e.url, e.is_down
                    FROM endpoint_subscriptions es
                    JOIN endpoints e ON es.endpoint_id = e.id
                    WHERE es.chat_id = ?
                    ORDER BY e.name, e.url
                """,
                    (chat_id,),
                )

                rows = cur.fetchall()
                result = []

                for row in rows:
                    result.append(
                        {
                            "id": row["id"],
                            "enabled": row["enabled"],
                            "created_at": row["created_at"],
                            "endpoint": {
                                "id": row["endpoint_id"],
                                "name": row["name"],
                                "url": row["url"],
                                "is_down": row["is_down"],
                            },
                        }
                    )

                return result
        except Exception as e:
            logger.error(f"Error getting user subscriptions: {e}")
            return []

    async def run(self) -> None:
        """Настраивает и запускает бота."""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not provided")
            return

        self.application = Application.builder().token(self.token).build()

        # Регистрируем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(
            CommandHandler("subscribe", self.subscribe_command)
        )
        self.application.add_handler(
            CommandHandler("list", self.list_subscriptions_command)
        )
        self.application.add_handler(
            CommandHandler("unsubscribe", self.list_subscriptions_command)  # NOTE: /unsubscribe intentionally reuses /list to show the unsubscribe buttons inline.
        )
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("help", self.help_command))

        # Регистрируем обработчик callback кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))

        logger.info("Telegram bot handlers registered")

        logger.info("Starting Telegram bot...")

        # Инициализируем и запускаем приложение
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot started polling")

        # Держим задачу активной и обрабатываем корректное завершение
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Stopping Telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram bot stopped")
            raise


# Глобальная переменная для бота
telegram_bot_handler = None


async def start_telegram_bot_async() -> Optional[Application]:
    """Асинхронный запуск Telegram бота и возврат объекта Application."""
    global telegram_bot_handler

    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not configured, skipping bot startup")
        return None

    try:
        telegram_bot_handler = TelegramBotHandler(config.TELEGRAM_BOT_TOKEN)

        # Запускаем polling в фоновом режиме и возвращаем application
        loop = asyncio.get_event_loop()
        loop.create_task(telegram_bot_handler.run())

        logger.info("Telegram bot has been scheduled to run.")
        return telegram_bot_handler.application

    except Exception as e:
        logger.error(f"Error starting Telegram bot asynchronously: {e}")
        return None
