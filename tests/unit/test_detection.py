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
