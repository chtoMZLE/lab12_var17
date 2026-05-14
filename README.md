# Лабораторная работа №12

| | |
|---|---|
| **Вариант** | 17 |
| **Студент** | Тараканова Мария Вадимовна |
| **Группа** | 221131 |
| **Предметная область** | Платформа для спортивных тренировок |

---

## Содержание

- [Ключевые особенности](#ключевые-особенности)
- [Технологический стек](#технологический-стек)
- [Структура проекта](#структура-проекта)
- [Сборка и запуск модулей](#сборка-и-запуск-модулей)
- [Тестирование](#тестирование)

---

## Ключевые особенности

### Задание 1 — Веб-приложение (task1/)
- **JWT-аутентификация** с bcrypt-хешированием паролей и защитой от timing-атак при логине
- **CRUD** для четырёх сущностей: User, Workout, Exercise, Progress — с проверкой прав доступа (пользователь видит только свои данные)
- **Аналитический эндпоинт** `/analytics/weekly` — суммарный поднятый вес и количество тренировок за 7 дней
- **Роль администратора** с расширенными правами удаления любых объектов
- **Async SQLAlchemy 2.x** — все запросы к БД неблокирующие
- **Alembic** — версионированные миграции схемы БД
- Готов к запуску через **Docker / docker-compose**

### Задание 2 — Code Review (task2/)
Проведён строгий аудит кода из Задания 1. Найдено и исправлено **7 проблем**:

| # | Категория | Проблема | Исправление |
|---|-----------|----------|-------------|
| 1 | Безопасность | Timing-атака в `/auth/login`: при несуществующем email `verify_password` не вызывался | Всегда вызываем `pwd_context.hash()` с dummy-хешем |
| 2 | Безопасность | Хардкод `SECRET_KEY = "change-me-..."` | `Field(..., min_length=32)` — app падает при старте без ключа |
| 3 | Производительность | `db.refresh()` перед re-fetch с `selectinload` — лишний round-trip к БД | Убран избыточный `refresh` |
| 4 | Производительность | Все list-эндпоинты без пагинации | `skip` / `limit` query-параметры на всех list-эндпоинтах |
| 5 | Типизация | `async def get_db() -> AsyncSession` — неверный тип генератора | `-> AsyncGenerator[AsyncSession, None]` |
| 6 | Обработка ошибок | Нет `except IntegrityError` в create_exercise / create_progress | Обёрнуто в `try/except IntegrityError` → HTTP 404/422 |
| 7 | PEP 484 | `do_run_migrations(connection)` без type hints в alembic/env.py | `(connection: AsyncConnection) -> None` |

### Задание 4 — CI/CD с ИИ (task4/ + .github/)
- **GitHub Actions** workflow запускается при каждом открытии / обновлении PR
- Python-скрипт получает `git diff`, отправляет в **Claude API** (модель `claude-opus-4-7`)
- Ответ ИИ публикуется как **комментарий к PR** через GitHub REST API
- Промпт структурирован: описание изменений, список файлов, найденные проблемы с категориями, покрытие тестами, итоговый вердикт
- Безопасная конкатенация промпта — диффы с `{переменными}` не вызывают `KeyError`

### Задание 7 — Unit-тесты (task7/)
- **77 тестов** покрывают все роутеры приложения из Задания 1
- Покрытие кода: **96.23%** (порог — 90%)
- Асинхронные тесты через `pytest-asyncio`
- In-memory **SQLite** — PostgreSQL для запуска не нужен
- Граничные случаи: пустой список упражнений, отрицательный вес, доступ к чужим данным

---

## Технологический стек

### Backend (task1)
| Компонент | Технология |
|-----------|-----------|
| Веб-фреймворк | FastAPI |
| ORM | SQLAlchemy 2.x (async) |
| База данных | PostgreSQL + asyncpg |
| Валидация | Pydantic v2 |
| Миграции | Alembic |
| Аутентификация | JWT (python-jose) + bcrypt (passlib) |
| Контейнеризация | Docker, docker-compose |

### CI/CD (task4)
| Компонент | Технология |
|-----------|-----------|
| Платформа | GitHub Actions |
| AI-модель | Claude claude-opus-4-7 (Anthropic API) |
| HTTP-клиент | httpx |

### Тестирование (task7)
| Компонент | Технология |
|-----------|-----------|
| Test runner | pytest 8.x |
| Async тесты | pytest-asyncio |
| HTTP-клиент тестов | httpx AsyncClient + ASGITransport |
| Тестовая БД | SQLite in-memory (aiosqlite) |
| Покрытие | pytest-cov / coverage.py |

---

## Структура проекта

```
lab12-var17/
│
├── .github/
│   └── workflows/
│       └── ai-review.yml          # GitHub Actions: AI-анализ PR
│
├── task1/                         # Задание 1: веб-приложение
│   ├── app/
│   │   ├── main.py                # Точка входа FastAPI
│   │   ├── config.py              # Настройки (pydantic-settings)
│   │   ├── database.py            # Async engine + сессия
│   │   ├── dependencies.py        # get_current_user, get_current_admin
│   │   ├── models/                # SQLAlchemy ORM модели
│   │   │   ├── user.py            #   User (роли: user / admin)
│   │   │   ├── workout.py         #   Workout
│   │   │   ├── exercise.py        #   Exercise
│   │   │   └── progress.py        #   Progress / рекорды
│   │   ├── schemas/               # Pydantic схемы (Create / Update / Read)
│   │   ├── routers/               # Эндпоинты
│   │   │   ├── auth.py            #   POST /auth/register, /auth/login
│   │   │   ├── users.py           #   GET/PATCH /users/me, admin CRUD
│   │   │   ├── workouts.py        #   CRUD /workouts/
│   │   │   ├── exercises.py       #   CRUD /workouts/{id}/exercises/
│   │   │   ├── progress.py        #   CRUD /progress/
│   │   │   └── analytics.py       #   GET /analytics/weekly
│   │   └── services/
│   │       └── auth.py            # JWT + bcrypt
│   ├── alembic/                   # Миграции БД
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── .env.example
│
├── task2/
│   └── REVIEW.md                  # Задание 2: таблица code review
│
├── task4/                         # Задание 4: AI CI/CD
│   ├── ai_review.py               # Скрипт: diff → Claude → GitHub comment
│   ├── test_ai_review.py          # 30 unit-тестов скрипта
│   ├── requirements.txt
│   └── pytest.ini
│
├── task7/                         # Задание 7: тесты приложения
│   ├── conftest.py                # Фикстуры: SQLite engine, клиент, пользователи
│   ├── test_auth.py               # 11 тестов аутентификации
│   ├── test_workouts.py           # 15 тестов тренировок
│   ├── test_exercises.py          # 13 тестов упражнений
│   ├── test_progress.py           # 18 тестов прогресса
│   ├── test_analytics.py          # 5 тестов аналитики
│   ├── test_users.py              # 10 тестов пользователей
│   ├── test_misc.py               # 5 тестов (health, валидаторы, edge cases)
│   ├── requirements-test.txt
│   └── pytest.ini
│
├── workplan                       # Исходное задание
├── .gitignore
└── README.md
```

---

## Сборка и запуск модулей

### Задание 1 — Запуск через Docker

```bash
cd task1

# Скопировать конфиг окружения и задать секретный ключ
cp .env.example .env
# Отредактировать .env: установить SECRET_KEY длиной >= 32 символов

# Поднять PostgreSQL + приложение
docker-compose up --build
```

После запуска:
- API доступно по адресу: `http://localhost:8000`
- Интерактивная документация: `http://localhost:8000/docs`
- Альтернативная документация: `http://localhost:8000/redoc`

**Основные эндпоинты:**

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/auth/register` | Регистрация |
| `POST` | `/auth/login` | Вход, получение JWT |
| `GET` | `/users/me` | Профиль текущего пользователя |
| `POST` | `/workouts/` | Создать тренировку |
| `GET` | `/workouts/` | Список своих тренировок |
| `POST` | `/workouts/{id}/exercises/` | Добавить упражнение |
| `GET` | `/analytics/weekly` | Аналитика за 7 дней |

### Задание 1 — Запуск без Docker

```bash
cd task1
pip install -r requirements.txt

# Применить миграции (PostgreSQL должен быть запущен)
alembic upgrade head

# Запустить сервер
uvicorn app.main:app --reload
```

### Задание 4 — Настройка AI Code Review

1. В настройках репозитория GitHub добавить секрет `ANTHROPIC_API_KEY`
2. Workflow запустится автоматически при создании Pull Request

Локальный тест скрипта:
```bash
cd task4
pip install -r requirements.txt

export ANTHROPIC_API_KEY=your_key
export GITHUB_TOKEN=your_token
export REPO=owner/repo
export PR_NUMBER=1
git diff main...HEAD > /tmp/pr_diff.txt
export DIFF_FILE=/tmp/pr_diff.txt

python ai_review.py
```

---

## Тестирование

### Задание 7 — Тесты приложения (task1)

```bash
cd task7
pip install -r requirements-test.txt
pytest
```

Запуск отдельных модулей:
```bash
pytest test_auth.py -v        # аутентификация
pytest test_workouts.py -v    # тренировки
pytest test_exercises.py -v   # упражнения
pytest test_progress.py -v    # прогресс
pytest test_analytics.py -v   # аналитика
pytest test_users.py -v       # пользователи
```

Только граничные случаи:
```bash
pytest -v -k "empty_exercises or negative_weight or other_user"
```

**Результаты:**

```
============================= test session starts =============================
collected 77 items

test_analytics.py .....                                              [  6%]
test_auth.py ...........                                             [ 20%]
test_exercises.py .............                                      [ 37%]
test_misc.py .....                                                   [ 44%]
test_progress.py ..................                                   [ 67%]
test_users.py ..........                                             [ 80%]
test_workouts.py ...............                                     [100%]

TOTAL                             504     19    96%
Required test coverage of 90% reached. Total coverage: 96.23%
========================== 77 passed in 22.76s ================================
```

HTML-отчёт покрытия генерируется автоматически в `task7/htmlcov/index.html`.

**Граничные случаи (обязательные по заданию):**

| Тест | Файл | Проверяет |
|------|------|-----------|
| `test_create_workout_empty_exercises` | test_workouts.py | Тренировка с `exercises: []` — валидна |
| `test_create_exercise_negative_weight_rejected` | test_exercises.py | `weight_kg: -10.0` → HTTP 422 |
| `test_create_progress_negative_weight_rejected` | test_progress.py | `max_weight_kg: -1.0` → HTTP 422 |
| `test_create_progress_negative_reps_rejected` | test_progress.py | `total_reps: -3` → HTTP 422 |
| `test_get_other_user_workout_returns_404` | test_workouts.py | Чужая тренировка → HTTP 404 |
| `test_get_other_user_progress_returns_404` | test_progress.py | Чужой прогресс → HTTP 404 |

### Задание 4 — Тесты AI-скрипта

```bash
cd task4
pip install anthropic httpx pytest
pytest
```

**Результаты:**

```
============================= test session starts =============================
collected 30 items

test_ai_review.py ..............................  [100%]

============================= 30 passed in 0.57s ==============================
```

Все 30 тестов работают без реальных API-вызовов — Anthropic SDK и httpx замокированы через `unittest.mock`.

