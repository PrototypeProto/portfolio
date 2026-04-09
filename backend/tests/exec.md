## Currently: 121 tests

- pytest.ini — config, asyncio mode, test paths

- tests/ 
- tests/conftest.py — async Postgres engine (separate test DB), per-test transaction rollback, AsyncClient with dependency overrides, and factory helpers to create users/tokens without going through HTTP
- tests/test_utils.py — pure unit tests, no I/O
- tests/test_auth_routes.py — full HTTP integration tests for the entire auth flow
- tests/test_role_checker.py — dependency-level tests for RoleChecker and CookieTokenBearer
- tests/test_admin_routes.py — admin endpoint tests
- tests/test_forum_routes.py — forum endpoint tests

# Exec

## Start test containers (one-time per dev session)
docker compose --profile test up -d

## Run all tests
cd backend
pytest

## Run trigger-dependent tests (requires migrations applied to test DB first)
alembic -x db_url=postgresql+asyncpg://postgres:postgres@localhost:5433/portfolio_test upgrade head
pytest --run-triggers

## Stop test containers when done
docker compose --profile test down