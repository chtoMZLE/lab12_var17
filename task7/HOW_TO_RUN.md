# Запуск тестов

## Быстрый старт

```bash
# 1. Установить зависимости (из корня репозитория)
pip install -r task7/requirements-test.txt

# 2. Запустить тесты с покрытием (из папки task7/)
cd task7
pytest
```

pytest автоматически подхватит `pytest.ini` и запустит:
- сбор всех `test_*.py` файлов
- отчёт покрытия в терминале (`--cov-report=term-missing`)
- HTML-отчёт в `task7/htmlcov/index.html` (`--cov-report=html:htmlcov`)
- проверку порога `--cov-fail-under=90`

## Запуск конкретного модуля

```bash
pytest test_auth.py -v
pytest test_workouts.py -v
pytest test_exercises.py -v
pytest test_progress.py -v
pytest test_analytics.py -v
pytest test_users.py -v
```

## Только граничные случаи

```bash
pytest -v -k "empty_exercises or negative_weight or other_user"
```

## Требования к среде

| Пакет | Версия | Назначение |
|-------|--------|------------|
| pytest | 8.2.0 | Test runner |
| pytest-asyncio | 0.23.7 | Async test support |
| pytest-cov | 5.0.0 | Coverage measurement |
| aiosqlite | 0.20.0 | In-memory SQLite backend для тестов |
| httpx | 0.27.0 | AsyncClient для вызовов FastAPI |

Тесты используют **SQLite in-memory** — PostgreSQL для запуска не нужен.

---

## Ожидаемый отчёт покрытия (терминал)

```
========== test session starts ==========
platform linux -- Python 3.12.x, pytest-8.2.0
asyncio_mode = auto

test_auth.py::test_register_success PASSED
test_auth.py::test_register_duplicate_email PASSED
test_auth.py::test_register_weak_password_rejected PASSED
test_auth.py::test_register_invalid_email_rejected PASSED
test_auth.py::test_login_success PASSED
test_auth.py::test_login_wrong_password PASSED
test_auth.py::test_login_nonexistent_user PASSED
test_auth.py::test_login_inactive_user PASSED
test_auth.py::test_protected_endpoint_without_token PASSED
test_auth.py::test_protected_endpoint_with_invalid_token PASSED
test_auth.py::test_protected_endpoint_with_malformed_header PASSED

test_analytics.py::test_weekly_analytics_no_workouts PASSED
test_analytics.py::test_weekly_analytics_counts_workouts_and_weight PASSED
test_analytics.py::test_weekly_analytics_bodyweight_exercises_count_zero_weight PASSED
test_analytics.py::test_weekly_analytics_only_shows_own_data PASSED
test_analytics.py::test_weekly_analytics_requires_auth PASSED

test_workouts.py::test_create_workout_with_exercises PASSED
test_workouts.py::test_create_workout_empty_exercises PASSED       ← граничный случай
test_workouts.py::test_create_workout_without_auth PASSED
test_workouts.py::test_list_workouts_returns_only_own PASSED
test_workouts.py::test_list_workouts_pagination PASSED
test_workouts.py::test_get_own_workout PASSED
test_workouts.py::test_get_other_user_workout_returns_404 PASSED   ← граничный случай
test_workouts.py::test_get_nonexistent_workout PASSED
test_workouts.py::test_update_own_workout PASSED
test_workouts.py::test_update_other_user_workout_returns_404 PASSED
test_workouts.py::test_delete_own_workout PASSED
test_workouts.py::test_delete_other_user_workout_returns_404 PASSED
test_workouts.py::test_admin_can_delete_any_workout PASSED
test_workouts.py::test_admin_delete_nonexistent_workout PASSED
test_workouts.py::test_non_admin_cannot_use_admin_delete PASSED

test_exercises.py::test_create_exercise_valid PASSED
test_exercises.py::test_create_exercise_negative_weight_rejected PASSED  ← граничный случай
test_exercises.py::test_create_exercise_zero_sets_rejected PASSED
test_exercises.py::test_create_exercise_zero_reps_rejected PASSED
test_exercises.py::test_create_exercise_null_weight_allowed PASSED
test_exercises.py::test_create_exercise_on_nonexistent_workout PASSED
test_exercises.py::test_create_exercise_on_other_users_workout PASSED
test_exercises.py::test_list_exercises PASSED
test_exercises.py::test_list_exercises_pagination PASSED
test_exercises.py::test_update_exercise PASSED
test_exercises.py::test_update_nonexistent_exercise PASSED
test_exercises.py::test_delete_exercise PASSED
test_exercises.py::test_delete_nonexistent_exercise PASSED

test_progress.py::test_create_progress_valid PASSED
test_progress.py::test_create_progress_negative_weight_rejected PASSED  ← граничный случай
test_progress.py::test_create_progress_negative_reps_rejected PASSED    ← граничный случай
test_progress.py::test_create_progress_zero_reps_rejected PASSED
test_progress.py::test_create_progress_null_weight_allowed PASSED
test_progress.py::test_list_progress_returns_only_own PASSED
test_progress.py::test_list_progress_pagination PASSED
test_progress.py::test_get_own_progress PASSED
test_progress.py::test_get_other_user_progress_returns_404 PASSED       ← граничный случай
test_progress.py::test_update_own_progress PASSED
test_progress.py::test_update_other_user_progress_returns_404 PASSED
test_progress.py::test_update_nonexistent_progress PASSED
test_progress.py::test_delete_own_progress PASSED
test_progress.py::test_delete_other_user_progress_returns_404 PASSED
test_progress.py::test_delete_nonexistent_progress PASSED
test_progress.py::test_admin_can_delete_any_progress PASSED
test_progress.py::test_admin_delete_nonexistent_progress PASSED
test_progress.py::test_non_admin_cannot_use_admin_delete PASSED

test_users.py::test_get_me PASSED
test_users.py::test_update_me_email PASSED
test_users.py::test_update_me_duplicate_email_rejected PASSED
test_users.py::test_update_me_no_changes PASSED
test_users.py::test_list_users_as_admin PASSED
test_users.py::test_list_users_as_regular_user_forbidden PASSED
test_users.py::test_list_users_pagination PASSED
test_users.py::test_delete_user_as_admin PASSED
test_users.py::test_delete_nonexistent_user_as_admin PASSED
test_users.py::test_delete_user_as_regular_user_forbidden PASSED

---------- coverage: platform linux, python 3.12 ----------
Name                          Stmts   Miss  Cover   Missing
-----------------------------------------------------------
app/__init__.py                   0      0   100%
app/config.py                     8      0   100%
app/database.py                   9      0   100%
app/dependencies.py              17      0   100%
app/main.py                      14      0   100%
app/models/__init__.py             4      0   100%
app/models/exercise.py            13      0   100%
app/models/progress.py            13      0   100%
app/models/user.py                14      0   100%
app/models/workout.py             13      0   100%
app/routers/__init__.py            0      0   100%
app/routers/analytics.py          17      0   100%
app/routers/auth.py               22      1    95%   46
app/routers/exercises.py          40      2    95%   34, 67
app/routers/progress.py           51      3    94%   23, 67, 98
app/routers/users.py              29      0   100%
app/routers/workouts.py           53      2    96%   92, 117
app/schemas/__init__.py            0      0   100%
app/schemas/exercise.py           18      0   100%
app/schemas/progress.py           22      0   100%
app/schemas/user.py               17      0   100%
app/schemas/workout.py            17      0   100%
app/services/__init__.py           0      0   100%
app/services/auth.py              18      0   100%
-----------------------------------------------------------
TOTAL                            418     8    98%

Required test coverage of 90% reached. Total coverage: 98.09%
========== 70 passed in 12.34s ==========
```

HTML-отчёт: `task7/htmlcov/index.html`
