"""Django framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (Django)
- Fat models, thin views. Business logic lives on model methods and \
managers, not in views or serializers.
- Use class-based views (CBVs) for standard CRUD. Function-based views \
only for one-off endpoints that don't fit a generic pattern.
- Always use the ORM for queries. Raw SQL only when the ORM genuinely \
cannot express the query (annotate, Subquery, and Window cover most cases).
- Never import settings directly — use `django.conf.settings` or \
django-environ for environment-specific config.
- Migrations are code. Review auto-generated migrations before committing. \
Never edit a migration that has been applied to production.
- Use Django's permission framework and decorators (`@login_required`, \
`@permission_required`) — do not roll custom auth middleware.
- Keep `urls.py` files per-app. The project-level `urls.py` should only \
include app URL confs.\
""",
    "architecture": """\
# Architecture — Django

## Directory Layout
```
project/
  settings/
    base.py           # Shared settings
    development.py    # DEBUG=True, console email backend
    production.py     # Security middleware, real caches
  urls.py             # Root URL conf — includes per-app urls
  wsgi.py / asgi.py
apps/
  users/
    models.py         # User-related models + managers
    views.py          # ViewSets or CBVs
    serializers.py    # DRF serializers (if using DRF)
    urls.py           # App-level URL patterns
    admin.py          # ModelAdmin customizations
    signals.py        # Post-save / pre-delete signals
    tests/
      test_models.py
      test_views.py
  core/
    models.py         # Abstract base models (TimestampMixin, etc.)
    middleware.py      # Custom middleware
    management/
      commands/        # Custom manage.py commands
```

## Key Patterns
- **App-per-domain**: each Django app owns one bounded context. Apps \
communicate through well-defined model interfaces, not cross-app imports.
- **Custom managers**: encapsulate common query patterns \
(`User.objects.active()`, `Order.objects.pending()`).
- **Signals sparingly**: use for cross-cutting concerns (audit log, cache \
invalidation). Prefer explicit method calls for business logic.
- **Middleware pipeline**: request flows through SecurityMiddleware → \
SessionMiddleware → AuthMiddleware → custom middleware → view.
- **Admin as ops tool**: customize `ModelAdmin` with `list_display`, \
`search_fields`, `readonly_fields`. Admin is for staff, not end users.\
""",
    "conventions": """\
# Conventions — Django

## Naming
- Apps: short, singular nouns (`user`, `order`, `invoice`).
- Models: singular PascalCase (`Order`, not `Orders`).
- URL names: `app_name:action-noun` (`users:detail`, `orders:list`).
- Template dirs mirror app structure: `templates/users/detail.html`.

## Model Guidelines
- Every model gets `__str__`. Use `Meta.ordering` for default sort.
- Use `choices` with `TextChoices`/`IntegerChoices` enums, not raw strings.
- Add `db_index=True` on fields used in filter/order_by. Use `indexes` \
Meta for compound indexes.
- Soft-delete via `is_active` flag + custom manager, not by overriding \
`delete()`.

## View Guidelines
- DRF ViewSets for API endpoints. Use `@action` for non-CRUD operations.
- Pagination on all list endpoints. Default: `PageNumberPagination`.
- Filter backends: `django-filter` for query-param filtering.

## Settings
- Use `django-environ` or `os.environ` via `settings/base.py`.
- `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS` from environment — never \
hardcoded.
- Split settings: `base.py` (shared), `development.py`, `production.py`, \
`testing.py`.\
""",
    "testing": """\
# Testing — Django

## Stack
- **Framework**: pytest + pytest-django.
- **Factories**: factory_boy with `DjangoModelFactory`.
- **API testing**: DRF's `APIClient` or `APIRequestFactory`.

## Principles
- Use `pytest.mark.django_db` for any test touching the database.
- Factory-based test data — never use fixtures.json or raw \
`Model.objects.create()` scattered across tests.
- Test views through the HTTP layer (`client.get`, `client.post`) to \
exercise URL routing, middleware, and serialization.
- Model tests: cover custom methods, managers, constraints, and signals.

## File Layout
```
apps/users/tests/
  conftest.py           # App-specific fixtures
  test_models.py        # Model method + manager tests
  test_views.py         # API endpoint tests
  test_serializers.py   # Serializer validation tests
  factories.py          # factory_boy factories
```

## Commands
- `pytest` — run all tests.
- `pytest apps/users/` — run one app's tests.
- `pytest --reuse-db` — skip DB creation for faster reruns.
- `python manage.py test` — Django's built-in runner (CI fallback).\
""",
    "deployment": """\
# Deployment — Django

## Build
- `python manage.py collectstatic --noinput` — gather static files.
- `python manage.py migrate --noinput` — apply pending migrations.
- `python manage.py check --deploy` — verify production settings.

## Production Server
- Gunicorn: `gunicorn project.wsgi:application -w 4 -b 0.0.0.0:8000`.
- Behind nginx or Caddy for TLS, static file serving, and buffering.
- For async views/channels: `daphne` or `uvicorn project.asgi:application`.

## Docker
```dockerfile
FROM python:3.12-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "project.wsgi:application", "-w", "4", "-b", "0.0.0.0:8000"]
```

## Environment
- `DJANGO_SETTINGS_MODULE=project.settings.production` in environment.
- Database via `DATABASE_URL` parsed by `dj-database-url`.
- Static files: S3/GCS via `django-storages` or whitenoise for simple \
deploys.\
""",
}
