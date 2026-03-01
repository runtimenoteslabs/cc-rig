"""Tests for project detection from file markers."""

import json

from cc_rig.config.detection import detect_project


class TestLanguageDetection:
    def test_empty_directory(self, tmp_path):
        result = detect_project(tmp_path)
        assert result.language == ""
        assert result.framework == ""
        assert result.confidence == "none"
        assert result.markers_found == []

    def test_nonexistent_directory(self, tmp_path):
        result = detect_project(tmp_path / "nonexistent")
        assert result.language == ""
        assert result.confidence == "none"

    def test_python_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        result = detect_project(tmp_path)
        assert result.language == "python"
        assert "pyproject.toml" in result.markers_found

    def test_python_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==3.0\n")
        result = detect_project(tmp_path)
        assert result.language == "python"

    def test_go_project(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/test\n\ngo 1.21\n")
        result = detect_project(tmp_path)
        assert result.language == "go"

    def test_rust_project(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"\n')
        result = detect_project(tmp_path)
        assert result.language == "rust"

    def test_typescript_project(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "tsconfig.json").write_text("{}")
        result = detect_project(tmp_path)
        assert result.language == "typescript"
        assert "package.json" in result.markers_found
        assert "tsconfig.json" in result.markers_found


class TestFrameworkDetection:
    def test_nextjs_from_config(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "next.config.js").write_text("module.exports = {}")
        result = detect_project(tmp_path)
        assert result.framework == "nextjs"
        assert result.confidence == "high"
        assert result.test_cmd == "npm test"

    def test_nextjs_from_mjs_config(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "next.config.mjs").write_text("export default {}")
        result = detect_project(tmp_path)
        assert result.framework == "nextjs"

    def test_django_from_manage_py(self, tmp_path):
        (tmp_path / "manage.py").write_text("#!/usr/bin/env python")
        result = detect_project(tmp_path)
        assert result.framework == "django"
        assert result.confidence == "high"
        assert result.test_cmd == "python manage.py test"

    def test_fastapi_from_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = ["fastapi"]\n'
        )
        result = detect_project(tmp_path)
        assert result.framework == "fastapi"
        assert result.confidence == "high"
        assert result.test_cmd == "pytest"

    def test_flask_from_requirements(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("flask==3.0\nSQLAlchemy\n")
        result = detect_project(tmp_path)
        assert result.framework == "flask"
        assert result.confidence == "high"

    def test_gin_from_go_mod(self, tmp_path):
        (tmp_path / "go.mod").write_text(
            "module example.com/test\n\ngo 1.21\n\nrequire github.com/gin-gonic/gin v1.9\n"
        )
        result = detect_project(tmp_path)
        assert result.framework == "gin"
        assert result.confidence == "high"
        assert result.test_cmd == "go test ./..."

    def test_echo_from_go_mod(self, tmp_path):
        (tmp_path / "go.mod").write_text(
            "module example.com/test\n\ngo 1.21\n\nrequire github.com/labstack/echo v4\n"
        )
        result = detect_project(tmp_path)
        assert result.framework == "echo"
        assert result.confidence == "high"

    def test_rust_cli_from_cargo(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "test"\n\n[dependencies]\nclap = "4.0"\n'
        )
        result = detect_project(tmp_path)
        assert result.framework == "clap"
        assert result.confidence == "high"
        assert result.test_cmd == "cargo test"

    def test_axum_from_cargo(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "test"\n\n[dependencies]\naxum = "0.7"\ntokio = "1"\n'
        )
        result = detect_project(tmp_path)
        assert result.framework == "axum"
        assert result.confidence == "high"
        assert result.test_cmd == "cargo test"

    def test_axum_wins_over_clap(self, tmp_path):
        """Axum should take priority when both axum and clap are present."""
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "test"\n\n[dependencies]\naxum = "0.7"\nclap = "4.0"\ntokio = "1"\n'
        )
        result = detect_project(tmp_path)
        assert result.framework == "axum"

    def test_rails_from_gemfile_and_marker(self, tmp_path):
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\ngem 'rails', '~> 7.1'\n")
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "application.rb").write_text("module MyApp\nend\n")
        result = detect_project(tmp_path)
        assert result.framework == "rails"
        assert result.confidence == "high"

    def test_rails_from_gemfile_deps(self, tmp_path):
        """Detect Rails from Gemfile dependencies alone (no config/application.rb marker)."""
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\ngem 'rails', '~> 7.1'\n")
        result = detect_project(tmp_path)
        assert result.framework == "rails"
        assert result.confidence == "high"

    def test_spring_boot_from_pom_xml(self, tmp_path):
        (tmp_path / "pom.xml").write_text(
            "<project>\n<dependencies>\n"
            "<dependency>spring-boot-starter-web</dependency>\n"
            "</dependencies>\n</project>\n"
        )
        result = detect_project(tmp_path)
        assert result.framework == "spring-boot"
        assert result.confidence == "high"
        assert result.test_cmd == "./mvnw test"

    def test_spring_boot_from_build_gradle(self, tmp_path):
        (tmp_path / "build.gradle").write_text(
            "plugins {\n  id 'org.springframework.boot' version '3.2.0'\n}\n"
        )
        result = detect_project(tmp_path)
        assert result.framework == "spring-boot"
        assert result.confidence == "high"

    def test_spring_boot_from_framework_marker(self, tmp_path):
        """Detect Spring Boot from application.properties marker."""
        (tmp_path / "pom.xml").write_text("<project></project>\n")
        src_dir = tmp_path / "src" / "main" / "resources"
        src_dir.mkdir(parents=True)
        (src_dir / "application.properties").write_text("server.port=8080\n")
        result = detect_project(tmp_path)
        assert result.framework == "spring-boot"
        assert result.confidence == "high"

    def test_aspnet_from_csproj(self, tmp_path):
        (tmp_path / "MyApp.csproj").write_text(
            '<Project Sdk="Microsoft.NET.Sdk.Web">\n'
            "<ItemGroup>\n"
            '<PackageReference Include="Microsoft.AspNetCore.OpenApi" />\n'
            "</ItemGroup>\n</Project>\n"
        )
        result = detect_project(tmp_path)
        assert result.framework == "aspnet"
        assert result.confidence == "high"
        assert result.test_cmd == "dotnet test"

    def test_csharp_detected_from_csproj(self, tmp_path):
        """*.csproj files should detect language as csharp."""
        (tmp_path / "MyApp.csproj").write_text('<Project Sdk="Microsoft.NET.Sdk">\n</Project>\n')
        result = detect_project(tmp_path)
        assert result.language == "csharp"

    def test_java_no_framework(self, tmp_path):
        """Plain pom.xml without Spring Boot should be low confidence."""
        (tmp_path / "pom.xml").write_text("<project><groupId>com.example</groupId></project>\n")
        result = detect_project(tmp_path)
        assert result.language == "java"
        assert result.framework == ""
        assert result.confidence == "low"


class TestFrameworkDefaults:
    def test_nextjs_defaults(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "test", "dependencies": {"next": "14.0"}})
        )
        result = detect_project(tmp_path)
        assert result.framework == "nextjs"
        assert result.language == "typescript"
        assert result.project_type == "web_fullstack"
        assert result.source_dir == "app"
        assert result.build_cmd == "next build"

    def test_fastapi_defaults(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = ["fastapi"]\n'
        )
        result = detect_project(tmp_path)
        assert result.project_type == "api"
        assert result.source_dir == "app"
        assert result.lint_cmd == "ruff check ."

    def test_rust_cli_defaults(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "test"\n\n[dependencies]\nclap = "4.0"\n'
        )
        result = detect_project(tmp_path)
        assert result.project_type == "cli"
        assert result.source_dir == "src"
        assert result.build_cmd == "cargo build"

    def test_axum_defaults(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "test"\n\n[dependencies]\naxum = "0.7"\n'
        )
        result = detect_project(tmp_path)
        assert result.project_type == "api"
        assert result.source_dir == "src"
        assert result.lint_cmd == "cargo clippy"

    def test_rails_defaults(self, tmp_path):
        (tmp_path / "Gemfile").write_text("gem 'rails', '~> 7.1'\n")
        result = detect_project(tmp_path)
        assert result.project_type == "web_fullstack"
        assert result.source_dir == "app"
        assert result.test_dir == "test"
        assert result.lint_cmd == "bundle exec rubocop"
        assert result.typecheck_cmd == ""

    def test_spring_boot_defaults(self, tmp_path):
        (tmp_path / "pom.xml").write_text(
            "<project><dependencies>spring-boot-starter-web</dependencies></project>\n"
        )
        result = detect_project(tmp_path)
        assert result.project_type == "api"
        assert result.source_dir == "src/main/java"
        assert result.test_dir == "src/test/java"
        assert result.lint_cmd == "./mvnw checkstyle:check"
        assert result.typecheck_cmd == ""
        assert result.build_cmd == "./mvnw package -DskipTests"

    def test_aspnet_defaults(self, tmp_path):
        (tmp_path / "MyApp.csproj").write_text(
            '<Project><PackageReference Include="Microsoft.AspNetCore" /></Project>\n'
        )
        result = detect_project(tmp_path)
        assert result.project_type == "api"
        assert result.source_dir == "src"
        assert result.test_dir == "tests"
        assert result.lint_cmd == "dotnet format --verify-no-changes"
        assert result.typecheck_cmd == ""
        assert result.build_cmd == "dotnet build"


class TestLowConfidence:
    def test_python_no_framework(self, tmp_path):
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup()")
        result = detect_project(tmp_path)
        assert result.language == "python"
        assert result.framework == ""
        assert result.confidence == "low"

    def test_go_no_framework(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/test\n\ngo 1.21\n")
        result = detect_project(tmp_path)
        assert result.language == "go"
        assert result.framework == ""
        assert result.confidence == "low"

    def test_ruby_no_framework(self, tmp_path):
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\ngem 'sinatra'\n")
        result = detect_project(tmp_path)
        assert result.language == "ruby"
        assert result.framework == ""
        assert result.confidence == "low"


class TestEdgeCases:
    def test_multiple_markers(self, tmp_path):
        """Multiple markers should all be recorded."""
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "test"\ndependencies = ["fastapi"]\n'
        )
        (tmp_path / "requirements.txt").write_text("fastapi\n")
        result = detect_project(tmp_path)
        assert "pyproject.toml" in result.markers_found
        assert "requirements.txt" in result.markers_found
        assert result.framework == "fastapi"

    def test_nextjs_from_package_json_deps(self, tmp_path):
        """Detect Next.js from package.json dependencies (no next.config.*)."""
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "test", "dependencies": {"next": "14.0", "react": "18.0"}})
        )
        result = detect_project(tmp_path)
        assert result.framework == "nextjs"
        assert result.confidence == "high"
