"""Gin (Go) framework template content."""

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
## Framework Rules (Gin / Go)
- Layer as Handler → Service → Repository. Handlers parse requests and \
call services. Services contain business logic. Repositories own DB access.
- Use Gin's middleware chain for cross-cutting concerns: logging, auth, \
CORS, request ID, panic recovery.
- Return structured JSON errors via `c.JSON(statusCode, gin.H{"error": msg})`. \
Never call `c.Abort()` without setting a response body.
- Context propagation: pass `c.Request.Context()` to service/repo layers \
for cancellation and tracing. Never store `*gin.Context` in structs.
- Dependency injection via constructor functions, not global variables. \
Wire dependencies in `main()` or a `wire.go` setup.
- Use struct tags for binding and validation: `binding:"required"`, \
`json:"field_name"`. Let Gin's `ShouldBindJSON` handle validation.
- Errors are values. Wrap with `fmt.Errorf("operation: %w", err)` to \
preserve the error chain. Check with `errors.Is` / `errors.As`.\
""",
    "architecture": """\
# Architecture — Gin (Go)

## Directory Layout
```
cmd/
  server/
    main.go           # Entry point: wiring, server start
internal/
  handler/
    user_handler.go   # HTTP handlers (parse request, call service)
    middleware.go      # Auth, logging, CORS middleware
  service/
    user_service.go   # Business logic
  repository/
    user_repo.go      # Database access (sqlx / pgx / GORM)
  model/
    user.go           # Domain types / DB models
  dto/
    user_dto.go       # Request/response structs with JSON + binding tags
  config/
    config.go         # Viper or env-based config struct
pkg/
  errutil/            # Shared error types, sentinel errors
  httputil/           # Response helpers, pagination
migrations/           # SQL migration files (golang-migrate)
```

## Key Patterns
- **Constructor injection**: `NewUserHandler(svc UserService)` — each \
layer receives its dependencies as interfaces.
- **Interface-driven**: services accept repository interfaces, enabling \
mock-based testing without a real database.
- **Router groups**: `v1 := r.Group("/api/v1")` with middleware applied \
per group.
- **Graceful shutdown**: `signal.NotifyContext` + `srv.Shutdown(ctx)` in \
`main.go`.
- **Config**: single `Config` struct loaded from environment variables \
at startup. No config reads inside handlers.
- **Structured logging**: `slog` (stdlib) or `zerolog`. Attach request \
ID via middleware.\
""",
    "conventions": """\
# Conventions — Gin (Go)

## Naming
- Packages: short, lowercase, no underscores (`handler`, `service`, `repo`).
- Interfaces: verb-based (`UserReader`, `OrderCreator`), not `IUser`.
- Exported types: PascalCase. Unexported helpers: camelCase.
- Test files: `*_test.go` in the same package.

## Handler Guidelines
- One handler file per resource (`user_handler.go`, `order_handler.go`).
- Handler methods on a struct: `type UserHandler struct { svc UserService }`.
- Parse input → validate → call service → write response. No business \
logic in handlers.

## Error Handling
- Define sentinel errors in `errutil` (`ErrNotFound`, `ErrConflict`).
- Services return `error`; handlers map to HTTP status via a helper \
or switch.
- Middleware-level panic recovery returns 500 with a generic message.

## Testing
- Table-driven tests with `t.Run` sub-tests for all handler and \
service functions.
- Use `httptest.NewRecorder()` + `gin.CreateTestContext()` for handler \
tests.
- Interfaces for all cross-layer dependencies to enable mocking.

## Concurrency
- Never share `*gin.Context` across goroutines. Copy needed values first.
- Use `errgroup.Group` for parallel service calls with proper error \
propagation.\
""",
    "testing": f"""\
# Testing — Gin (Go)

## Stack
{GO_TESTING_STACK.format(framework="Gin")}

## Principles
- Table-driven tests are the default pattern. Each test case is a struct \
with input, expected output, and description.
- Handler tests: create a `httptest.NewRecorder`, build a `*gin.Context`, \
inject mock services, call the handler, assert response code + body.
- Service tests: inject mock repositories, test business logic in isolation.
- Repository tests: run against a real database (Testcontainers) or \
use SQLite for speed.

{GO_TESTING_FILE_LAYOUT}

{GO_TESTING_COMMANDS}\
""",
    "deployment": f"""\
# Deployment — Gin (Go)

{GO_DEPLOYMENT_BUILD}

{GO_DOCKER}

{GO_DEPLOYMENT_PRODUCTION}

{
        GO_DEPLOYMENT_ENVIRONMENT_BASE.format(
            env_note="`GIN_MODE=release` in production (disables debug logging)"
        )
    }\
""",
}
