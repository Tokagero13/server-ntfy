# Recent Decisions

## [2026-08-09 22:11] Spawn failed (transient, attempt 1): manager: Task 24a66f41cbe1 has effort='max' but no model, and no default_model is configured. Refusing to guess a model. (24a66f41cbe1)
Spawn failed (transient, attempt 1): manager: Task 24a66f41cbe1 has effort='max' but no model, and no default_model is configured. Refusing to guess a model.












## [2026-08-09 22:16] Completed: Fix wrong type annotation in monitoring.py and unify dashboard message formatting (1985f979581b)
Completed: Fix wrong type annotation in monitoring.py and unify dashboard message formatting










## [2026-08-09 22:17] Decomposed 'start refactoring' into 7 file-disjoint tasks: (1) qa/e4c8f38c4f5d pytest infra + validation/monitoring unit tests, (2) architect/34196aa87c4d repository DAL layer in app/repositories (new files), (3) backend/9c424e1782a9 fix wrong sqlite cursor type annotation + extract dashboard message helper in monitoring.py, (4) backend/243fc900fa9b dedupe subscribe/keyboard logic in telegram_bot.py (~180 duplicate lines), (5) backend/ef92d5f815ea move send_startup_notification(s) out of oversized app/__init__.py into app/core/startup.py, (6) architect/c3849e1033a8 extract url validators + fix triple model registration, (7) docs/0df11926e25d refactoring roadmap. File ownership is fully disjoint (verified) so tasks can run concurrently without merge conflicts. Round 2 follow-ups (migrate callers to repositories, wire REQUEST_TIMEOUT, split monitoring state machine, migrations, CORS) captured in docs/refactoring.md. (db8a08129be6)
Decomposed 'start refactoring' into 7 file-disjoint tasks: (1) qa/e4c8f38c4f5d pytest infra + validation/monitoring unit tests, (2) architect/34196aa87c4d repository DAL layer in app/repositories (new files), (3) backend/9c424e1782a9 fix wrong sqlite cursor type annotation + extract dashboard message helper in monitoring.py, (4) backend/243fc900fa9b dedupe subscribe/keyboard logic in telegram_bot.py (~180 duplicate lines), (5) backend/ef92d5f815ea move send_startup_notification(s) out of oversized app/__init__.py into app/core/startup.py, (6) architect/c3849e1033a8 extract url validators + fix triple model registration, (7) docs/0df11926e25d refactoring roadmap. File ownership is fully disjoint (verified) so tasks can run concurrently without merge conflicts. Round 2 follow-ups (migrate callers to repositories, wire REQUEST_TIMEOUT, split monitoring state machine, migrations, CORS) captured in docs/refactoring.md.








## [2026-08-09 22:17] Wrote docs/refactoring.md with Motivation, Round 1 (six items), Round 2 (seven follow-ups), Non-goals, and How to verify sections. (75706745b15c)
Wrote docs/refactoring.md with Motivation, Round 1 (six items), Round 2 (seven follow-ups), Non-goals, and How to verify sections.






## [2026-08-09 22:23] Completed: Set up pytest infrastructure with initial unit tests. 18 tests pass covering validate_url, normalize_url, and should_send_down_notification scenarios. (e4c8f38c4f5d)
Completed: Set up pytest infrastructure with initial unit tests. 18 tests pass covering validate_url, normalize_url, and should_send_down_notification scenarios.




## [2026-08-09 22:44] Extracted _upsert_subscription (3 occurrences: def + 2 call sites), _build_endpoint_keyboard (3 occurrences), _ENDPOINT_LIST_TEXT constant. subscribe_command and refresh_endpoints_callback now share the helper. Line count: 697 -> 614 (-83 lines). Added NOTE comment on /unsubscribe handler. All imports verified OK. (36c094ca5b33)
Extracted _upsert_subscription (3 occurrences: def + 2 call sites), _build_endpoint_keyboard (3 occurrences), _ENDPOINT_LIST_TEXT constant. subscribe_command and refresh_endpoints_callback now share the helper. Line count: 697 -> 614 (-83 lines). Added NOTE comment on /unsubscribe handler. All imports verified OK.


## [2026-08-09 22:44] Created app/core/startup.py with send_startup_notification and send_startup_notifications moved verbatim from __init__.py. Fixed imports. __init__.py reduced from 228 to 100 lines, now imports from .core.startup. All acceptance checks pass: imports work, no function defs in __init__.py. (494a42ae6a55)
Created app/core/startup.py with send_startup_notification and send_startup_notifications moved verbatim from __init__.py. Fixed imports. __init__.py reduced from 228 to 100 lines, now imports from .core.startup. All acceptance checks pass: imports work, no function defs in __init__.py.
