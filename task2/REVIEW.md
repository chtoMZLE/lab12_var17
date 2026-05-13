# Code Review — Задание повышенной сложности 2

Аудит кода, сгенерированного в task1. Найдено и исправлено 7 проблем.

---

## Таблица находок и исправлений

| # | Категория | Что сгенерировал ИИ | В чём проблема | Как исправил |
|---|-----------|---------------------|----------------|--------------|
| 1 | **Безопасность** — тайминг-атака | `routers/auth.py`: `if user is None or not verify_password(...)` — short-circuit evaluation | Если email не найден, `verify_password` (bcrypt) **не вызывается** → ответ возвращается быстрее. Атакующий может перебором определять существующие email-адреса, замеряя время ответа | Всегда вызываем `verify_password` с реальным или заглушечным хешем (`_DUMMY_HASH`), чтобы время ответа было одинаковым |
| 2 | **Безопасность** — слабый дефолт | `config.py`: `SECRET_KEY: str = "change-me-to-a-long-random-secret-key"` | При деплое без `.env` приложение стартует с **известным** секретом → злоумышленник может подписывать произвольные JWT | Заменено на `Field(..., min_length=32)` — Pydantic выбрасывает `ValidationError` при старте, если переменная не задана или короче 32 символов |
| 3 | **Производительность** — лишние DB round-trips | `routers/workouts.py`: после `commit()` вызывался `await db.refresh(workout)`, а затем сразу ещё один `SELECT` с `selectinload` | `db.refresh` делает отдельный SELECT, но **не загружает** lazy relationships — сразу после него шёл второй запрос для загрузки упражнений. Итого: 2 лишних round-trip к БД (в `create_workout` и `update_workout`) | Убрали `db.refresh(workout)` перед re-fetch — оставили только один запрос с `selectinload` |
| 4 | **Производительность** — отсутствие пагинации | `list_workouts`, `list_users`, `list_exercises`, `list_progress` — без параметров пагинации | При тысячах записей эндпоинт загружает **все** строки в память → OOM, таймауты, медленные ответы | Добавлены `skip: int = Query(0, ge=0)` и `limit: int = Query(100, ge=1, le=1000)` ко всем list-эндпоинтам + `.offset()/.limit()` в запросы |
| 5 | **Стиль / типизация** — неверный тип генератора | `database.py`: `async def get_db() -> AsyncSession` | Функция содержит `yield` → это **асинхронный генератор**, а не обычная корутина. mypy в strict-режиме выдаёт ошибку типа | Исправлен тип на `-> AsyncGenerator[AsyncSession, None]` (импорт из `collections.abc`) |
| 6 | **Обработка исключений БД** — голый HTTP 500 | `exercises.py`, `progress.py`: нет `try/except IntegrityError` вокруг `db.commit()` | При нарушении FK-constraint (race condition: workout удалили между проверкой владельца и INSERT упражнения) — необработанный `IntegrityError` пробрасывается как HTTP **500 Internal Server Error** | Обёрнуто в `try/except IntegrityError` → `db.rollback()` → HTTP 404 / 422 с понятным сообщением |
| 7 | **PEP 484 / стиль** — отсутствие type hints | `alembic/env.py`: `def do_run_migrations(connection)` — без аннотации параметра и возвращаемого типа | Нарушение PEP 484; mypy не может проверить корректность использования `connection` внутри функции | Добавлены аннотации: `(connection: AsyncConnection) -> None` (импорт `AsyncConnection` из `sqlalchemy.ext.asyncio`) |

---

## Файлы, затронутые исправлениями

| Файл | Изменения |
|------|-----------|
| `task1/app/config.py` | SECRET_KEY: убран дефолт, добавлен `Field(..., min_length=32)` |
| `task1/app/database.py` | Тип возврата `get_db` → `AsyncGenerator[AsyncSession, None]` |
| `task1/app/routers/auth.py` | Устранена тайминг-атака через `_DUMMY_HASH` |
| `task1/app/routers/workouts.py` | Убраны лишние `db.refresh`; добавлена пагинация |
| `task1/app/routers/users.py` | Добавлена пагинация в `list_users` |
| `task1/app/routers/exercises.py` | Добавлена пагинация; добавлен `except IntegrityError` |
| `task1/app/routers/progress.py` | Добавлена пагинация; добавлен `except IntegrityError` |
| `task1/alembic/env.py` | Добавлены type hints в `do_run_migrations` |
