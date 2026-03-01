"""Laravel (PHP) framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (PHP / Laravel)
- Use Eloquent ORM for database access. Prefer query scopes and \
relationships over raw SQL. Use `where`, `find`, `with` for queries.
- Always validate input with Form Requests (`php artisan make:request`). \
Never trust raw `$request->input()` without validation.
- Follow the Service/Repository pattern for complex business logic. \
Controllers should be thin — delegate to services immediately.
- Use Laravel's dependency injection container. Type-hint interfaces \
in constructors and bind implementations in service providers.
- Route model binding for resource routes — let Laravel resolve models \
from URL parameters automatically.
- Use config() and env() helpers for environment-specific values. \
Never call env() outside config files (it returns null when config is cached).
- Use Blade components and layouts for views. Prefer components over \
@include directives for reusable UI.\
""",
    "architecture": """\
# Architecture — PHP / Laravel

## Directory Layout
```
app/
  Http/
    Controllers/
      UserController.php      # Resource controllers (CRUD actions)
    Requests/
      StoreUserRequest.php    # Form Request validation
    Middleware/
      Authenticate.php        # Auth middleware
  Models/
    User.php                  # Eloquent model (relationships, scopes, casts)
  Services/
    UserService.php           # Business logic
  Repositories/
    UserRepository.php        # Data access layer (optional)
  Providers/
    AppServiceProvider.php    # Service container bindings
config/
  app.php                     # Application configuration
  database.php                # Database connections
database/
  migrations/                 # Timestamped migration files
  seeders/                    # Database seeders
  factories/                  # Model factories for testing
resources/
  views/
    layouts/                  # Blade layout templates
    components/               # Blade components
routes/
  web.php                     # Web routes
  api.php                     # API routes
tests/
  Feature/                    # HTTP/integration tests
  Unit/                       # Unit tests
```

## Key Patterns
- **Resource controllers**: `Route::resource('users', UserController::class)` \
generates standard CRUD routes.
- **Form Requests**: separate validation logic from controllers. Each request \
class defines `rules()` and optionally `authorize()`.
- **Eloquent relationships**: define `hasMany`, `belongsTo`, `morphMany` on \
models. Use `with()` for eager loading to avoid N+1 queries.
- **Service Providers**: register bindings, event listeners, and middleware \
in providers. Boot method for post-registration setup.
- **Migrations**: one migration per schema change. Use `php artisan migrate` \
to apply, never edit old migrations.
- **Events & Listeners**: decouple side effects (emails, notifications) \
from main business logic.\
""",
    "conventions": """\
# Conventions — PHP / Laravel

## Naming
- Models: singular PascalCase (`User`, `OrderItem`). Tables: plural \
snake_case (`users`, `order_items`).
- Controllers: singular PascalCase + Controller suffix (`UserController`).
- Form Requests: verb + model + Request (`StoreUserRequest`, `UpdateUserRequest`).
- Services: model + Service (`UserService`, `PaymentService`).
- Migrations: timestamp prefix with snake_case description.

## Controller Guidelines
- One resource per controller. Use invokable controllers for single-action \
endpoints.
- Return views with `view()` or JSON with `response()->json()`.
- Use route model binding: `public function show(User $user)`.
- Keep controllers thin — max 5-7 lines per action method.

## Model Guidelines
- Define `$fillable` or `$guarded` for mass assignment protection.
- Use attribute casting (`$casts`) for dates, booleans, JSON, enums.
- Named scopes for common queries: `scopeActive`, `scopeRecent`.
- Relationships: always specify the foreign key explicitly for clarity.

## Code Style
- Follow PSR-12 coding standard. Use Laravel Pint for formatting.
- Use strict types: `declare(strict_types=1)` at the top of every file.
- Prefer collection methods (`map`, `filter`, `reduce`) over manual loops.
- Use PHP 8.1+ features: enums, readonly properties, named arguments.\
""",
    "testing": """\
# Testing — PHP / Laravel

## Stack
- **Framework**: PHPUnit (Laravel default) or Pest PHP.
- **HTTP testing**: `$this->get()`, `$this->post()` — built-in HTTP test \
methods with assertion helpers.
- **Database**: `RefreshDatabase` trait for migration-based test isolation, \
or `DatabaseTransactions` for speed.
- **Factories**: Model factories for generating test data with Faker.

## Principles
- Test through the HTTP layer with feature tests. Validates routing, \
middleware, validation, and response format together.
- Unit test services and complex model logic in isolation.
- Use model factories for test data — never seed test data manually.
- Assert response status, JSON structure, and database state.

## File Layout
```
tests/
  Feature/
    UserControllerTest.php     # HTTP endpoint tests
    AuthenticationTest.php     # Auth flow tests
  Unit/
    Services/
      UserServiceTest.php      # Service unit tests
    Models/
      UserTest.php             # Model unit tests
  TestCase.php                 # Base test class
```

## Commands
- `php artisan test` — run all tests.
- `php artisan test --filter=UserControllerTest` — run single test class.
- `php artisan test --parallel` — run tests in parallel.
- `php artisan test --coverage` — with coverage report.\
""",
    "deployment": """\
# Deployment — PHP / Laravel

## Server
- Use Laravel Sail (Docker) for local development.
- Production: Nginx + PHP-FPM or Laravel Octane (Swoole/RoadRunner) \
for high-performance serving.
- Configure `APP_ENV=production` and `APP_DEBUG=false`.

## Docker
```dockerfile
FROM php:8.3-fpm-alpine AS builder
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --optimize-autoloader --no-scripts
COPY . .
RUN php artisan config:cache && php artisan route:cache && php artisan view:cache

FROM php:8.3-fpm-alpine
RUN apk add --no-cache libpq-dev && docker-php-ext-install pdo_pgsql
WORKDIR /app
COPY --from=builder /app /app
EXPOSE 9000
CMD ["php-fpm"]
```

## Production
- Run `php artisan migrate --force` before deploying new code.
- Cache config, routes, and views: `php artisan optimize`.
- Set `APP_KEY` via environment variable (generated with `php artisan key:generate`).
- Use queues (Redis/SQS) for background jobs.

## Environment
- `APP_KEY` — application encryption key.
- `DB_CONNECTION` / `DB_HOST` / `DB_DATABASE` — database config.
- `APP_ENV` — environment (production, local, testing).
- `CACHE_DRIVER` — cache backend (redis, file, memcached).
- `QUEUE_CONNECTION` — queue backend (redis, sqs, database).\
""",
}
