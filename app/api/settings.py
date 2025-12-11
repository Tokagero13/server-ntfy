# -*- coding: utf-8 -*-
import logging
from flask import request
from flask_restx import Namespace, Resource
from .. import config
from ..db import get_db_connection, get_settings
from ..models import add_models_to_api

logger = logging.getLogger(__name__)

ns = Namespace("settings", description="Управление настройками мониторинга")
models = add_models_to_api(ns)

@ns.route("/")
class Settings(Resource):
    @ns.doc("get_settings")
    @ns.marshal_with(models['settings'])
    def get(self):
        """Получить текущие настройки"""
        current_settings = get_settings()
        return {
            "check_interval": int(current_settings.get("check_interval", config.CHECK_INTERVAL)),
            "notify_every_minutes": int(current_settings.get("notify_every_minutes", config.NOTIFY_EVERY_MINUTES)),
        }

    @ns.doc("update_settings")
    @ns.expect(models['settings'])
    @ns.response(200, "Настройки обновлены")
    def put(self):
        """Обновить настройки"""
        data = request.json
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                for key, value in data.items():
                    if key in ["check_interval", "notify_every_minutes"]:
                        cur.execute(
                            "UPDATE settings SET value = ? WHERE key = ?",
                            (str(value), key),
                        )
                conn.commit()
                logger.info(f"Settings updated: {data}")
                return {"message": "Настройки успешно обновлены"}, 200
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            ns.abort(500, "Internal server error")