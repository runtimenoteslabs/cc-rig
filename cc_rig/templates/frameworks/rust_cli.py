"""Rust CLI (Clap) framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (Rust CLI / Clap)
- Define the CLI interface with Clap's derive macros (`#[derive(Parser)]`). \
Avoid the builder API unless derive cannot express the structure.
- Use `thiserror` for library/domain errors and `anyhow` (or `eyre`) in \
`main()` and top-level orchestration for convenient error propagation.
- Propagate errors with `?` — never use `.unwrap()` or `.expect()` in \
library code. Reserve `.expect("reason")` for cases with a clear invariant.
- Structure as a thin binary (`src/main.rs`) calling into a library \
(`src/lib.rs`). This enables integration testing of the logic without \
spawning a process.
- Use `#[derive(Debug, Clone)]` liberally. Implement `Display` for \
user-facing types.
- Respect the Unix contract: stdout for data, stderr for diagnostics. \
Exit code 0 on success, non-zero on failure.
- Dependencies: keep the dependency tree small. Audit with `cargo audit` \
and `cargo deny`.\
""",
    "architecture": """\
# Architecture — Rust CLI (Clap)

## Directory Layout
```
src/
  main.rs             # Entry point: parse args, call run(), handle errors
  lib.rs              # Re-exports, top-level run() function
  cli.rs              # Clap derive structs (Args, Subcommands)
  commands/
    mod.rs            # Route subcommands to handler functions
    init.rs           # `init` subcommand logic
    build.rs          # `build` subcommand logic
  config/
    mod.rs            # Config loading (file + env + CLI overrides)
  core/
    mod.rs            # Domain types and core logic
  error.rs            # Error types (thiserror enums)
  output.rs           # Formatting: table, JSON, plain text
tests/
  integration/        # Integration tests calling lib functions
    cli_tests.rs      # Full CLI invocations via assert_cmd
```

## Key Patterns
- **Derive-based CLI**: `#[derive(Parser)]` on a top-level `Cli` struct. \
Subcommands as an enum with `#[derive(Subcommand)]`.
- **Error enum**: one `#[derive(thiserror::Error)]` enum per module. \
`main()` uses `anyhow::Result` for top-level orchestration.
- **Config layering**: defaults → config file (TOML/JSON) → env vars → \
CLI flags. Each layer overrides the previous.
- **Builder pattern**: for complex construction (e.g., output formatters), \
use the builder pattern with `Default` impl.
- **Thin main**: `main()` parses args, calls `lib::run(args)`, and maps \
the result to exit codes and error display.
- **Feature flags**: use Cargo features for optional capabilities \
(e.g., `features = ["color"]` gating `colored` output).\
""",
    "conventions": """\
# Conventions — Rust CLI (Clap)

## Naming
- Crate name: kebab-case (`my-tool`). Module names: snake_case.
- Types: PascalCase. Functions/methods: snake_case.
- Error variants: `<Context><Problem>` (`ConfigNotFound`, `ParseFailed`).

## Code Organization
- One public type or function per module when the module is small.
- Use `mod.rs` or `module_name.rs` with a directory — be consistent, \
pick one style for the project.
- Keep `main.rs` under 30 lines. All logic lives in `lib.rs` and modules.

## Error Handling
- `thiserror` for typed errors with context. Each error variant has a \
`#[error("...")]` message suitable for end users.
- Use `anyhow::Context` (`.context("while doing X")`) in `main()` / \
orchestration code for ad-hoc context.
- Map errors to exit codes in a central `match` in `main()`.

## Output
- Structured output: support `--format json|table|plain` via an output \
module.
- Progress indication: use `indicatif` for progress bars on long \
operations.
- Color: use `colored` or `owo-colors`, gated behind `--color auto|always|never`.

## Documentation
- Every public item has a doc comment (`///`).
- `//!` module-level docs on `lib.rs` explaining what the crate does.
- Examples in doc comments that compile (`cargo test` runs them).\
""",
    "testing": """\
# Testing — Rust CLI (Clap)

## Stack
- **Unit tests**: `#[cfg(test)] mod tests` inline in each module.
- **Integration tests**: `tests/` directory, tests the public API.
- **CLI tests**: `assert_cmd` + `predicates` for end-to-end CLI testing.
- **Snapshot tests**: `insta` for output snapshot testing.

## Principles
- Unit tests live next to the code in `#[cfg(test)]` blocks. Test \
internal logic directly.
- Integration tests in `tests/` import only from `lib.rs` — this \
validates the public API surface.
- CLI tests use `assert_cmd::Command` to spawn the binary and assert \
on stdout, stderr, and exit codes.
- Use `tempfile::TempDir` for tests that create files. Never write to \
the real filesystem.

## File Layout
```
src/
  core/
    mod.rs            # Contains #[cfg(test)] mod tests { ... }
tests/
  integration/
    cli_tests.rs      # assert_cmd based CLI tests
    config_tests.rs   # Config loading tests
```

## Commands
- `cargo test` — run all unit + integration tests.
- `cargo test -- --nocapture` — show println output.
- `cargo test -p my-crate` — test specific crate in workspace.
- `cargo insta test` — run and update snapshot tests.
- `cargo tarpaulin` — code coverage.\
""",
    "deployment": """\
# Deployment — Rust CLI

## Build
- `cargo build --release` — optimized binary in `target/release/`.
- Strip symbols: `strip = true` in `[profile.release]` in Cargo.toml.
- LTO: `lto = true` for smaller binaries (slower compile).

## Cross-Compilation
- Use `cross` (`cargo install cross`) for easy cross-compilation.
- Common targets: `x86_64-unknown-linux-musl` (static Linux), \
`aarch64-apple-darwin` (Apple Silicon), `x86_64-pc-windows-msvc`.
- CI matrix: build for all targets in GitHub Actions.

## Distribution
- GitHub Releases: upload prebuilt binaries per platform.
- `cargo install my-tool` — install from crates.io.
- Homebrew tap: formula pointing at GitHub release tarballs.
- Shell installer: `curl -sSf https://... | sh` pattern.

## CI
- `cargo clippy -- -D warnings` — lint with zero warnings.
- `cargo fmt --check` — formatting check.
- `cargo audit` — vulnerability scan on dependencies.
- `cargo deny check` — license and duplicate dependency checks.\
""",
}
