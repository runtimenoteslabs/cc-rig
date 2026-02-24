"""Flask framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (Flask)
- Use the application factory pattern (`create_app()` in `app/__init__.py`). \
Never create the Flask instance at module level.
- Organize routes with Blueprints. One Blueprint per domain/feature area. \
Register Blueprints in the factory.
- Configuration via `app.config.from_object()` or `app.config.from_envvar()`. \
Never hardcode secrets or environment-specific values.
- Use Flask extensions properly: initialize with `ext.init_app(app)` in the \
factory, not `ext = Ext(app)` at module level.
- Error handlers: register `@app.errorhandler(404)` and \
`@app.errorhandler(500)` returning JSON (API) or templates (web).
- Request context: access `request`, `g`, `current_app` only inside \
request handlers or functions called from them. Never at import time.
- Use `flask.abort(status)` for HTTP errors. Custom exceptions with \
`@app.errorhandler(CustomError)` for domain errors.\
""",
    "architecture": """\
# Architecture — Flask

## Directory Layout
```
app/
  __init__.py         # create_app() factory
  extensions.py       # Extension instances (db, migrate, login, etc.)
  models/
    user.py           # SQLAlchemy models
    order.py
  api/
    __init__.py       # API blueprint registration
    users.py          # /api/users routes
    orders.py         # /api/orders routes
  services/
    user_service.py   # Business logic layer
  schemas/
    user_schema.py    # Marshmallow or Pydantic schemas
  templates/          # Jinja2 templates (if serving HTML)
  static/             # CSS, JS, images (if serving HTML)
config.py             # Config classes (Development, Production, Testing)
wsgi.py               # WSGI entry point: app = create_app()
migrations/           # Flask-Migrate / Alembic migrations
```

## Key Patterns
- **Application factory**: `create_app(config_name)` creates and configures \
the app, registers blueprints and extensions, returns the app.
- **Blueprint → Service → Model**: routes are thin; business logic in \
services; DB access through SQLAlchemy models/queries.
- **Extension pattern**: `db = SQLAlchemy()` in `extensions.py`, \
`db.init_app(app)` in factory. Importable everywhere without circular deps.
- **Config classes**: `Development(Config)`, `Production(Config)` — select \
via `FLASK_CONFIG` env var.
- **Context processors**: register with `@app.context_processor` for \
template globals.
- **CLI commands**: `@app.cli.command()` for management tasks (seed DB, \
create admin).\
""",
    "conventions": """\
# Conventions — Flask

## Naming
- Blueprints: short names matching the domain (`api`, `auth`, `admin`).
- Route functions: verb_noun (`get_users`, `create_order`).
- Models: singular PascalCase (`User`, `Order`).
- Config classes: environment name (`Development`, `Production`, `Testing`).

## Route Guidelines
- Use `@bp.route` with explicit `methods=["GET"]` — never rely on \
implicit GET.
- Return tuples `(response, status_code)` or use `jsonify()` for JSON.
- Parse request data: `request.get_json()` for JSON, `request.form` for \
forms, `request.args` for query params.
- Validate input with Marshmallow schemas or a validation library before \
passing to services.

## Extension Usage
- SQLAlchemy: define models inheriting from `db.Model`.
- Flask-Migrate: never edit migration files manually after applying.
- Flask-Login: use `@login_required` decorator. `current_user` is the \
proxy.
- Flask-CORS: configure per-blueprint if APIs and web share the app.

## Error Handling
- Register error handlers on the app, not on blueprints (unless scoped).
- Return JSON `{"error": "message"}` with proper status codes for APIs.
- Log exceptions at ERROR level in 500 handlers. Use `app.logger`.\
""",
    "testing": """\
# Testing — Flask

## Stack
- **Framework**: pytest.
- **Client**: `app.test_client()` for HTTP-layer tests.
- **Database**: test-scoped DB with rollback, or SQLite in-memory.
- **Factories**: factory_boy with `SQLAlchemyModelFactory`.

## Principles
- Use the `app` fixture (application factory with test config) and the \
`client` fixture (`app.test_client()`).
- Test through HTTP: `client.get("/api/users")`, assert status and JSON.
- Isolate database tests with transaction rollback per test or an \
in-memory SQLite database.
- Mock external services (email, payment) at the service layer boundary.

## File Layout
```
tests/
  conftest.py          # app, client, db fixtures
  test_users.py        # User API endpoint tests
  test_orders.py       # Order API endpoint tests
  test_services/
    test_user_service.py  # Service unit tests
  factories.py         # factory_boy factories
```

## Commands
- `pytest` — run all tests.
- `pytest -x -v` — stop on first failure, verbose.
- `pytest --cov=app` — with coverage report.
- `flask test` — custom CLI command (if registered).\
""",
    "deployment": """\
# Deployment — Flask

## Build
- No build step. Ensure `requirements.txt` is up to date.
- `flask db upgrade` — apply pending migrations.

## Production Server
- Gunicorn: `gunicorn wsgi:app -w 4 -b 0.0.0.0:8000`.
- Never use `flask run` or the development server in production.
- Behind nginx or Caddy for TLS, static files, and buffering.

## Docker
```dockerfile
FROM python:3.12-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["gunicorn", "wsgi:app", "-w", "4", "-b", "0.0.0.0:8000"]
```

## Environment
- `FLASK_CONFIG=production` to select the Production config class.
- `SECRET_KEY`, `DATABASE_URL` from environment variables.
- Never commit `.env`. Provide `.env.example` as a reference.
- Static files: serve via nginx or a CDN, not Flask's built-in server.\
""",
}
