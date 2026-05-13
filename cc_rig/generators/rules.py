"""Generate .claude/rules/*.md path-scoped instruction files (CC v2.1.108+).

CC loads files matching the ``paths`` glob frontmatter when Claude reads
matching files. cc-rig generates a small, opinionated set of rule files
per project based on language/framework/tier. Files outside this set
are user territory and are never overwritten.

Per Gate 2 contract: each candidate file is checked via
``tracker.is_user_authored(rel_path)``. If True, the file is left alone.
Otherwise, cc-rig writes the generated content (with backup of any prior
cc-rig output via FileTracker).
"""
# ruff: noqa: E501  # Rule body strings are markdown content, not code.

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker

# Workflows that get the security.md rule file. Aligned with
# settings.py::_HIGH_RIGOR_WORKFLOWS so the two move together.
_HIGH_RIGOR_WORKFLOWS = frozenset({"rigorous", "superpowers", "verify-heavy", "spec-driven"})

# Frameworks whose conventional layout includes a migrations directory.
_MIGRATION_FRAMEWORKS = frozenset(
    {
        "django",
        "fastapi",
        "flask",
        "rails",
        "laravel",
        "phoenix",
        "spring-boot",
        "spring",
    }
)

# Frameworks that signal frontend code (or where typescript is the language).
_FRONTEND_FRAMEWORKS = frozenset({"nextjs", "express"})

# Test-file glob patterns per language. Mirrors test_dir conventions
# already encoded in templates.
_TEST_GLOBS_BY_LANGUAGE: dict[str, list[str]] = {
    "python": ["tests/**/*.py", "**/*_test.py", "**/test_*.py"],
    "typescript": ["tests/**/*.{ts,tsx}", "**/*.test.{ts,tsx}", "**/__tests__/**/*"],
    "javascript": ["tests/**/*.js", "**/*.test.{js,jsx}", "**/__tests__/**/*"],
    "go": ["**/*_test.go"],
    "rust": ["tests/**/*.rs", "**/src/**/*test*.rs"],
    "ruby": ["test/**/*.rb", "spec/**/*.rb"],
    "java": ["src/test/**/*.{java,kt}"],
    "csharp": ["**/*.Tests/**/*.cs", "**/*Tests.cs"],
    "php": ["tests/**/*.php"],
    "elixir": ["test/**/*.exs"],
}


def generate_rules(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
    prior_manifest: Optional[dict[str, Any]] = None,
) -> list[str]:
    """Generate .claude/rules/*.md based on config detection.

    Returns list of relative file paths written. Files skipped because
    they were user-authored are not in the returned list.

    On rerun: if ``prior_manifest`` is supplied (typically read by the
    orchestrator from ``.claude/.cc-rig-manifest.json``), files we wrote
    in a prior generation are recognized as ours and overwritten safely.
    Files outside the prior manifest are treated as user-authored and
    left alone.
    """
    files_written: list[str] = []
    rules_dir = output_dir / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    candidates: list[tuple[str, str]] = []

    # tests.md: always generate when language is recognized.
    if config.language in _TEST_GLOBS_BY_LANGUAGE:
        candidates.append((".claude/rules/tests.md", _render_tests_rule(config)))

    # migrations.md: framework-driven.
    if config.framework in _MIGRATION_FRAMEWORKS:
        candidates.append((".claude/rules/migrations.md", _render_migrations_rule(config)))

    # security.md: high-rigor tiers only. Eager load (no `paths`).
    if config.workflow in _HIGH_RIGOR_WORKFLOWS:
        candidates.append((".claude/rules/security.md", _render_security_rule(config)))

    # frontend.md: frontend frameworks or TypeScript language.
    if config.framework in _FRONTEND_FRAMEWORKS or config.language == "typescript":
        candidates.append((".claude/rules/frontend.md", _render_frontend_rule(config)))

    for rel_path, content in candidates:
        if tracker is not None:
            if tracker.is_user_authored(rel_path, prior_manifest=prior_manifest):
                continue
            tracker.write_text(rel_path, content)
        else:
            full = output_dir / rel_path
            if full.exists():
                # Conservative: without a tracker we can't tell user from
                # prior generation. Skip rather than overwrite.
                continue
            full.write_text(content)
        files_written.append(rel_path)

    return files_written


# ── Rule rendering ─────────────────────────────────────────────────


def _render_tests_rule(config: ProjectConfig) -> str:
    globs = _TEST_GLOBS_BY_LANGUAGE.get(config.language, [])
    paths_yaml = "\n".join(f'  - "{g}"' for g in globs)
    test_cmd = config.test_cmd or "(see CLAUDE.md)"
    return f"""---
paths:
{paths_yaml}
---

# Test-file rules

When editing tests in this project:

- Run `{test_cmd}` after every change. A test you cannot run is a test you cannot trust.
- One assertion per test where practical. Multiple assertions are fine when they cover the same behavior; avoid bundling unrelated checks.
- Test names describe behavior, not implementation: `test_user_cannot_delete_others_posts`, not `test_delete_function`.
- Prefer real fixtures over mocks for the system under test. Mock only at trust boundaries (network, time, randomness).
- New code paths require new tests. If you cannot easily write one, the design probably needs work.
"""


def _render_migrations_rule(config: ProjectConfig) -> str:
    return """---
paths:
  - "**/migrations/**"
  - "**/migrate/**"
  - "**/db/migrate/**"
  - "**/alembic/**"
  - "**/priv/repo/migrations/**"
---

# Migration rules

Migrations are append-only history. The rules:

- Never edit a migration that has been applied (in any environment). Add a new migration that fixes the issue forward.
- Every migration must be reversible if technically possible. Document an irreversible migration with a comment explaining why.
- Schema changes that lock or rewrite large tables run in their own migration, separate from data backfills, so they can be retried independently.
- Add the migration AND a smoke test (or assertion) that the new schema/data shape exists, in the same change.
"""


def _render_security_rule(config: ProjectConfig) -> str:
    # No `paths`: load eagerly for high-rigor tiers.
    return """# Security rules

This project is configured for high-rigor work. Apply these checks before any change touches authentication, secrets, input handling, or external I/O:

- Validate every input at the boundary. Type checks are not validation; range/length/format/whitelist are.
- Treat all user-supplied strings as hostile. SQL, shell, HTML, regex, and path operations all need explicit escaping or parameterization.
- Never log secrets, tokens, or PII. Redact at the logger, not at the call site.
- Fail closed: on auth/authz uncertainty, deny. On crypto uncertainty, raise rather than guess.
- New external dependencies require a one-line note in the PR body explaining why no existing dependency covers the need.
- If the change touches `auth/`, `security/`, or anything handling secrets, run a /security-review pass before merging.
"""


def _render_frontend_rule(config: ProjectConfig) -> str:
    return """---
paths:
  - "**/*.{tsx,jsx,vue}"
  - "**/pages/**"
  - "**/components/**"
  - "**/app/**/*.{ts,tsx}"
---

# Frontend rules

When editing UI code in this project:

- Components do one thing. If a component renders three unrelated sections with three useEffects, it should be three components.
- State lives at the lowest scope that needs it. Lifting state up is fine; reaching down past one boundary is a smell.
- Side effects (fetch, subscribe, set timer) live in effects or event handlers, never in render.
- Accessibility is part of the change, not a follow-up: every interactive element gets a label, every image gets alt text, every form gets keyboard navigation.
- Loading and error states are required, not optional. Users see them in production even when they don't appear in your dev environment.
"""
