"""Rust Web (Axum) framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (Rust / Axum)
- Build the HTTP layer with Axum extractors (`Path`, `Query`, `Json`, \
`State`) as handler function arguments. Let the type system drive \
request parsing.
- Implement `IntoResponse` for domain types and error enums so handlers \
return `Result<impl IntoResponse, AppError>`. Never call `.unwrap()` in \
handlers.
- Use `tower` middleware (layers) for cross-cutting concerns: tracing, \
CORS, compression, timeouts, rate limiting. Compose with \
`ServiceBuilder`.
- Share application state via `Extension` or `State<Arc<AppState>>`. \
Never use global mutable statics.
- Serialize/deserialize with `serde`. Derive `Serialize`, `Deserialize` \
on all request/response types.
- Use `thiserror` for domain errors and map them to HTTP status codes in \
a centralized `IntoResponse` impl.
- Propagate errors with `?` — never `.unwrap()` or `.expect()` in \
library code.\
""",
    "architecture": """\
# Architecture — Rust / Axum

## Directory Layout
```
src/
  main.rs             # Entry point: tokio::main, build Router, serve
  lib.rs              # Re-exports, AppState, shared types
  routes/
    mod.rs            # Route tree construction (Router::new().merge(...))
    users.rs          # /api/users routes
    health.rs         # /health endpoint
  handlers/
    mod.rs            # Handler functions grouped by resource
    users.rs          # User CRUD handlers
  models/
    mod.rs            # Domain types, DB models (sqlx/diesel)
    user.rs           # User model + queries
  db/
    mod.rs            # Connection pool setup (sqlx::PgPool)
    migrations/       # SQL migrations (sqlx-cli or refinery)
  error.rs            # AppError enum + IntoResponse impl
  middleware/
    mod.rs            # Custom tower layers (auth, logging)
  config.rs           # Config struct from environment
tests/
  api/                # Integration tests against the running app
    users_test.rs     # User endpoint tests
  common/
    mod.rs            # Shared test helpers, fixtures
```

## Key Patterns
- **Router composition**: each module returns a `Router`, composed in \
`routes/mod.rs` via `.merge()` or `.nest()`.
- **Extractor-driven**: handlers declare what they need as function \
parameters. Axum extracts and validates automatically.
- **AppState**: `Arc<AppState>` holds DB pool, config, and shared \
services. Passed via `State` extractor.
- **Error handling**: `AppError` enum with `IntoResponse` impl maps \
domain errors to HTTP responses with proper status codes.
- **Graceful shutdown**: `tokio::signal` + `axum::serve(...).with_graceful_shutdown(...)`.
- **Structured logging**: `tracing` + `tracing-subscriber` with \
`tower-http::trace::TraceLayer` for request spans.\
""",
    "conventions": """\
# Conventions — Rust / Axum

## Naming
- Crate name: kebab-case (`my-api`). Module names: snake_case.
- Types: PascalCase (`CreateUserRequest`). Functions: snake_case.
- Route handlers: verb-based (`get_user`, `create_user`, `delete_user`).
- Error variants: `<Context><Problem>` (`DatabaseError`, `NotFound`).

## Code Organization
- One module per resource in `routes/` and `handlers/`.
- Keep handlers thin: parse request → call service → return response.
- Business logic lives in service functions or model methods, not handlers.
- Use `mod.rs` for directory modules. Be consistent across the project.

## Extractors
- `Json<T>` for request bodies, `Path<T>` for URL params, `Query<T>` \
for query strings.
- Custom extractors implement `FromRequestParts` or `FromRequest`.
- Order matters: body-consuming extractors (`Json`, `Form`) must be last.

## Error Handling
- Define `AppError` with `thiserror`. Implement `IntoResponse` to map \
each variant to an HTTP status + JSON body.
- Use `?` throughout — let errors bubble up to the handler boundary.
- Log errors with `tracing::error!` in the `IntoResponse` impl.

## Logging
- Use `tracing` (not `log`). Instrument async functions with \
`#[tracing::instrument]`.
- Set levels via `RUST_LOG` env var (e.g., `RUST_LOG=my_api=debug,tower_http=info`).\
""",
    "testing": """\
# Testing — Rust / Axum

## Stack
- **Unit tests**: `#[cfg(test)] mod tests` inline in each module.
- **Integration tests**: `tests/` directory, test against the full router.
- **HTTP tests**: `tower::ServiceExt::oneshot` to send requests without \
spawning a server.
- **Database tests**: `sqlx::test` for transactional test isolation.

## Principles
- Integration tests build the full `Router` with test state (in-memory \
DB or test database), then use `oneshot` to send requests.
- Use `serde_json::json!` to build request bodies.
- Assert on status codes, response bodies, and headers.
- Database tests use `#[sqlx::test]` for automatic migration + rollback.

## File Layout
```
tests/
  api/
    users_test.rs     # /api/users endpoint tests
    health_test.rs    # Health check tests
  common/
    mod.rs            # Test app builder, helpers
```

## Commands
- `cargo test` — run all unit + integration tests.
- `cargo test -- --nocapture` — show println/tracing output.
- `cargo test api::` — run only API integration tests.
- `cargo nextest run` — parallel test runner (faster).
- `cargo tarpaulin` — code coverage.\
""",
    "deployment": """\
# Deployment — Rust / Axum

## Build
- `cargo build --release` — optimized binary in `target/release/`.
- Strip symbols: `strip = true` in `[profile.release]` for smaller binaries.
- LTO: `lto = true` for maximum optimization (slower compile).

## Docker
```dockerfile
FROM rust:1.78-slim AS builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/my-api /usr/local/bin/
EXPOSE 3000
CMD ["my-api"]
```

## Production
- Set `RUST_LOG=info` (or `warn` for quieter output).
- Configure connection pool size via environment variables.
- Use health check endpoint for load balancer probes.
- Run database migrations on startup or as a separate init step.

## Environment
- `DATABASE_URL` — PostgreSQL connection string.
- `RUST_LOG` — tracing filter directive.
- `HOST` / `PORT` — bind address (default `0.0.0.0:3000`).
- `RUST_BACKTRACE=1` — enable backtraces in error output.\
""",
}
