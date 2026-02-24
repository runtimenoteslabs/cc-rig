"""Shared content for Go web framework templates (Gin, Echo)."""

GO_TESTING_STACK = """\
- **Framework**: `testing` stdlib + `testify/assert` for assertions.
- **HTTP testing**: `net/http/httptest` + {framework} test context.
- **Mocking**: `testify/mock` or `gomock` for interface mocks.
- **Integration**: `testcontainers-go` for database tests."""

GO_TESTING_FILE_LAYOUT = """\
## File Layout
```
internal/
  handler/
    user_handler.go
    user_handler_test.go    # Handler tests with mock service
  service/
    user_service.go
    user_service_test.go    # Service tests with mock repo
  repository/
    user_repo.go
    user_repo_test.go       # Integration tests with real DB
```"""

GO_TESTING_COMMANDS = """\
## Commands
- `go test ./...` — run all tests.
- `go test -v ./internal/handler/` — verbose, single package.
- `go test -race ./...` — race condition detection.
- `go test -cover -coverprofile=coverage.out ./...` — coverage report."""

GO_DEPLOYMENT_BUILD = """\
## Build
- `go build -o server ./cmd/server` — single static binary.
- `CGO_ENABLED=0` for fully static builds (no libc dependency).
- Use `-ldflags "-s -w"` to strip debug symbols for smaller binaries."""

GO_DOCKER = """\
## Docker
```dockerfile
FROM golang:1.22 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /server ./cmd/server

FROM gcr.io/distroless/static-debian12
COPY --from=build /server /server
CMD ["/server"]
```"""

GO_DEPLOYMENT_PRODUCTION = """\
## Production
- Single binary deployment — no runtime dependencies.
- Health check: `GET /healthz` returning 200.
- Graceful shutdown via `SIGTERM` handling in `main.go`.
- Run behind a reverse proxy (nginx/Caddy/cloud LB) for TLS."""

GO_DEPLOYMENT_ENVIRONMENT_BASE = """\
## Environment
- All config via environment variables loaded at startup.
- {env_note}
- Secrets injected via orchestrator or secret manager."""
