"""Generate .claude/skills/ — download community skills + bundled fallbacks."""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.project import ProjectConfig
from cc_rig.generators.fileops import FileTracker
from cc_rig.skills.downloader import SkillInstallReport, download_skills
from cc_rig.skills.registry import resolve_skills


def generate_skills(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Generate skill files in .claude/skills/.

    Downloads community skills from the curated registry, with offline
    fallbacks for tdd/debug. Always generates the project-patterns stub.

    Returns list of relative file paths written.
    """
    files_written: list[str] = []

    # Resolve which skills to install
    specs = resolve_skills(
        config.template_preset or config.framework or "",
        config.workflow or "standard",
        config.default_mcps,
        packs=config.skill_packs,
    )

    # Attempt to download community skills
    report = _download_community_skills(specs, output_dir, tracker)
    files_written.extend(report.all_files)

    # Speedrun bundled_only: generate thin tdd/debug instead of downloading
    if config.workflow == "speedrun":
        files_written.extend(_write_tdd_fallback(config, output_dir, tracker))
        files_written.extend(_write_debug_fallback(config, output_dir, tracker))
    else:
        # Offline fallback: if tdd/debug download failed and workflow needs them
        if "test-driven-development" in report.failed_names:
            files_written.extend(_write_tdd_fallback(config, output_dir, tracker))
        if "systematic-debugging" in report.failed_names:
            files_written.extend(_write_debug_fallback(config, output_dir, tracker))

    # Always generate project-patterns stub
    files_written.extend(_write_project_patterns_stub(config, output_dir, tracker))

    return files_written


def _download_community_skills(
    specs: list,
    output_dir: Path,
    tracker: FileTracker | None,
) -> SkillInstallReport:
    """Download skills, returning a report. Never raises."""
    try:
        return download_skills(specs, output_dir, tracker=tracker)
    except Exception:
        # Total download failure — return empty report
        report = SkillInstallReport()
        object.__setattr__(report, "_files", [])
        for spec in specs:
            report.failed.append((spec.name, "download system failure"))
        return report


# ── Bundled fallback: TDD ──────────────────────────────────────────────


def _write_tdd_fallback(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Write thin bundled TDD skill (offline fallback or speedrun)."""
    skills_dir = output_dir / ".claude" / "skills" / "tdd"
    skills_dir.mkdir(parents=True, exist_ok=True)

    test_cmd = config.test_cmd or "echo 'run tests'"
    lang = config.language or "the project language"
    framework = config.framework or "the project framework"

    test_guidance = _tdd_guidance_for(framework)

    content = (
        "---\n"
        "name: tdd\n"
        f"description: Test-Driven Development workflow for {framework}\n"
        "---\n"
        "\n"
        "# TDD Skill\n"
        "\n"
        "Test-Driven Development workflow customized for "
        f"{framework} ({lang}).\n"
        "\n"
        "## Cycle\n"
        "\n"
        "1. **Red**: Write a failing test that defines the "
        "desired behavior.\n"
        f"   Run: `{test_cmd}` — confirm it fails.\n"
        "2. **Green**: Write the minimal code to make the test "
        "pass.\n"
        f"   Run: `{test_cmd}` — confirm it passes.\n"
        "3. **Refactor**: Clean up the code without changing "
        "behavior.\n"
        f"   Run: `{test_cmd}` — confirm it still passes.\n"
        "4. **Commit**: One focused commit per red-green-refactor "
        "cycle.\n"
        "\n"
        "## Rules\n"
        "\n"
        "- Never write production code without a failing test.\n"
        "- Each test should test one behavior.\n"
        "- Test names describe the expected behavior, not the "
        "method name.\n"
        "- Keep tests fast. Mock external services and databases "
        "in unit tests.\n"
        "\n"
        f"## {framework} Testing Patterns\n"
        "\n"
        f"{test_guidance}\n"
    )

    rel = ".claude/skills/tdd/SKILL.md"
    if tracker is not None:
        tracker.write_text(rel, content)
    else:
        path = skills_dir / "SKILL.md"
        path.write_text(content)
    return [rel]


def _tdd_guidance_for(framework: str) -> str:
    """Return framework-specific TDD guidance."""
    guides: dict[str, str] = {
        "fastapi": (
            "- Use `TestClient` from `starlette.testclient` for "
            "endpoint tests.\n"
            "- Use `pytest.fixture` for database sessions and "
            "test data.\n"
            "- Test request validation by sending invalid "
            "payloads.\n"
            "- Test error responses match the expected status "
            "codes and schemas.\n"
            "- Use `httpx.AsyncClient` for async endpoint tests."
        ),
        "django": (
            "- Use `django.test.TestCase` for database tests "
            "(auto transaction rollback).\n"
            "- Use `Client` for view/endpoint tests.\n"
            "- Test models, views, and forms separately.\n"
            "- Use `factory_boy` or fixtures for test data.\n"
            "- Test both authenticated and unauthenticated "
            "access."
        ),
        "nextjs": (
            "- Use Jest or Vitest for unit tests.\n"
            "- Use React Testing Library for component tests.\n"
            "- Test user interactions, not implementation "
            "details.\n"
            "- Use `getByRole`, `getByText` over `getByTestId`.\n"
            "- Test Server Components with async rendering "
            "patterns."
        ),
        "gin": (
            "- Use `httptest.NewRecorder()` for handler tests.\n"
            "- Write table-driven tests with `t.Run()` "
            "subtests.\n"
            "- Use interfaces for dependency injection in "
            "services.\n"
            "- Test middleware independently from handlers.\n"
            "- Use `testify/assert` or stdlib `testing` "
            "assertions."
        ),
        "echo": (
            "- Use `httptest.NewRecorder()` for handler tests.\n"
            "- Write table-driven tests with `t.Run()` "
            "subtests.\n"
            "- Use interfaces for dependency injection in "
            "services.\n"
            "- Test middleware independently from handlers.\n"
            "- Use `echo.New()` test context for handler unit "
            "tests."
        ),
        "clap": (
            "- Use `#[test]` for unit tests in `src/`.\n"
            "- Use `assert_cmd` crate for CLI integration "
            "tests.\n"
            "- Test both stdout output and exit codes.\n"
            "- Use `tempfile` for tests that need filesystem "
            "state.\n"
            "- Test error messages match expected format."
        ),
        "flask": (
            "- Use `app.test_client()` for endpoint tests.\n"
            "- Use `pytest.fixture` with application factory "
            "pattern.\n"
            "- Test request validation and error responses.\n"
            "- Use `flask.testing.FlaskClient` for session "
            "handling.\n"
            "- Isolate database tests with transactions or "
            "test databases."
        ),
        "axum": (
            "- Use `#[tokio::test]` for async test functions.\n"
            "- Use `tower::ServiceExt::oneshot` to test handlers "
            "without spawning a server.\n"
            "- Use `#[sqlx::test]` for transactional database "
            "test isolation.\n"
            "- Build test requests with `axum::http::Request::builder()`.\n"
            "- Assert on response status codes and "
            "`serde_json`-deserialized bodies."
        ),
        "rails": (
            "- Use `ActiveSupport::TestCase` for model unit "
            "tests.\n"
            "- Use `ActionDispatch::IntegrationTest` for full "
            "request cycle tests.\n"
            "- Use fixtures (YAML) or `factory_bot` for test "
            "data.\n"
            "- Test validations, scopes, and associations in "
            "model tests.\n"
            "- Verify redirects, flash messages, and response "
            "codes in controller tests."
        ),
    }
    return guides.get(
        framework,
        (
            "- Follow the project's established test patterns.\n"
            "- Keep unit tests isolated from external services.\n"
            "- Use descriptive test names.\n"
            "- Test edge cases and error paths."
        ),
    )


# ── Bundled fallback: Systematic Debug ─────────────────────────────────


def _write_debug_fallback(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    """Write thin bundled debug skill (offline fallback or speedrun)."""
    skills_dir = output_dir / ".claude" / "skills" / "systematic-debug"
    skills_dir.mkdir(parents=True, exist_ok=True)

    test_cmd = config.test_cmd or "echo 'run tests'"
    lang = config.language or "the project language"
    framework = config.framework or "the project framework"

    debug_guidance = _debug_guidance_for(framework)

    content = (
        "---\n"
        "name: systematic-debug\n"
        f"description: Structured debugging workflow for {framework}\n"
        "---\n"
        "\n"
        "# Systematic Debug Skill\n"
        "\n"
        "Structured debugging workflow for "
        f"{framework} ({lang}).\n"
        "\n"
        "## Process\n"
        "\n"
        "1. **Reproduce**: Create a reliable reproduction of "
        "the bug.\n"
        f"   Run: `{test_cmd}` to confirm the failure.\n"
        "2. **Isolate**: Narrow down the scope.\n"
        "   - Binary search through recent commits if needed "
        "(`git bisect`).\n"
        "   - Add logging to trace execution flow.\n"
        "   - Eliminate variables: does it reproduce with "
        "minimal input?\n"
        "3. **Identify**: Find the exact line(s) causing the "
        "issue.\n"
        "   - Read the code path from entry to failure.\n"
        "   - Check assumptions at each step.\n"
        "4. **Fix**: Apply the minimal correction.\n"
        "5. **Verify**: Run the reproduction test. Run the "
        "full suite.\n"
        "6. **Prevent**: Add a regression test. Update "
        "memory/gotchas.md if applicable.\n"
        "\n"
        "## Rules\n"
        "\n"
        "- Never guess. Form a hypothesis, then test it.\n"
        "- Change one thing at a time.\n"
        "- If a fix feels like a hack, you have not found the "
        "root cause.\n"
        "- Document what you tried and what you learned.\n"
        "\n"
        f"## {framework} Debugging Tips\n"
        "\n"
        f"{debug_guidance}\n"
    )

    rel = ".claude/skills/systematic-debug/SKILL.md"
    if tracker is not None:
        tracker.write_text(rel, content)
    else:
        path = skills_dir / "SKILL.md"
        path.write_text(content)
    return [rel]


def _debug_guidance_for(framework: str) -> str:
    """Return framework-specific debugging guidance."""
    guides: dict[str, str] = {
        "fastapi": (
            "- Check request/response schemas match with "
            "`print(response.json())`.\n"
            "- Use `--log-level debug` for uvicorn.\n"
            "- Check dependency injection order (Depends chain).\n"
            "- Async bugs: check for missing `await` or "
            "blocking calls in async endpoints.\n"
            "- Database: check session lifecycle and connection "
            "pool exhaustion."
        ),
        "django": (
            "- Use `django-debug-toolbar` for request "
            "profiling.\n"
            "- Check ORM queries with `queryset.query` "
            "or `django.db.connection.queries`.\n"
            "- Middleware ordering matters — check `MIDDLEWARE` "
            "list.\n"
            "- Template errors: check context variables passed "
            "to render.\n"
            "- Migration issues: check `showmigrations` for "
            "gaps."
        ),
        "nextjs": (
            "- Server vs client: check if the error is in RSC "
            "or client component.\n"
            "- Use React DevTools for component state "
            "inspection.\n"
            "- Check `next.config.js` for misconfigurations.\n"
            "- Hydration errors: compare server-rendered vs "
            "client-rendered HTML.\n"
            "- API route errors: check the Network tab for "
            "response payloads."
        ),
        "gin": (
            "- Use `gin.DebugMode()` for verbose route "
            "logging.\n"
            "- Check middleware chain with "
            "`c.Next()` / `c.Abort()` flow.\n"
            "- Use `go vet` and `golangci-lint` for static "
            "analysis.\n"
            "- Concurrency bugs: check for shared state "
            "without mutexes.\n"
            "- Use `pprof` for performance-related issues."
        ),
        "echo": (
            "- Use `echo.Debug` mode for verbose logging.\n"
            "- Check middleware chain ordering.\n"
            "- Use `go vet` and `golangci-lint` for static "
            "analysis.\n"
            "- Check context handling (`echo.Context` vs "
            "`context.Context`).\n"
            "- Use `pprof` for performance-related issues."
        ),
        "clap": (
            "- Use `RUST_BACKTRACE=1` for full stack traces.\n"
            "- Use `dbg!()` macro for quick value inspection.\n"
            "- Check ownership and borrow issues with "
            "`cargo check`.\n"
            "- Use `RUST_LOG=debug` with `env_logger` for "
            "log-level control.\n"
            "- Lifetime errors: simplify the type signatures "
            "first."
        ),
        "flask": (
            "- Use `app.run(debug=True)` for auto-reload and "
            "debugger.\n"
            "- Check Blueprint registration order.\n"
            "- Use `flask shell` for interactive debugging.\n"
            "- SQLAlchemy: check session state and "
            "`db.session.rollback()` on errors.\n"
            "- Check `app.url_map` for route conflicts."
        ),
        "axum": (
            "- Use `RUST_BACKTRACE=1` for full stack traces.\n"
            "- Use `tracing` with `RUST_LOG=debug` for detailed "
            "request logging.\n"
            "- Check extractor failures — Axum returns 400/422 "
            "when extractors fail to parse.\n"
            "- Use `dbg!()` macro for quick value inspection.\n"
            "- Check `tower` layer ordering — middleware runs "
            "in the order layers are added."
        ),
        "rails": (
            "- Use `rails console` for interactive debugging "
            "and data inspection.\n"
            "- Use `debug` gem (Ruby 3.1+) or `byebug` for "
            "breakpoint debugging.\n"
            "- Run `rails routes` to verify URL routing.\n"
            "- Enable ActiveRecord query logging with "
            "`ActiveRecord::Base.logger = Logger.new(STDOUT)`.\n"
            "- Check `rails db:migrate:status` for pending "
            "migrations."
        ),
    }
    return guides.get(
        framework,
        (
            "- Use the language's standard debugging tools.\n"
            "- Add logging at key decision points.\n"
            "- Check recent git changes with `git log --oneline`.\n"
            "- Verify assumptions about input data."
        ),
    )


# ── Project Patterns (always generated) ────────────────────────────────


def _write_project_patterns_stub(
    config: ProjectConfig,
    output_dir: Path,
    tracker: FileTracker | None = None,
) -> list[str]:
    skills_dir = output_dir / ".claude" / "skills" / "project-patterns"
    skills_dir.mkdir(parents=True, exist_ok=True)

    content = (
        "# Project Patterns Skill\n"
        "\n"
        "Project-specific conventions, architecture decisions, "
        "and naming rules.\n"
        "\n"
        "## Instructions\n"
        "\n"
        "Fill in your project-specific patterns below. "
        "These guide Claude to follow your team's conventions.\n"
        "\n"
        "## Naming Conventions\n"
        "\n"
        "(Add your naming rules here.)\n"
        "\n"
        "## Architecture Patterns\n"
        "\n"
        "(Add your architecture patterns here.)\n"
        "\n"
        "## Code Organization\n"
        "\n"
        "(Add your code organization rules here.)\n"
        "\n"
        "## Tip\n"
        "\n"
        "Use `npx skills add anthropics/skills --skill skill-creator` "
        "to have Claude help you write this skill.\n"
    )

    rel = ".claude/skills/project-patterns/SKILL.md"
    if tracker is not None:
        tracker.write_text(rel, content)
    else:
        path = skills_dir / "SKILL.md"
        path.write_text(content)
    return [rel]
