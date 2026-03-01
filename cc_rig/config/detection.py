"""Detect existing project language, framework, and tool commands from file markers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DetectionResult:
    """Result of scanning a directory for project markers."""

    language: str = ""
    framework: str = ""
    project_type: str = ""
    test_cmd: str = ""
    lint_cmd: str = ""
    format_cmd: str = ""
    typecheck_cmd: str = ""
    build_cmd: str = ""
    source_dir: str = "."
    test_dir: str = "tests"
    markers_found: list[str] = field(default_factory=list)
    confidence: str = "none"  # none, low, high


# Markers that indicate a language
_LANGUAGE_MARKERS: dict[str, str] = {
    "package.json": "typescript",
    "tsconfig.json": "typescript",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "manage.py": "python",
    "Gemfile": "ruby",
    "composer.json": "php",
    "pom.xml": "java",
    "build.gradle": "java",
    "mix.exs": "elixir",
}

# Framework-specific markers (checked after language detection)
_FRAMEWORK_MARKERS: dict[str, str] = {
    "next.config.js": "nextjs",
    "next.config.mjs": "nextjs",
    "next.config.ts": "nextjs",
    "manage.py": "django",
    "config/application.rb": "rails",
    "src/main/resources/application.properties": "spring-boot",
    "src/main/resources/application.yml": "spring-boot",
    "artisan": "laravel",
}

# Template defaults for detected frameworks (matches SMART-DEFAULTS-MATRIX.md §3)
_FRAMEWORK_DEFAULTS: dict[str, dict[str, str]] = {
    "nextjs": {
        "language": "typescript",
        "project_type": "web_fullstack",
        "test_cmd": "npm test",
        "lint_cmd": "npm run lint",
        "format_cmd": "npx prettier --write",
        "typecheck_cmd": "npx tsc --noEmit",
        "build_cmd": "next build",
        "source_dir": "app",
        "test_dir": "src/__tests__",
    },
    "fastapi": {
        "language": "python",
        "project_type": "api",
        "test_cmd": "pytest",
        "lint_cmd": "ruff check .",
        "format_cmd": "ruff format .",
        "typecheck_cmd": "mypy .",
        "build_cmd": "",
        "source_dir": "app",
        "test_dir": "tests",
    },
    "django": {
        "language": "python",
        "project_type": "web_fullstack",
        "test_cmd": "python manage.py test",
        "lint_cmd": "ruff check .",
        "format_cmd": "ruff format .",
        "typecheck_cmd": "mypy .",
        "build_cmd": "",
        "source_dir": ".",
        "test_dir": "tests",
    },
    "flask": {
        "language": "python",
        "project_type": "api",
        "test_cmd": "pytest",
        "lint_cmd": "ruff check .",
        "format_cmd": "ruff format .",
        "typecheck_cmd": "mypy .",
        "build_cmd": "",
        "source_dir": "app",
        "test_dir": "tests",
    },
    "gin": {
        "language": "go",
        "project_type": "api",
        "test_cmd": "go test ./...",
        "lint_cmd": "golangci-lint run",
        "format_cmd": "goimports -w .",
        "typecheck_cmd": "go vet ./...",
        "build_cmd": "go build ./cmd/server",
        "source_dir": ".",
        "test_dir": ".",
    },
    "echo": {
        "language": "go",
        "project_type": "api",
        "test_cmd": "go test ./...",
        "lint_cmd": "golangci-lint run",
        "format_cmd": "goimports -w .",
        "typecheck_cmd": "go vet ./...",
        "build_cmd": "go build ./cmd/server",
        "source_dir": ".",
        "test_dir": ".",
    },
    "clap": {
        "language": "rust",
        "project_type": "cli",
        "test_cmd": "cargo test",
        "lint_cmd": "cargo clippy",
        "format_cmd": "cargo fmt",
        "typecheck_cmd": "cargo check",
        "build_cmd": "cargo build",
        "source_dir": "src",
        "test_dir": "tests",
    },
    "axum": {
        "language": "rust",
        "project_type": "api",
        "test_cmd": "cargo test",
        "lint_cmd": "cargo clippy",
        "format_cmd": "cargo fmt",
        "typecheck_cmd": "cargo check",
        "build_cmd": "cargo build",
        "source_dir": "src",
        "test_dir": "tests",
    },
    "rails": {
        "language": "ruby",
        "project_type": "web_fullstack",
        "test_cmd": "bundle exec rails test",
        "lint_cmd": "bundle exec rubocop",
        "format_cmd": "bundle exec rubocop -a",
        "typecheck_cmd": "",
        "build_cmd": "",
        "source_dir": "app",
        "test_dir": "test",
    },
    "spring-boot": {
        "language": "java",
        "project_type": "api",
        "test_cmd": "./mvnw test",
        "lint_cmd": "./mvnw checkstyle:check",
        "format_cmd": "./mvnw spotless:apply",
        "typecheck_cmd": "",
        "build_cmd": "./mvnw package -DskipTests",
        "source_dir": "src/main/java",
        "test_dir": "src/test/java",
    },
    "aspnet": {
        "language": "csharp",
        "project_type": "api",
        "test_cmd": "dotnet test",
        "lint_cmd": "dotnet format --verify-no-changes",
        "format_cmd": "dotnet format",
        "typecheck_cmd": "",
        "build_cmd": "dotnet build",
        "source_dir": "src",
        "test_dir": "tests",
    },
    "laravel": {
        "language": "php",
        "project_type": "web_fullstack",
        "test_cmd": "php artisan test",
        "lint_cmd": "./vendor/bin/pint",
        "format_cmd": "./vendor/bin/pint",
        "typecheck_cmd": "",
        "build_cmd": "",
        "source_dir": "app",
        "test_dir": "tests",
    },
    "express": {
        "language": "typescript",
        "project_type": "api",
        "test_cmd": "npm test",
        "lint_cmd": "npm run lint",
        "format_cmd": "npx prettier --write .",
        "typecheck_cmd": "npx tsc --noEmit",
        "build_cmd": "npm run build",
        "source_dir": "src",
        "test_dir": "src/__tests__",
    },
    "phoenix": {
        "language": "elixir",
        "project_type": "web_fullstack",
        "test_cmd": "mix test",
        "lint_cmd": "mix credo",
        "format_cmd": "mix format",
        "typecheck_cmd": "",
        "build_cmd": "mix release",
        "source_dir": "lib",
        "test_dir": "test",
    },
    "go-std": {
        "language": "go",
        "project_type": "api",
        "test_cmd": "go test ./...",
        "lint_cmd": "golangci-lint run",
        "format_cmd": "goimports -w .",
        "typecheck_cmd": "go vet ./...",
        "build_cmd": "go build ./cmd/server",
        "source_dir": ".",
        "test_dir": ".",
    },
}


def _detect_framework_from_deps(project_dir: Path, language: str) -> str:
    """Try to detect framework by reading dependency files."""
    if language == "python":
        # Check pyproject.toml for dependencies
        pyproject = project_dir / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                if "fastapi" in content.lower():
                    return "fastapi"
                if "flask" in content.lower():
                    return "flask"
                if "django" in content.lower():
                    return "django"
            except OSError:
                pass

        # Check requirements.txt
        requirements = project_dir / "requirements.txt"
        if requirements.exists():
            try:
                content = requirements.read_text().lower()
                if "fastapi" in content:
                    return "fastapi"
                if "flask" in content:
                    return "flask"
                if "django" in content:
                    return "django"
            except OSError:
                pass

    elif language == "typescript":
        # Check package.json for Next.js or Express
        pkg_json = project_dir / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text())
                all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in all_deps:
                    return "nextjs"
                if "express" in all_deps:
                    return "express"
            except (OSError, json.JSONDecodeError):
                pass

    elif language == "go":
        # Check go.mod for gin/echo
        go_mod = project_dir / "go.mod"
        if go_mod.exists():
            try:
                content = go_mod.read_text()
                if "gin-gonic/gin" in content:
                    return "gin"
                if "labstack/echo" in content:
                    return "echo"
            except OSError:
                pass

    elif language == "rust":
        # Check Cargo.toml for axum (web) before clap (CLI)
        cargo = project_dir / "Cargo.toml"
        if cargo.exists():
            try:
                content = cargo.read_text().lower()
                if "axum" in content:
                    return "axum"
                if "clap" in content:
                    return "clap"
            except OSError:
                pass

    elif language == "ruby":
        # Check Gemfile for rails
        gemfile = project_dir / "Gemfile"
        if gemfile.exists():
            try:
                content = gemfile.read_text().lower()
                if "rails" in content:
                    return "rails"
            except OSError:
                pass

    elif language == "java":
        # Check pom.xml for Spring Boot
        pom = project_dir / "pom.xml"
        if pom.exists():
            try:
                content = pom.read_text().lower()
                if "spring-boot-starter" in content:
                    return "spring-boot"
            except OSError:
                pass
        # Check build.gradle for Spring Boot
        gradle = project_dir / "build.gradle"
        if gradle.exists():
            try:
                content = gradle.read_text().lower()
                if "org.springframework.boot" in content:
                    return "spring-boot"
            except OSError:
                pass

    elif language == "csharp":
        # Check *.csproj for ASP.NET
        csproj_files = list(project_dir.glob("*.csproj"))
        for csproj in csproj_files:
            try:
                content = csproj.read_text().lower()
                if "microsoft.aspnetcore" in content:
                    return "aspnet"
            except OSError:
                pass

    elif language == "php":
        # Check composer.json for Laravel
        composer = project_dir / "composer.json"
        if composer.exists():
            try:
                pkg = json.loads(composer.read_text())
                all_deps = {**pkg.get("require", {}), **pkg.get("require-dev", {})}
                if "laravel/framework" in all_deps:
                    return "laravel"
            except (OSError, json.JSONDecodeError):
                pass

    elif language == "elixir":
        # Check mix.exs for Phoenix
        mix_exs = project_dir / "mix.exs"
        if mix_exs.exists():
            try:
                content = mix_exs.read_text().lower()
                if "phoenix" in content:
                    return "phoenix"
            except OSError:
                pass

    return ""


def detect_project(project_dir: str | Path) -> DetectionResult:
    """Scan a directory for project markers and return detected stack info."""
    project_dir = Path(project_dir)
    result = DetectionResult()

    if not project_dir.is_dir():
        return result

    # Pass 1: Find all markers present
    for marker, language in _LANGUAGE_MARKERS.items():
        if (project_dir / marker).exists():
            result.markers_found.append(marker)
            if not result.language:
                result.language = language

    # Pass 1b: Glob-based language detection (*.csproj → csharp)
    if not result.language:
        csproj_files = list(project_dir.glob("*.csproj"))
        if csproj_files:
            result.language = "csharp"
            result.markers_found.append(csproj_files[0].name)

    # Pass 2: Check framework-specific markers
    for marker, framework in _FRAMEWORK_MARKERS.items():
        if (project_dir / marker).exists():
            result.framework = framework

    # Pass 3: If no framework from markers, try dependency files
    if not result.framework and result.language:
        result.framework = _detect_framework_from_deps(project_dir, result.language)

    # Pass 4: Apply framework defaults if we found a framework
    if result.framework and result.framework in _FRAMEWORK_DEFAULTS:
        defaults = _FRAMEWORK_DEFAULTS[result.framework]
        result.language = defaults["language"]
        result.project_type = defaults["project_type"]
        result.test_cmd = defaults["test_cmd"]
        result.lint_cmd = defaults["lint_cmd"]
        result.format_cmd = defaults["format_cmd"]
        result.typecheck_cmd = defaults["typecheck_cmd"]
        result.build_cmd = defaults["build_cmd"]
        result.source_dir = defaults["source_dir"]
        result.test_dir = defaults["test_dir"]
        result.confidence = "high"
    elif result.language:
        result.confidence = "low"

    return result
