# Changelog

All notable changes to cc-rig will be documented in this file.

## [1.0.0] - 2026-02-22

### Added

**Core**
- Two-axis architecture: Config Experience (A0-A3) x Runtime Discipline (B0-B3)
- 7 framework templates: FastAPI, Django, Flask, Next.js, Gin, Echo, Rust CLI
- 5 workflow presets: speedrun, standard, spec-driven, gtd-lite, verify-heavy
- Smart defaults engine: template + workflow compose independently (35 valid combos)
- ProjectConfig dataclass with full serialization round-trip

**Generators**
- CLAUDE.md generator with cache-aware static-first ordering (~55 lines)
- settings.json with hook schema (command + prompt types)
- Up to 12 agent definitions with role-specific prompts and tool restrictions
- Up to 16 slash commands with YAML frontmatter
- 4 bundled skills (TDD, systematic-debug, project-patterns, deployment-checklist)
- 4 agent docs (architecture, conventions, testing, deployment) — framework-specific
- 5-file memory system with anti-ballooning rules
- MCP server configuration
- Hook shell scripts (format, lint, typecheck, safety guards)
- Post-generation validator with 19 checks

**CLI & Wizard**
- `cc-rig init` with 6 flow paths: zero-config, guided, quick, expert, config-load, migrate
- `cc-rig preset list` to browse templates and workflows
- Interactive wizard with testable IO (injectable input/output)
- Project detection for `--migrate` (pyproject.toml, package.json, go.mod, Cargo.toml, etc.)

**Config Management**
- `cc-rig config save/load/list/inspect/diff/lock/unlock`
- Personal configs in `~/.cc-rig/configs/`
- Team configs in `.cc-rig.json` (committable)
- Portable export strips machine-specific paths
- Locked configs prevent modification via wizard

**Doctor & Clean**
- `cc-rig doctor` with 10+ health checks (files, hooks, memory, manifest, staleness)
- `cc-rig doctor --fix` for safe auto-remediation (permissions, missing memory files)
- `cc-rig clean` manifest-based removal (only deletes generated files)
- Empty directory cleanup after clean

**Runtime Harness**
- `cc-rig harness init --lite` (B1): task tracking + budget awareness
- `cc-rig harness init` (B2): + verification gates + review notes
- `cc-rig harness init --autonomy` (B3): autonomous loop with safety rails
- Safety config: max iterations, checkpoint commits, blocked-state handling
- `--ralph` hidden alias preserved

**Infrastructure**
- Zero runtime dependencies (Python stdlib only)
- pytest test suite (685 tests)
- ruff linting and formatting
- GitHub Actions CI (Python 3.9-3.12)
- MIT license
