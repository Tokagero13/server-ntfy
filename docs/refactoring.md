# Refactoring Roadmap

## Motivation

This codebase has grown organically and now shows the strain: raw `sqlite3` calls are scattered across route handlers with no repository boundary, there is no automated test suite, Telegram notification logic is duplicated between `app/__init__.py`'s startup path and `app/core/notifications.py`, and `app/__init__.py` itself has become an oversized module that mixes app construction, background task orchestration, and startup notification blasts. The goal of this refactor is to introduce enough structure that future changes are safe, testable, and localized — without rewriting the product.

## Round 1 (this batch)

The current run ships six focused changes:

- **(a) pytest infrastructure** — added `requirements-dev.txt`, a `pytest.ini` / `conftest.py`, and a first smoke test so `python -m pytest` runs green in CI-friendly form.
- **(b) repository layer scaffolding** — introduced `app/repositories/` with `EndpointRepository`, `NotificationRepository`, and `SubscriptionRepository` wrapping the raw SQL currently inlined in `app/api/endpoints.py` and `app/db.py`.
- **(c) monitoring.py type/format fixes** — cleaned up type hints, docstrings, and log format strings in `app/core/monitoring.py` (`check_endpoint_status_with_fallback`, `should_send_down_notification`, `update_notification_time`).
- **(d) telegram_bot dedup** — collapsed duplicated message-building and chat-id resolution helpers in `app/core/telegram_bot.py` into a single shared path shared with `app/core/notifications.py`.
- **(e) startup extraction** — moved `send_startup_notification` / `send_startup_notifications` / `run_background_tasks` out of `app/__init__.py` into `app/core/startup.py`, leaving `create_app` focused on app construction.
- **(f) validators + model registration cleanup** — extracted `normalize_url` / `validate_url` from `app/api/endpoints.py` into `app/api/validators.py`, and simplified `add_models_to_api` in `app/models.py` so registration is declarative.

## Round 2 (planned, not yet scheduled)

- Migrate the remaining callers in `app/api/endpoints.py`, `app/api/settings.py`, and `app/core/monitoring.py` off raw `sqlite3` and onto the new repositories from Round 1(b).
- Dedupe the startup Telegram loop in `app/core/startup.py` against `send_telegram_notification` in `app/core/notifications.py` — there should be exactly one code path that talks to Telegram.
- Wire `REQUEST_TIMEOUT` from `app/config.py` into the Telegram and NTFY HTTP calls in `app/core/notifications.py` (both are currently hardcoded to 10s / 5s).
- Split the `check_endpoints_loop` state machine in `app/core/monitoring.py` into small, named functions per scenario (was-up-now-down, was-down-now-up, still-down, recovered-within-grace, etc.) so each transition is independently testable.
- Introduce Alembic-style migrations to replace the ad-hoc `ALTER TABLE` / `try/except` flow inside `init_db` in `app/db.py`.
- Delete `index.html` **if** `index2.html` is the live entrypoint — verify against `app/__init__.py` route wiring and any reverse-proxy config before removing.
- Tighten CORS: replace the current permissive setup with an allow-list driven by config.

## Non-goals

This refactor deliberately does **not** change the SQLite schema (columns and tables stay as they are; only the access layer moves), does **not** switch web frameworks (Flask + flask-restx stay), and does **not** touch the frontend HTML/JS in `index.html` / `index2.html` in this round. Anything schema-shaped or framework-shaped is out of scope until the repository layer and test coverage from Round 1 and Round 2 are in place.

## How to verify

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -x -q
python -c "from app import create_app; create_app()"
```
