"""Echo (Go) framework template content."""

from cc_rig.templates.frameworks._go_web_base import (
    GO_DEPLOYMENT_BUILD,
    GO_DEPLOYMENT_ENVIRONMENT_BASE,
    GO_DEPLOYMENT_PRODUCTION,
    GO_DOCKER,
    GO_TESTING_COMMANDS,
    GO_TESTING_FILE_LAYOUT,
    GO_TESTING_STACK,
)

CONTENT: dict = {
    "rules": """\
## Framework Rules (Echo / Go)
- Layer as Handler → Service → Repository. Handlers own HTTP concerns; \
services own business logic; repositories own data access.
- Use Echo's middleware chaining: Logger, Recover, CORS, RequestID. \
Register global middleware in `main()`, route-specific in groups.
- Bind and validate request payloads with `c.Bind(&req)` and struct \
tags (`validate:"required"`). Use the `go-playground/validator` integration.
- Return errors from handlers — Echo's `HTTPErrorHandler` centralizes \
error-to-response mapping. Never write the response AND return an error.
- Pass `c.Request().Context()` to service and repository layers. Never \
store `echo.Context` in long-lived structs.
- Use constructor injection for handler dependencies. Wire everything \
in `main()` or a dedicated setup function.
- Wrap errors with `fmt.Errorf("operation: %w", err)` to preserve the \
chain. Use `errors.Is` / `errors.As` for checking.\
""",
    "architecture": """\
# Architecture — Echo (Go)

## Directory Layout
```
cmd/
  server/
    main.go           # Entry point: create Echo, wire deps, start
internal/
  handler/
    user_handler.go   # Route handlers bound to a struct
    routes.go         # Route registration helper
  service/
    user_service.go   # Business logic with interface dependencies
  repository/
    user_repo.go      # Database layer (sqlx / pgx / ent)
  model/
    user.go           # Domain models
  dto/
    request.go        # Request structs with json + validate tags
    response.go       # Response structs
  middleware/
    auth.go           # JWT / session middleware
    logging.go        # Custom structured logging middleware
  config/
    config.go         # Environment-based config struct
pkg/
  apperror/           # Custom error types with HTTP status mapping
migrations/           # SQL migration files
```

## Key Patterns
- **Central error handler**: register `e.HTTPErrorHandler` to map domain \
errors and `echo.HTTPError` to consistent JSON responses.
- **Route groups**: `v1 := e.Group("/api/v1", middleware.Auth())` — \
middleware scoped per group.
- **Dependency injection**: `NewUserHandler(svc service.UserService)` \
returns a struct; handler methods registered on routes.
- **Graceful shutdown**: `e.Start()` in a goroutine, `signal.Notify` + \
`e.Shutdown(ctx)` for clean stop.
- **Structured logging**: `slog` or `zerolog` integrated via custom \
middleware that logs method, path, status, latency.
- **Context values**: use typed keys for request-scoped values \
(user ID, trace ID).\
""",
    "conventions": """\
# Conventions — Echo (Go)

## Naming
- Packages: short, lowercase (`handler`, `service`, `repository`).
- Interfaces: capability-based (`UserCreator`, `OrderFinder`).
- Handler structs: `UserHandler`, `OrderHandler` — one per resource.
- Files: snake_case (`user_handler.go`, `user_service.go`).

## Handler Guidelines
- Handlers receive `echo.Context`, return `error`.
- Parse → validate → delegate to service → return `c.JSON(status, data)`.
- Never embed business logic in handlers.
- Use `echo.NewHTTPError(code, message)` for HTTP-specific errors.

## Error Handling
- Define domain errors in `apperror` package with embedded HTTP status.
- Central `HTTPErrorHandler` inspects error type and renders JSON.
- Log unexpected errors (5xx) at ERROR level; expected errors (4xx) at \
WARN or DEBUG.

## Middleware
- Order matters: Recover first, then Logger, then CORS, then Auth.
- Skip middleware for specific routes via `middleware.Skipper` functions.
- Rate limiting: use `echo-contrib` rate limiter or custom token bucket.

## Testing
- Use `httptest.NewRequest` + `echo.New().NewContext()` for handler tests.
- Interface-based mocking for all cross-layer dependencies.\
""",
    "testing": f"""\
# Testing — Echo (Go)

## Stack
{GO_TESTING_STACK.format(framework="Echo")}

## Principles
- Table-driven tests for all handlers and services.
- Handler tests: `httptest.NewRequest` → `echo.New().NewContext(req, rec)` \
→ inject mock service → call handler → assert on recorder.
- Service tests: mock repository interface, test business rules.
- Integration tests: real database via Testcontainers, test full flow.

{GO_TESTING_FILE_LAYOUT}

{GO_TESTING_COMMANDS}\
""",
    "deployment": f"""\
# Deployment — Echo (Go)

{GO_DEPLOYMENT_BUILD}

{GO_DOCKER}

{GO_DEPLOYMENT_PRODUCTION}

{
        GO_DEPLOYMENT_ENVIRONMENT_BASE.format(
            env_note="Echo runs in release mode by default (no debug flag like Gin)"
        )
    }\
""",
}
