"""Phoenix (Elixir) framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (Elixir / Phoenix)
- Organize business logic in Contexts (bounded contexts). Each context \
is a public API module that encapsulates a domain area (Accounts, Catalog).
- Use Ecto changesets for all data validation and casting. Never trust \
raw input — validate through changesets before database operations.
- Use the Plug pipeline for cross-cutting concerns: authentication, \
logging, CORS, request ID. Compose plugs in router pipelines.
- LiveView for interactive UI. Use `handle_event` for user interactions, \
`handle_info` for server-push updates. Minimize assigns in socket.
- Pattern match function heads for different cases instead of \
conditional logic. Use guard clauses for type/value checks.
- Use `with` expressions for chaining operations that may fail. \
Return `{:ok, result}` or `{:error, reason}` tuples consistently.
- Never store state in module attributes at runtime. Use GenServer, \
Agent, or ETS for process-level state.\
""",
    "architecture": """\
# Architecture — Elixir / Phoenix

## Directory Layout
```
lib/
  my_app/
    accounts/
      accounts.ex          # Context module (public API)
      user.ex              # Ecto schema
      user_token.ex        # Auth token schema
    catalog/
      catalog.ex           # Context module
      product.ex           # Ecto schema
    repo.ex                # Ecto.Repo configuration
  my_app_web/
    controllers/
      user_controller.ex   # HTTP controllers
      user_json.ex         # JSON rendering
    live/
      dashboard_live.ex    # LiveView modules
    components/
      core_components.ex   # Reusable UI components
    plugs/
      auth.ex              # Authentication plug
    router.ex              # Route definitions + pipelines
    endpoint.ex            # Endpoint configuration
config/
  config.exs               # Base configuration
  dev.exs                  # Development overrides
  prod.exs                 # Production configuration
  runtime.exs              # Runtime config (env vars)
priv/
  repo/migrations/         # Ecto migration files
test/
  my_app/
    accounts_test.exs      # Context tests
  my_app_web/
    controllers/           # Controller tests
    live/                  # LiveView tests
  support/
    fixtures/              # Test fixtures
    conn_case.ex           # Shared test setup
```

## Key Patterns
- **Contexts**: public API for each domain. Controllers call context \
functions, never Repo directly. `Accounts.create_user(attrs)`.
- **Ecto schemas**: define fields, types, validations, and associations. \
Schemas are data structures, not ActiveRecord-style objects.
- **Router pipelines**: `:browser` for HTML, `:api` for JSON. Each \
pipeline applies a chain of plugs.
- **LiveView**: server-rendered interactive UI. Socket assigns drive \
re-renders. Use `assign_async` for expensive loads.
- **PubSub**: use Phoenix.PubSub for real-time broadcasts between \
processes and LiveView instances.
- **Telemetry**: instrument with `:telemetry.execute/3`. Attach \
handlers for logging, metrics, monitoring.\
""",
    "conventions": """\
# Conventions — Elixir / Phoenix

## Naming
- Modules: PascalCase namespaced (`MyApp.Accounts`, `MyAppWeb.UserController`).
- Functions: snake_case (`create_user`, `list_products`).
- Files: snake_case matching module name (`user_controller.ex`).
- Contexts: noun-based (`Accounts`, `Catalog`), not verb-based.

## Context Guidelines
- One context per domain boundary. Keep context modules focused.
- Context functions are the public API — document with @doc.
- Return `{:ok, struct}` or `{:error, changeset}` for mutations.
- Use `Repo.preload` in context functions, not in controllers.

## Controller Guidelines
- One controller per resource. Standard actions: index, show, new, \
create, edit, update, delete.
- Controllers parse params and call context functions. No business logic.
- Use `action_fallback` for consistent error rendering.
- Render JSON with dedicated `*_json.ex` modules.

## Code Style
- Use `mix format` — Elixir's built-in formatter.
- Run `mix credo` for static analysis and style checking.
- Pipe operator (`|>`) for data transformation chains.
- Pattern match in function heads over case statements when possible.
- Use typespecs (`@spec`) on public functions.\
""",
    "testing": """\
# Testing — Elixir / Phoenix

## Stack
- **Framework**: ExUnit (built-in Elixir test framework).
- **HTTP testing**: `ConnTest` for controller tests with `Phoenix.ConnTest`.
- **LiveView**: `LiveViewTest` for interactive UI testing.
- **Database**: Ecto.Adapters.SQL.Sandbox for test isolation.

## Principles
- Test contexts as the primary API boundary. Mock external services, \
not internal modules.
- Use `ConnTest` for full request cycle tests through the router.
- LiveView tests: mount, interact, assert on rendered HTML.
- Ecto Sandbox provides per-test database isolation with automatic \
rollback.

## File Layout
```
test/
  my_app/
    accounts_test.exs       # Context unit tests
    catalog_test.exs         # Context unit tests
  my_app_web/
    controllers/
      user_controller_test.exs  # HTTP endpoint tests
    live/
      dashboard_live_test.exs   # LiveView tests
  support/
    conn_case.ex             # Shared ConnTest setup
    data_case.ex             # Shared DataCase setup
    fixtures/
      accounts_fixtures.ex   # Test data factories
```

## Commands
- `mix test` — run all tests.
- `mix test test/my_app/accounts_test.exs` — run single test file.
- `mix test --trace` — verbose output with test names.
- `mix test --cover` — with coverage report.
- `mix test --stale` — only run tests affected by recent changes.\
""",
    "deployment": """\
# Deployment — Elixir / Phoenix

## Build
- `mix release` produces a self-contained release in `_build/prod/rel/`.
- Releases include the Erlang runtime — no Elixir/Erlang install needed \
on the target server.
- `MIX_ENV=prod mix assets.deploy` for asset compilation.

## Docker
```dockerfile
FROM elixir:1.16-alpine AS builder
ENV MIX_ENV=prod
WORKDIR /app
RUN mix local.hex --force && mix local.rebar --force
COPY mix.exs mix.lock ./
RUN mix deps.get --only prod && mix deps.compile
COPY . .
RUN mix assets.deploy && mix release

FROM alpine:3.19
RUN apk add --no-cache libstdc++ libgcc ncurses
WORKDIR /app
COPY --from=builder /app/_build/prod/rel/my_app ./
EXPOSE 4000
CMD ["bin/my_app", "start"]
```

## Production
- Run migrations: `bin/my_app eval "MyApp.Release.migrate"`.
- Use `runtime.exs` for environment variable configuration.
- Enable clustering with `libcluster` for multi-node deployments.
- Erlang distribution provides built-in node communication.

## Environment
- `DATABASE_URL` — PostgreSQL connection string.
- `SECRET_KEY_BASE` — Phoenix secret key (generate with `mix phx.gen.secret`).
- `PHX_HOST` — production hostname.
- `PORT` — HTTP port (default 4000).
- `MIX_ENV` — environment (prod, dev, test).\
""",
}
