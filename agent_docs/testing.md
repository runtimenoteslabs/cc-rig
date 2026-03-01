# Testing

# Testing — FastAPI

## Stack
- **Framework**: pytest + pytest-asyncio.
- **Client**: `httpx.AsyncClient` with `ASGITransport` (not deprecated `TestClient` for async tests).
- **Database**: test-scoped database with rollback per test, or SQLite in-memory.

## Principles
- Test through the HTTP layer using the ASGI test client. This validates routing, serialization, and dependency injection together.
- Override dependencies with `app.dependency_overrides[get_db] = ...` for isolation.
- Fixtures: define `client`, `db_session`, `auth_headers` as session/function-scoped pytest fixtures.
- Use `factory_boy` or simple factory functions for test data creation.

## File Layout
```
tests/
  conftest.py         # Shared fixtures (client, db, auth)
  api/
    test_users.py     # Endpoint tests grouped by router
    test_items.py
  services/
    test_user_service.py  # Unit tests for business logic
```

## Commands
- `pytest` — run all tests.
- `pytest -x --tb=short` — stop on first failure, short traceback.
- `pytest --cov=app --cov-report=term-missing` — with coverage.

## E2E Test Matrix

The E2E test matrix (`tests/integration/test_e2e_matrix.py`) provides systematic verification of `cc-rig init` output across all configuration dimensions: 11 templates × 5 workflows × 4 harness levels × 4 feature flags. 16 representative scenarios plus full cross-product validation.

- **Run**: `pytest tests/integration/test_e2e_matrix.py -v`
- **Spec**: `specs/e2e-test-matrix.md` — full scenario descriptions, expected outputs, coverage matrix

Each generated project includes `CLAUDE.local.md` (personal preferences, gitignored) and uses `@import` syntax for agent docs in CLAUDE.md. The E2E suite validates both features.
