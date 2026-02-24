"""FastAPI framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (FastAPI)
- All route handlers must be `async def`. Use sync `def` only for pure \
CPU-bound work with no I/O.
- Request/response models use Pydantic v2 `BaseModel`. Never pass raw \
dicts across API boundaries.
- Use `Depends()` for dependency injection — database sessions, auth, \
config, and shared services.
- Raise `HTTPException` (or custom subclasses) for error responses. \
Never return bare dicts with status codes.
- Path operations go in routers (`APIRouter`), not directly on the `app`.
- Background tasks use `BackgroundTasks` parameter or Celery/ARQ for \
long-running work. Never block the event loop.
- Always set `response_model` on endpoints to control serialization \
and auto-generate OpenAPI schemas.\
""",
    "architecture": """\
# Architecture — FastAPI

## Directory Layout
```
app/
  main.py             # FastAPI app factory, middleware, lifespan
  api/
    v1/
      router.py       # Includes all v1 route modules
      users.py        # /users endpoints
      items.py        # /items endpoints
    deps.py           # Shared dependencies (get_db, get_current_user)
  models/
    user.py           # SQLAlchemy / SQLModel ORM models
    item.py
  schemas/
    user.py           # Pydantic request/response schemas
    item.py
  services/
    user_service.py   # Business logic layer
  core/
    config.py         # Settings via pydantic-settings
    security.py       # JWT / OAuth2 utilities
  db/
    session.py        # Engine, SessionLocal, get_db dependency
    migrations/       # Alembic migrations
```

## Key Patterns
- **Router → Dependency → Service → Repository**: routes are thin; business \
logic lives in services; DB access in repository functions.
- **Pydantic Settings**: `BaseSettings` with `.env` loading for all config. \
No raw `os.getenv`.
- **Lifespan context manager**: startup/shutdown logic (DB pool, cache \
connections) in `@asynccontextmanager` passed to `FastAPI(lifespan=...)`.
- **Middleware stack**: CORS, trusted-host, request-ID, timing — registered \
in `main.py`.
- **Exception handlers**: register global handlers for `HTTPException`, \
`RequestValidationError`, and domain-specific errors.\
""",
    "conventions": """\
# Conventions — FastAPI

## Naming
- Files: snake_case. Routers: plural nouns (`users.py`, `items.py`).
- Pydantic schemas: `<Entity>Create`, `<Entity>Read`, `<Entity>Update`.
- Service functions: verb-first (`create_user`, `get_user_by_id`).
- Dependencies: `get_*` naming (`get_db`, `get_current_user`).

## Endpoint Guidelines
- Group endpoints in `APIRouter` with a common `prefix` and `tags`.
- Use path parameters for resource identity (`/users/{user_id}`), \
query parameters for filtering/pagination.
- Return explicit `response_model` — never leak ORM objects to the client.
- Use status codes: 201 for creation, 204 for deletes, 422 auto-handled \
by FastAPI for validation.

## Async Best Practices
- Use `httpx.AsyncClient` for outbound HTTP, not `requests`.
- Database: use async drivers (asyncpg, aiosqlite) with async session.
- File I/O: use `aiofiles` or run in threadpool via `run_in_executor`.

## Error Handling
- Domain errors: custom exception classes inheriting `HTTPException`.
- Validation: let Pydantic handle it — do not manually validate request \
bodies.
- Logging: structured JSON logs via `structlog` or stdlib `logging` \
with JSON formatter.\
""",
    "testing": """\
# Testing — FastAPI

## Stack
- **Framework**: pytest + pytest-asyncio.
- **Client**: `httpx.AsyncClient` with `ASGITransport` (not deprecated \
`TestClient` for async tests).
- **Database**: test-scoped database with rollback per test, or SQLite \
in-memory.

## Principles
- Test through the HTTP layer using the ASGI test client. This validates \
routing, serialization, and dependency injection together.
- Override dependencies with `app.dependency_overrides[get_db] = ...` \
for isolation.
- Fixtures: define `client`, `db_session`, `auth_headers` as \
session/function-scoped pytest fixtures.
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
- `pytest --cov=app --cov-report=term-missing` — with coverage.\
""",
    "deployment": """\
# Deployment — FastAPI

## Build
- No build step. Run directly with `uvicorn app.main:app`.
- Pin dependencies with `pip-compile` or `uv pip compile`.

## Docker
```dockerfile
FROM python:3.12-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Production
- Run behind Gunicorn with Uvicorn workers: \
`gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4`.
- Use `--proxy-headers` and `--forwarded-allow-ips` behind a reverse proxy.
- Health check endpoint: `GET /health` returning 200.

## Environment
- All config via environment variables loaded through `pydantic-settings`.
- Never commit `.env`. Provide `.env.example` with dummy values.
- Secrets (DB password, JWT key) injected via orchestrator or vault.\
""",
}
