"""Generic (language-agnostic) template content."""

CONTENT: dict = {
    "rules": """\
## Project Rules
- Keep functions small and focused. Each function does one thing and \
does it well.
- Fail fast: validate inputs at system boundaries. Return errors early \
rather than nesting deeply.
- No magic numbers or strings. Use named constants for values that have \
semantic meaning.
- Dependencies flow inward: outer layers depend on inner layers, never \
the reverse. Core logic has zero framework imports.
- Every public function and module has a doc comment explaining its \
purpose, not restating its implementation.
- Side effects (I/O, network, database) are isolated at the edges. \
Core logic is pure and testable without mocks.\
""",
    "architecture": """\
# Architecture

## Directory Layout
```
src/                  # Application source code
  main.*              # Entry point
  core/               # Domain logic (no I/O, no framework imports)
  services/           # Orchestration: coordinates core logic with I/O
  adapters/           # External system integrations (DB, HTTP, files)
  config/             # Configuration loading and validation
tests/                # Test suite (mirrors src/ structure)
  unit/               # Fast, isolated tests for core logic
  integration/        # Tests involving real external systems
docs/                 # Project documentation
scripts/              # Build, deploy, and utility scripts
```

## Key Patterns
- **Ports and Adapters**: core logic defines interfaces (ports); adapters \
implement them for specific technologies.
- **Dependency Injection**: constructors accept interfaces, not concrete \
implementations. Wire dependencies at the entry point.
- **Layered error handling**: core returns typed errors; services map them \
to application-level errors; entry point maps to exit codes or HTTP status.
- **Configuration hierarchy**: defaults → config file → environment \
variables → CLI flags. Each layer overrides the previous.
- **Single Responsibility Modules**: each module/package owns one concept. \
If a module needs a compound name, it is doing too much.
- **Fail-fast validation**: validate all external input at the boundary \
(CLI args, API payloads, file contents) before passing to core logic.\
""",
    "conventions": """\
# Conventions

## Naming
- Files and directories: lowercase with separators appropriate to the \
language (snake_case for Python/Rust, kebab-case for JS/TS, etc.).
- Functions/methods: verb-first (`create_user`, `parse_config`, `validate`).
- Types/classes: PascalCase nouns describing what they represent.
- Constants: UPPER_SNAKE_CASE.
- Boolean variables/functions: `is_*`, `has_*`, `can_*`, `should_*`.

## Code Organization
- One concept per file. If a file exceeds ~300 lines, split it.
- Group by feature/domain, not by type (prefer `users/service.py` over \
`services/user_service.py` when the project is large).
- Keep import sections organized: stdlib, third-party, local — with \
blank lines between groups.

## Error Handling
- Use the language's idiomatic error mechanism (exceptions, Result types, \
error returns).
- Provide context when propagating errors: what operation failed and why.
- Log at the appropriate level: ERROR for failures needing attention, \
WARN for recoverable issues, INFO for operational events, DEBUG for \
development.

## Documentation
- README: what the project does, how to set up, how to run, how to test.
- Code comments explain WHY, not WHAT. The code itself explains WHAT.\
""",
    "testing": """\
# Testing

## Principles
- Tests are first-class code. Apply the same quality standards as \
production code.
- Test behavior, not implementation. Tests should survive refactoring \
that preserves behavior.
- Each test covers one scenario with a clear Arrange → Act → Assert \
structure.
- Fast tests run first. Isolate slow tests (I/O, network, database) \
behind a marker or directory.
- No test interdependence. Each test sets up its own state and cleans \
up after itself. Tests must pass in any order.

## Structure
```
tests/
  unit/               # Fast, no I/O, mock external dependencies
  integration/        # Real databases, file systems, or APIs
  fixtures/           # Shared test data files
  conftest / helpers  # Shared setup, factories, utilities
```

## Practices
- Use factories or builders for test data, not hand-crafted literals \
repeated across tests.
- Mock at the boundary: mock the adapter/port interface, not internal \
functions.
- Aim for high coverage of core logic. Adapters are covered by \
integration tests.
- Run the full suite in CI on every push. Use a fast subset as a \
pre-commit check.
- Snapshot/golden-file tests for complex output (CLI output, generated \
files, API responses).\
""",
    "deployment": """\
# Deployment

## Build
- Automate the build with a single command (`make build`, `npm run build`, \
`cargo build --release`).
- Pin all dependency versions. Use a lockfile.
- Build artifacts are reproducible: same source + same deps = same output.

## Containerization
- Use multi-stage Docker builds: build stage with full toolchain, runtime \
stage with minimal base image.
- Run as a non-root user inside the container.
- Health check endpoint or command for orchestrator liveness probes.

## CI/CD
- Lint, test, and build on every push.
- Deploy to staging on merge to main. Promote to production after \
verification.
- Use environment variables for all environment-specific configuration.
- Secrets managed via a secret manager or CI/CD variables — never in \
the repository.

## Release
- Tag releases with semantic versioning.
- Changelog generated from commit messages or maintained manually.
- Rollback plan: every deploy should be reversible within minutes.\
""",
}
