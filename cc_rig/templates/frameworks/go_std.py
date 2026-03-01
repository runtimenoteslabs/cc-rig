"""Go stdlib (net/http) framework template content."""

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
## Framework Rules (Go / stdlib net/http)
- Layer as Handler → Service → Repository. Handlers are plain \
`http.HandlerFunc` functions that parse requests and call services. \
Services contain business logic. Repositories own DB access.
- Use `http.NewServeMux()` for routing (Go 1.22+ enhanced patterns). \
Register routes with `mux.HandleFunc("GET /api/users", handler)`.
- Middleware via function composition: `func middleware(next http.Handler) \
http.Handler`. Chain middleware by wrapping handlers.
- Use `context.Context` for request-scoped values, cancellation, and \
timeouts. Extract context from `r.Context()` and pass downstream.
- Dependency injection via constructor functions. Wire dependencies \
in `main()`. Handlers are methods on structs that hold service references.
- Parse JSON with `json.NewDecoder(r.Body).Decode(&req)`. Write JSON \
with `json.NewEncoder(w).Encode(resp)`. Always set Content-Type header.
- Errors are values. Wrap with `fmt.Errorf("operation: %w", err)` to \
preserve the error chain. Check with `errors.Is` / `errors.As`.\
""",
    "architecture": """\
# Architecture — Go stdlib (net/http)

## Directory Layout
```
cmd/
  server/
    main.go           # Entry point: wiring, server start, graceful shutdown
internal/
  handler/
    user_handler.go   # HTTP handlers (HandlerFunc methods on struct)
    middleware.go      # Auth, logging, CORS middleware functions
    routes.go         # Route registration on ServeMux
  service/
    user_service.go   # Business logic
  repository/
    user_repo.go      # Database access (database/sql, sqlx, pgx)
  model/
    user.go           # Domain types
  dto/
    user_dto.go       # Request/response structs with JSON tags
  config/
    config.go         # Environment-based config struct
pkg/
  httputil/           # Response helpers, error rendering
  errutil/            # Custom error types with HTTP status
migrations/           # SQL migration files (golang-migrate)
```

## Key Patterns
- **No framework**: stdlib `net/http` with Go 1.22+ enhanced ServeMux \
patterns (`GET /api/users/{id}`).
- **Constructor injection**: `NewUserHandler(svc UserService)` — each \
handler struct receives dependencies as interfaces.
- **Middleware chaining**: `func Chain(h http.Handler, mws ...Middleware) \
http.Handler` — compose middleware in a stack.
- **Graceful shutdown**: `signal.NotifyContext` + `srv.Shutdown(ctx)` \
in `main.go`. Close DB connections in deferred cleanup.
- **Config**: single `Config` struct populated from environment variables. \
No config reads after startup.
- **Structured logging**: `slog` (stdlib Go 1.21+). Attach request ID \
and user context via middleware.\
""",
    "conventions": """\
# Conventions — Go stdlib (net/http)

## Naming
- Packages: short, lowercase, no underscores (`handler`, `service`, `repo`).
- Interfaces: verb-based (`UserReader`, `OrderCreator`), not `IUser`.
- Exported types: PascalCase. Unexported helpers: camelCase.
- Test files: `*_test.go` in the same package.

## Handler Guidelines
- One handler file per resource (`user_handler.go`, `order_handler.go`).
- Handlers are methods on a struct: `type UserHandler struct { svc UserService }`.
- Parse input → validate → call service → write response. No business \
logic in handlers.
- Use `http.Error(w, msg, code)` for error responses or a custom \
error writer for consistent JSON errors.

## Middleware Guidelines
- Signature: `func(next http.Handler) http.Handler`.
- Common middleware: logging, panic recovery, CORS, request ID, auth.
- Order: recovery → logging → CORS → auth → handler.

## Error Handling
- Define sentinel errors in `errutil` (`ErrNotFound`, `ErrConflict`).
- Services return `error`; handlers map to HTTP status via a helper.
- Panic recovery middleware returns 500 with a generic message.

## Testing
- Table-driven tests with `t.Run` sub-tests for all handlers and \
service functions.
- Use `httptest.NewServer()` or `httptest.NewRecorder()` for handler tests.
- Interfaces for all cross-layer dependencies to enable mocking.

## Concurrency
- Never share `http.ResponseWriter` across goroutines.
- Use `errgroup.Group` for parallel service calls with proper error \
propagation.\
""",
    "testing": f"""\
# Testing — Go stdlib (net/http)

## Stack
{GO_TESTING_STACK.format(framework="net/http")}

## Principles
- Table-driven tests are the default pattern. Each test case is a struct \
with input, expected output, and description.
- Handler tests: create a `httptest.NewRecorder`, build an `http.Request`, \
inject mock services, call the handler, assert response code + body.
- Service tests: inject mock repositories, test business logic in isolation.
- Repository tests: run against a real database (Testcontainers) or \
use SQLite for speed.

{GO_TESTING_FILE_LAYOUT}

{GO_TESTING_COMMANDS}\
""",
    "deployment": f"""\
# Deployment — Go stdlib (net/http)

{GO_DEPLOYMENT_BUILD}

{GO_DOCKER}

{GO_DEPLOYMENT_PRODUCTION}

{
        GO_DEPLOYMENT_ENVIRONMENT_BASE.format(
            env_note="No framework mode flags — stdlib server is always production-ready"
        )
    }\
""",
}
