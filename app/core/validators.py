# -*- coding: utf-8 -*-
"""Domain-level URL normalization and validation helpers.

These helpers have no HTTP or Flask dependency and can be reused from any
caller (API layer, background workers, CLI tools, tests).
"""
from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    """Преобразование домена в полный URL с поддержкой портов.
    Возвращает HTTPS версию по умолчанию, HTTP fallback будет обработан в check_endpoint_status_with_fallback."""
    url = url.strip()

    # Если это уже полный URL, вернуть как есть
    if url.startswith(("http://", "https://")):
        return url

    # Для любого адреса без протокола добавляем HTTPS по умолчанию
    # Функция check_endpoint_status_with_fallback будет пробовать HTTP если HTTPS не работает
    return f"https://{url}"


def _is_valid_ipv4(ip: str) -> bool:
    """Проверка валидности IPv4 адреса"""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        for part in parts:
            num = int(part)
            if not (0 <= num <= 255):
                return False
        return True
    except ValueError:
        return False


def validate_url(url: str) -> bool:
    """Валидация URL или домена с поддержкой портов"""
    try:
        # Сначала нормализуем URL
        normalized = normalize_url(url)
        result = urlparse(normalized)

        # Проверяем, что есть схема и домен
        if not all([result.scheme, result.netloc]):
            return False

        # Проверяем корректность схемы
        if result.scheme not in ["http", "https"]:
            return False

        # Разбираем netloc для проверки порта
        netloc = result.netloc
        if ":" in netloc:
            hostname, port_str = netloc.rsplit(":", 1)
            try:
                port = int(port_str)
                # Проверяем корректность порта
                if not (1 <= port <= 65535):
                    return False
            except ValueError:
                return False
        else:
            hostname = netloc

        # Проверяем hostname
        if _is_valid_ipv4(hostname):
            return True  # Валидный IPv4
        elif hostname == "localhost":
            return True  # localhost всегда валиден
        elif "." in hostname:
            # Проверяем доменное имя
            parts = hostname.split(".")
            for part in parts:
                if not part or not all(c.isalnum() or c == "-" for c in part):
                    return False
                if part.startswith("-") or part.endswith("-"):
                    return False
            return True
        else:
            return False  # Неподдерживаемый формат

    except Exception:
        return False
