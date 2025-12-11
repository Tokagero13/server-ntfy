# -*- coding: utf-8 -*-
from flask_restx import Api

from .endpoints import ns as endpoints_ns
from .settings import ns as settings_ns


def init_api(api: Api):
    """Инициализирует все пространства имен API."""
    api.add_namespace(endpoints_ns)
    api.add_namespace(settings_ns)
