# -*- coding: utf-8 -*-
"""
Модуль для отправки групповых уведомлений через python-telegram-bot==20.7

Этот модуль предоставляет функциональность для отправки уведомлений
в групповые чаты Telegram с поддержкой топиков (форумных разделов).
"""

import logging
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)


class TelegramGroupNotifier:
    """
    Класс для отправки уведомлений в групповые чаты Telegram.

    Использует синхронный Bot API из python-telegram-bot==20.7
    для отправки сообщений в группы с поддержкой топиков.
    """

    def __init__(self, bot_token: str, chat_id: str, thread_id: Optional[str] = None):
        """
        Инициализация уведомителя.

        Args:
            bot_token: Токен Telegram бота
            chat_id: ID группового чата (отрицательное число для групп)
            thread_id: ID топика для форумных групп (опционально)
        """
        self.bot_token = bot_token
        self.chat_id = int(chat_id) if chat_id else None
        self.thread_id = int(thread_id) if thread_id else None
        self._bot: Optional[Bot] = None

        if not self.bot_token:
            raise ValueError("Bot token is required")
        if not self.chat_id:
            raise ValueError("Chat ID is required")

        # Проверяем, что chat_id отрицательный для групп
        if self.chat_id > 0:
            logger.warning(
                f"Chat ID {self.chat_id} is positive. Group chats should have negative IDs."
            )

    @property
    def bot(self) -> Bot:
        """Ленивая инициализация бота."""
        if self._bot is None:
            self._bot = Bot(token=self.bot_token)
        return self._bot

    def send_message(self, message: str) -> bool:
        """
        Отправляет сообщение в групповой чат.

        Args:
            message: Текст сообщения для отправки

        Returns:
            bool: True если сообщение отправлено успешно, False в случае ошибки
        """
        if not message:
            logger.warning("Empty message provided")
            return False

        try:
            import asyncio

            # Создаем event loop если его нет
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            kwargs = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}

            # Добавляем thread_id для топиков, если указан
            if self.thread_id:
                kwargs["message_thread_id"] = self.thread_id

            # Отправляем сообщение синхронно через asyncio
            response = loop.run_until_complete(self.bot.send_message(**kwargs))

            logger.info(
                f"Group notification sent to chat_id {self.chat_id}"
                + (f" (thread {self.thread_id})" if self.thread_id else "")
                + f": {message[:100]}{'...' if len(message) > 100 else ''}"
            )

            return True

        except TelegramError as e:
            logger.error(f"Telegram error sending group notification: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending group notification: {e}")
            return False

    def format_notification(self, message: str, endpoint_url: str) -> str:
        """
        Форматирует сообщение для группового чата.

        Args:
            message: Исходное сообщение уведомления
            endpoint_url: URL эндпоинта для добавления контекста

        Returns:
            str: Отформатированное сообщение
        """
        # Добавляем эмодзи и структуру для группового чата
        formatted_message = f"🔔 <b>Групповое уведомление мониторинга</b>\n\n{message}"

        # Добавляем ссылку на эндпоинт, если она не включена в сообщение
        if endpoint_url and endpoint_url not in message:
            formatted_message += f"\n\n🔗 <code>{endpoint_url}</code>"

        return formatted_message

    def test_connection(self) -> bool:
        """
        Тестирует соединение с Telegram API.

        Returns:
            bool: True если подключение успешно, False в случае ошибки
        """
        try:
            import asyncio

            # Создаем event loop если его нет
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Получаем информацию о боте для проверки токена
            bot_info = loop.run_until_complete(self.bot.get_me())
            logger.info(f"Bot connection test successful. Bot: @{bot_info.username}")

            # Пробуем отправить тестовое сообщение
            test_message = "🧪 Тест подключения группового уведомителя"
            return self.send_message(test_message)

        except TelegramError as e:
            logger.error(f"Bot connection test failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection test: {e}")
            return False


def send_group_notification(
    bot_token: str,
    chat_id: str,
    message: str,
    endpoint_url: str = "",
    thread_id: Optional[str] = None,
) -> bool:
    """
    Удобная функция для отправки группового уведомления.

    Args:
        bot_token: Токен Telegram бота
        chat_id: ID группового чата
        message: Текст сообщения
        endpoint_url: URL эндпоинта (для добавления в сообщение)
        thread_id: ID топика (опционально)

    Returns:
        bool: True если сообщение отправлено успешно
    """
    try:
        notifier = TelegramGroupNotifier(bot_token, chat_id, thread_id)
        formatted_message = notifier.format_notification(message, endpoint_url)
        return notifier.send_message(formatted_message)
    except Exception as e:
        logger.error(f"Error sending group notification: {e}")
        return False
