"""Tests for agent_docs/ content generation."""

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.agent_docs import generate_agent_docs
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS
from cc_rig.templates import get_framework_content

# ── Expected files ───────────────────────────────────────────────────

EXPECTED_DOCS = [
    "agent_docs/architecture.md",
    "agent_docs/conventions.md",
    "agent_docs/testing.md",
    "agent_docs/deployment.md",
    "agent_docs/cache-friendly-workflow.md",
]

# Framework-specific content markers — each template should include these
# keywords in the respective doc section.
FRAMEWORK_MARKERS = {
    "fastapi": {
        "architecture": ["FastAPI", "Pydantic", "APIRouter"],
        "conventions": ["async", "Depends"],
        "testing": ["pytest", "httpx"],
        "deployment": ["uvicorn"],
    },
    "django": {
        "architecture": ["Django", "models.py", "views.py"],
        "conventions": ["Django", "Model"],
        "testing": ["pytest", "django"],
        "deployment": ["gunicorn"],
    },
    "flask": {
        "architecture": ["Flask", "Blueprint"],
        "conventions": ["blueprint"],
        "testing": ["pytest"],
        "deployment": ["gunicorn"],
    },
    "nextjs": {
        "architecture": ["Next.js", "App Router"],
        "conventions": ["Server Component", "client"],
        "testing": ["Jest", "Playwright"],
        "deployment": ["Vercel"],
    },
    "gin": {
        "architecture": ["Gin"],
        "conventions": ["handler"],
        "testing": ["go test"],
        "deployment": ["Docker"],
    },
    "echo": {
        "architecture": ["Echo"],
        "conventions": ["handler"],
        "testing": ["go test"],
        "deployment": ["Docker"],
    },
    "rust-cli": {
        "architecture": ["Clap", "CLI"],
        "conventions": ["Rust"],
        "testing": ["cargo test"],
        "deployment": ["cargo"],
    },
}


def _generate_docs(template, workflow, tmp_path):
    config = compute_defaults(template, workflow, project_name="test-project")
    files = generate_agent_docs(config, tmp_path)
    return config, files


class TestAgentDocsGeneration:
    """Verify all 5 doc files are generated for every combo."""

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_all_docs_generated(self, template, tmp_path):
        _, files = _generate_docs(template, "standard", tmp_path)
        assert sorted(files) == sorted(EXPECTED_DOCS)

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_doc_files_exist(self, template, tmp_path):
        _generate_docs(template, "standard", tmp_path)
        for doc in EXPECTED_DOCS:
            path = tmp_path / doc
            assert path.exists(), f"Missing: {doc}"

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_doc_files_not_empty(self, template, tmp_path):
        _generate_docs(template, "standard", tmp_path)
        for doc in EXPECTED_DOCS:
            path = tmp_path / doc
            assert path.stat().st_size > 50, f"{doc} too small"

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_docs_generated_for_all_workflows(self, workflow, tmp_path):
        _, files = _generate_docs("fastapi", workflow, tmp_path)
        assert sorted(files) == sorted(EXPECTED_DOCS)

    def test_returns_exactly_five_files(self, tmp_path):
        _, files = _generate_docs("fastapi", "standard", tmp_path)
        assert len(files) == 5


class TestAgentDocsStructure:
    """Verify doc files have proper markdown structure."""

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_docs_start_with_h1_header(self, template, tmp_path):
        _generate_docs(template, "standard", tmp_path)
        for section in ("architecture", "conventions", "testing", "deployment"):
            content = (tmp_path / "agent_docs" / f"{section}.md").read_text()
            assert content.startswith(f"# {section.title()}\n"), (
                f"{section}.md doesn't start with expected H1 header"
            )

    @pytest.mark.parametrize("template", BUILTIN_TEMPLATES)
    def test_docs_have_substantial_content(self, template, tmp_path):
        """Each doc should have real framework-specific content, not stubs."""
        _generate_docs(template, "standard", tmp_path)
        for section in ("architecture", "conventions", "testing", "deployment"):
            content = (tmp_path / "agent_docs" / f"{section}.md").read_text()
            # At least 200 chars of content (not just a header)
            assert len(content) > 200, (
                f"{section}.md for {template} has only {len(content)} chars — likely a stub"
            )

    def test_cache_friendly_workflow_has_required_sections(self, tmp_path):
        _generate_docs("fastapi", "standard", tmp_path)
        content = (tmp_path / "agent_docs" / "cache-friendly-workflow.md").read_text()
        assert "# Cache-Friendly Workflow" in content
        assert "## CLAUDE.md Structure" in content
        assert "## Do" in content
        assert "## Don't" in content

    def test_cache_friendly_workflow_mentions_subagents(self, tmp_path):
        _generate_docs("fastapi", "standard", tmp_path)
        content = (tmp_path / "agent_docs" / "cache-friendly-workflow.md").read_text()
        assert "subagent" in content.lower() or "Task tool" in content

    def test_no_placeholder_text(self, tmp_path):
        """No doc should contain placeholder markers."""
        _generate_docs("fastapi", "standard", tmp_path)
        placeholders = ["<!-- Fill in -->", "TODO", "FIXME", "TBD", "PLACEHOLDER"]
        for doc in EXPECTED_DOCS:
            content = (tmp_path / doc).read_text()
            for p in placeholders:
                assert p not in content, f"{doc} contains placeholder '{p}'"


class TestFrameworkSpecificContent:
    """Verify docs contain framework-specific content, not generic text."""

    @pytest.mark.parametrize("template", list(FRAMEWORK_MARKERS.keys()))
    def test_architecture_is_framework_specific(self, template, tmp_path):
        _generate_docs(template, "standard", tmp_path)
        content = (tmp_path / "agent_docs" / "architecture.md").read_text()
        markers = FRAMEWORK_MARKERS[template]["architecture"]
        found = [m for m in markers if m.lower() in content.lower()]
        assert len(found) >= 1, (
            f"{template} architecture.md missing framework markers. Expected any of {markers}"
        )

    @pytest.mark.parametrize("template", list(FRAMEWORK_MARKERS.keys()))
    def test_conventions_is_framework_specific(self, template, tmp_path):
        _generate_docs(template, "standard", tmp_path)
        content = (tmp_path / "agent_docs" / "conventions.md").read_text()
        markers = FRAMEWORK_MARKERS[template]["conventions"]
        found = [m for m in markers if m.lower() in content.lower()]
        assert len(found) >= 1, (
            f"{template} conventions.md missing framework markers. Expected any of {markers}"
        )

    @pytest.mark.parametrize("template", list(FRAMEWORK_MARKERS.keys()))
    def test_testing_is_framework_specific(self, template, tmp_path):
        _generate_docs(template, "standard", tmp_path)
        content = (tmp_path / "agent_docs" / "testing.md").read_text()
        markers = FRAMEWORK_MARKERS[template]["testing"]
        found = [m for m in markers if m.lower() in content.lower()]
        assert len(found) >= 1, (
            f"{template} testing.md missing framework markers. Expected any of {markers}"
        )

    @pytest.mark.parametrize("template", list(FRAMEWORK_MARKERS.keys()))
    def test_deployment_is_framework_specific(self, template, tmp_path):
        _generate_docs(template, "standard", tmp_path)
        content = (tmp_path / "agent_docs" / "deployment.md").read_text()
        markers = FRAMEWORK_MARKERS[template]["deployment"]
        found = [m for m in markers if m.lower() in content.lower()]
        assert len(found) >= 1, (
            f"{template} deployment.md missing framework markers. Expected any of {markers}"
        )


class TestFrameworkContentRegistry:
    """Verify get_framework_content returns well-formed dicts."""

    @pytest.mark.parametrize(
        "framework",
        ["fastapi", "django", "flask", "nextjs", "gin", "echo", "clap"],
    )
    def test_content_has_all_sections(self, framework):
        content = get_framework_content(framework)
        required = {"rules", "architecture", "conventions", "testing", "deployment"}
        missing = required - set(content.keys())
        assert not missing, f"Framework '{framework}' CONTENT missing sections: {missing}"

    @pytest.mark.parametrize(
        "framework",
        ["fastapi", "django", "flask", "nextjs", "gin", "echo", "clap"],
    )
    def test_content_sections_are_non_empty_strings(self, framework):
        content = get_framework_content(framework)
        for key in ("rules", "architecture", "conventions", "testing", "deployment"):
            val = content.get(key, "")
            assert isinstance(val, str), f"{framework}.{key} is {type(val)}, expected str"
            assert len(val) > 50, f"{framework}.{key} too short ({len(val)} chars)"

    def test_unknown_framework_falls_back_to_generic(self):
        content = get_framework_content("unknown-framework-xyz")
        assert "rules" in content
        assert len(content["rules"]) > 10

    def test_clap_maps_to_rust_cli_module(self):
        """clap framework should resolve to rust_cli.py module."""
        content = get_framework_content("clap")
        # Should have Rust/Clap-specific content
        combined = " ".join(content.values()).lower()
        assert "rust" in combined or "clap" in combined or "cargo" in combined


class TestDocsDeterminism:
    """Verify docs are identical across repeated generation."""

    def test_same_template_produces_same_docs(self, tmp_path):
        import tempfile

        _, files1 = _generate_docs("fastapi", "standard", tmp_path)
        contents1 = {f: (tmp_path / f).read_text() for f in files1}

        with tempfile.TemporaryDirectory() as tmp2:
            from pathlib import Path

            _, files2 = _generate_docs("fastapi", "standard", Path(tmp2))
            contents2 = {f: (Path(tmp2) / f).read_text() for f in files2}

        assert contents1 == contents2

    def test_docs_same_across_workflows(self, tmp_path):
        """Agent docs should be framework-driven, not workflow-driven."""
        import tempfile

        _generate_docs("fastapi", "speedrun", tmp_path)
        speedrun = {doc: (tmp_path / doc).read_text() for doc in EXPECTED_DOCS}

        with tempfile.TemporaryDirectory() as tmp2:
            from pathlib import Path

            _generate_docs("fastapi", "verify-heavy", Path(tmp2))
            verify = {doc: (Path(tmp2) / doc).read_text() for doc in EXPECTED_DOCS}

        assert speedrun == verify
