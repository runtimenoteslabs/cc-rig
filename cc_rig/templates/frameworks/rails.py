"""Ruby on Rails framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (Ruby / Rails)
- Follow MVC strictly: fat models, skinny controllers. Business logic \
belongs in models or service objects, never in controllers or views.
- Use ActiveRecord for database access. Prefer scopes and query methods \
over raw SQL. Use `where`, `find_by`, `includes` for queries.
- Always use strong parameters (`params.require(:model).permit(:field)`) \
in controllers. Never trust user input.
- Extract complex business logic into service objects (`app/services/`). \
A service object does one thing and returns a result.
- Use callbacks sparingly. Prefer explicit method calls in service \
objects over `before_save` / `after_create` callbacks.
- Follow Rails conventions for naming: singular models (User), plural \
controllers (UsersController), plural tables (users).
- Use `rails routes` to verify routing. Prefer resourceful routes \
(`resources :users`) over custom routes.\
""",
    "architecture": """\
# Architecture — Ruby / Rails

## Directory Layout
```
app/
  models/
    user.rb             # ActiveRecord model (validations, scopes, associations)
    concerns/           # Shared model mixins
  controllers/
    application_controller.rb
    users_controller.rb  # RESTful actions (index, show, create, update, destroy)
    concerns/           # Shared controller mixins
  views/
    layouts/            # Application layout
    users/              # User view templates
  services/
    user_registration_service.rb  # Complex business logic
  jobs/
    send_email_job.rb   # Background jobs (ActiveJob / Sidekiq)
  mailers/
    user_mailer.rb      # Email templates
config/
  routes.rb             # URL routing (resources, namespaces)
  database.yml          # Database configuration
  application.rb        # Rails application config
db/
  migrate/              # Database migrations
  schema.rb             # Auto-generated schema
  seeds.rb              # Seed data
test/                   # Test directory (Rails default)
  models/
  controllers/
  integration/
  fixtures/
```

## Key Patterns
- **RESTful resources**: `resources :users` generates standard CRUD routes. \
Nest related resources (`resources :users { resources :posts }`).
- **Service objects**: encapsulate multi-step business logic. Return \
result objects, not raise exceptions for expected failures.
- **Concerns**: share behavior across models/controllers via `ActiveSupport::Concern`.
- **Background jobs**: use ActiveJob for async work (emails, imports). \
Back with Sidekiq or GoodJob in production.
- **Migrations**: one migration per schema change. Never edit old \
migrations — create new ones.
- **Config**: environment-specific settings in `config/environments/`. \
Secrets in `credentials.yml.enc`.\
""",
    "conventions": """\
# Conventions — Ruby / Rails

## Naming
- Models: singular PascalCase (`User`, `OrderItem`). Tables: plural \
snake_case (`users`, `order_items`).
- Controllers: plural PascalCase (`UsersController`). Files: snake_case (`users_controller.rb`).
- Routes: plural lowercase (`/users`, `/order_items`).
- Service objects: `VerbNounService` (`CreateUserService`, `ProcessPaymentService`).

## Controller Guidelines
- One resource per controller. Seven standard actions max: index, show, \
new, create, edit, update, destroy.
- Use `before_action` for shared setup (e.g., `set_user`).
- Respond with appropriate status codes: 201 for create, 204 for \
destroy, 422 for validation failure.
- Use `respond_to` for format negotiation (HTML, JSON, CSV).

## Model Guidelines
- Validations at the model level (`validates :email, presence: true`).
- Named scopes for common queries (`scope :active, -> { where(active: true) }`).
- Use `has_many`, `belongs_to`, `has_one` for associations. Always \
specify `dependent:` option.
- Keep models focused. Extract shared behavior into concerns.

## Code Style
- Follow the Ruby Style Guide. Use RuboCop for enforcement.
- Two-space indentation. No trailing whitespace.
- Use `frozen_string_literal: true` comment at the top of every file.
- Prefer `&&`/`||` over `and`/`or`. Use guard clauses for early returns.\
""",
    "testing": """\
# Testing — Ruby / Rails

## Stack
- **Framework**: Minitest (Rails default) or RSpec.
- **Integration**: `ActionDispatch::IntegrationTest` for full request \
cycle testing.
- **Fixtures**: `test/fixtures/` YAML files for test data (or \
`factory_bot` for factories).
- **System tests**: Capybara + Selenium for browser-based tests.

## Principles
- Test through the HTTP layer with integration tests. Validates routing, \
controller logic, and response format together.
- Unit test models for validations, scopes, and business logic.
- Use fixtures for simple data or `factory_bot` for complex scenarios.
- Test both success and failure paths. Verify flash messages and redirects.

## File Layout
```
test/
  models/
    user_test.rb          # Model unit tests
  controllers/
    users_controller_test.rb  # Controller functional tests
  integration/
    user_flows_test.rb    # Full request cycle tests
  system/
    user_signup_test.rb   # Browser-based tests
  fixtures/
    users.yml             # Test data
  test_helper.rb          # Shared setup
```

## Commands
- `bundle exec rails test` — run all tests.
- `bundle exec rails test test/models/` — run model tests.
- `bundle exec rails test:system` — run system tests.
- `bundle exec rails test -n test_should_create_user` — run single test.
- `COVERAGE=true bundle exec rails test` — with coverage.\
""",
    "deployment": """\
# Deployment — Ruby / Rails

## Server
- Use Puma as the application server (Rails default).
- Configure workers and threads in `config/puma.rb` based on available \
CPU cores and memory.
- Set `RAILS_ENV=production` and `RAILS_SERVE_STATIC_FILES=true` for \
asset serving.

## Docker
```dockerfile
FROM ruby:3.3-slim AS builder
WORKDIR /app
COPY Gemfile Gemfile.lock ./
RUN bundle config set --local deployment true && bundle install
COPY . .
RUN bundle exec rails assets:precompile

FROM ruby:3.3-slim
RUN apt-get update && apt-get install -y libpq-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app /app
EXPOSE 3000
CMD ["bundle", "exec", "puma", "-C", "config/puma.rb"]
```

## Production
- Run `rails db:migrate` before deploying new code.
- Use `rails credentials:edit` for secrets. Set `RAILS_MASTER_KEY` in \
the environment.
- Enable caching: `config.cache_store = :redis_cache_store`.
- Set up background job processing (Sidekiq, GoodJob).

## Environment
- `DATABASE_URL` — PostgreSQL connection string.
- `RAILS_ENV` — environment (production, development, test).
- `SECRET_KEY_BASE` — session encryption key.
- `RAILS_MASTER_KEY` — credentials decryption key.
- `REDIS_URL` — Redis connection for caching and jobs.\
""",
}
