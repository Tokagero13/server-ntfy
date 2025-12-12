#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки групповых уведомлений Telegram

Использует настройки из .env файла для тестирования функциональности
отправки сообщений в групповые чаты.
"""

import logging
import os
import sys
from datetime import datetime

# Добавляем путь к приложению
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import config
from app.core.group_notifications import TelegramGroupNotifier, send_group_notification
from app.core.notifications import send_group_telegram_notification, send_notifications

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_basic_group_notification():
    """Тестирует базовую отправку группового уведомления"""
    print("🧪 Тестирование базового группового уведомления...")

    if not config.TELEGRAM_GROUP_ENABLED:
        print("❌ Групповые уведомления отключены в конфигурации")
        return False

    if not config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не настроен")
        return False

    if not config.TELEGRAM_GROUP_CHAT_ID:
        print("❌ TELEGRAM_GROUP_CHAT_ID не настроен")
        return False

    try:
        success = send_group_notification(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_GROUP_CHAT_ID,
            message="🧪 Тест базовой функции групповых уведомлений",
            endpoint_url="https://test.example.com/health",
            thread_id=config.TELEGRAM_GROUP_THREAD_ID,
        )

        if success:
            print("✅ Базовое групповое уведомление отправлено успешно")
            return True
        else:
            print("❌ Ошибка при отправке базового группового уведомления")
            return False

    except Exception as e:
        print(f"❌ Исключение при тестировании базового уведомления: {e}")
        return False


def test_notifier_class():
    """Тестирует класс TelegramGroupNotifier"""
    print("\n🧪 Тестирование класса TelegramGroupNotifier...")

    try:
        notifier = TelegramGroupNotifier(
            bot_token=config.TELEGRAM_BOT_TOKEN,
            chat_id=config.TELEGRAM_GROUP_CHAT_ID,
            thread_id=config.TELEGRAM_GROUP_THREAD_ID,
        )

        # Тест соединения
        print("   Проверка соединения...")
        if not notifier.test_connection():
            print("❌ Ошибка подключения к Telegram API")
            return False

        # Тест отправки сообщения
        test_message = f"🧪 Тест класса TelegramGroupNotifier\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        success = notifier.send_message(test_message)

        if success:
            print("✅ Класс TelegramGroupNotifier работает корректно")
            return True
        else:
            print("❌ Ошибка при отправке через класс TelegramGroupNotifier")
            return False

    except Exception as e:
        print(f"❌ Исключение при тестировании класса: {e}")
        return False


def test_integration():
    """Тестирует интеграцию с основной системой уведомлений"""
    print("\n🧪 Тестирование интеграции с системой уведомлений...")

    try:
        # Тест функции интеграции
        success = send_group_telegram_notification(
            message="🧪 Тест интеграции групповых уведомлений",
            endpoint_url="https://integration-test.example.com",
        )

        if success:
            print("✅ Интеграция с системой уведомлений работает")

            # Тест полного диспетчера уведомлений
            print("   Тестирование полного диспетчера...")
            send_notifications(
                message="🧪 Тест полного диспетчера уведомлений",
                endpoint_url="https://dispatcher-test.example.com",
                endpoint_id=999,
            )
            print("✅ Полный диспетчер уведомлений протестирован")
            return True
        else:
            print("❌ Ошибка интеграции с системой уведомлений")
            return False

    except Exception as e:
        print(f"❌ Исключение при тестировании интеграции: {e}")
        return False


def print_configuration():
    """Выводит текущую конфигурацию"""
    print("📋 Текущая конфигурация:")
    print(
        f"   TELEGRAM_BOT_TOKEN: {'✅ настроен' if config.TELEGRAM_BOT_TOKEN else '❌ не настроен'}"
    )
    print(f"   TELEGRAM_GROUP_ENABLED: {config.TELEGRAM_GROUP_ENABLED}")
    print(f"   TELEGRAM_GROUP_CHAT_ID: {config.TELEGRAM_GROUP_CHAT_ID}")
    print(f"   TELEGRAM_GROUP_THREAD_ID: {config.TELEGRAM_GROUP_THREAD_ID}")
    print(f"   NTFY_ENABLED: {config.NTFY_ENABLED}")
    print(f"   TELEGRAM_ENABLED: {config.TELEGRAM_ENABLED}")


def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов групповых уведомлений Telegram\n")

    # Выводим конфигурацию
    print_configuration()
    print()

    # Счетчик успешных тестов
    passed = 0
    total = 3

    # Выполняем тесты
    if test_basic_group_notification():
        passed += 1

    if test_notifier_class():
        passed += 1

    if test_integration():
        passed += 1

    # Результаты
    print("\n📊 Результаты тестирования:")
    print(f"   Пройдено: {passed}/{total}")

    if passed == total:
        print("✅ Все тесты пройдены успешно!")
        print("\n🎉 Групповые уведомления Telegram настроены и работают корректно!")
    else:
        print("❌ Некоторые тесты не прошли")
        print("\n🔧 Проверьте конфигурацию и логи для устранения проблем")

    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)
