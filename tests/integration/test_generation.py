"""Integration tests: full generation for all 80 template × workflow combos."""

import json

import pytest

from cc_rig.config.defaults import compute_defaults
from cc_rig.presets.manager import BUILTIN_TEMPLATES, BUILTIN_WORKFLOWS
from cc_rig.validator import validate_output


def _generate_full(template, workflow, output_dir):
    from cc_rig.generators.orchestrator import generate_all

    config = compute_defaults(template, workflow, project_name="test-project")
    manifest = generate_all(config, output_dir)
    return config, manifest


# ── Shared fixture: generate once per (template, workflow) combo ──


@pytest.fixture(
    params=[(t, w) for t in BUILTIN_TEMPLATES for w in BUILTIN_WORKFLOWS],
    ids=lambda tw: f"{tw[0]}-{tw[1]}",
)
def generated_project(request, tmp_path):
    """Generate a project once, reuse for all cross-product assertions."""
    template, workflow = request.param
    output = tmp_path / "output"
    config, manifest = _generate_full(template, workflow, output)
    return config, manifest, output, template, workflow


class TestCrossProduct:
    """All 4 cross-product checks share one generate_all() call per combo."""

    def test_generation_succeeds(self, generated_project):
        config, manifest, output, template, workflow = generated_project
        assert (output / "CLAUDE.md").exists()
        assert len(manifest["files"]) > 0

    def test_no_empty_files(self, generated_project):
        config, manifest, output, template, workflow = generated_project
        for path in output.rglob("*"):
            if path.is_file():
                assert path.stat().st_size > 0, f"Empty file: {path.relative_to(output)}"

    def test_all_json_valid(self, generated_project):
        config, manifest, output, template, workflow = generated_project
        for path in output.rglob("*.json"):
            try:
                json.loads(path.read_text())
            except json.JSONDecodeError:
                pytest.fail(f"Invalid JSON: {path.relative_to(output)}")

    def test_validator_passes(self, generated_project):
        config, manifest, output, template, workflow = generated_project
        result = validate_output(config, output, manifest)
        errors = [f"{i.check}: {i.message} ({i.file})" for i in result.errors]
        assert result.passed, "Validator errors:\n" + "\n".join(errors)


# ── Non-parametrized tests (single-combo, run once each) ──


class TestGeneratedFilesExist:
    def test_claude_md_exists(self, tmp_path):
        output = tmp_path / "output"
        _generate_full("fastapi", "standard", output)
        assert (output / "CLAUDE.md").exists()

    def test_settings_json_exists(self, tmp_path):
        output = tmp_path / "output"
        _generate_full("fastapi", "standard", output)
        assert (output / ".claude" / "settings.json").exists()

    def test_agent_docs_exist(self, tmp_path):
        output = tmp_path / "output"
        _generate_full("fastapi", "standard", output)
        for doc in ["architecture.md", "conventions.md", "testing.md", "deployment.md"]:
            assert (output / "agent_docs" / doc).exists(), f"Missing {doc}"

    def test_memory_files_when_enabled(self, tmp_path):
        output = tmp_path / "output"
        config, _ = _generate_full("fastapi", "standard", output)
        assert config.features.memory is True
        assert (output / "memory" / "decisions.md").exists()
        assert (output / "memory" / "MEMORY-README.md").exists()

    def test_no_memory_when_disabled(self, tmp_path):
        output = tmp_path / "output"
        config, _ = _generate_full("fastapi", "speedrun", output)
        assert config.features.memory is False
        assert not (output / "memory").exists()

    def test_config_saved(self, tmp_path):
        output = tmp_path / "output"
        _generate_full("fastapi", "standard", output)
        assert (output / ".cc-rig.json").exists()
        data = json.loads((output / ".cc-rig.json").read_text())
        assert data["framework"] == "fastapi"

    def test_mcp_json_exists(self, tmp_path):
        output = tmp_path / "output"
        _generate_full("fastapi", "standard", output)
        assert (output / ".mcp.json").exists()

    def test_settings_local_json_exists(self, tmp_path):
        output = tmp_path / "output"
        _generate_full("fastapi", "standard", output)
        path = output / ".claude" / "settings.local.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["permissions"]["allow"] == []
        assert data["permissions"]["deny"] == []
        assert data["env"] == {}


class TestManifestCompleteness:
    def test_manifest_tracks_all_files(self, tmp_path):
        output = tmp_path / "output"
        _, manifest = _generate_full("fastapi", "standard", output)
        manifest_files = set(manifest["files"])
        actual_files = set()
        for path in output.rglob("*"):
            if path.is_file():
                actual_files.add(str(path.relative_to(output)))
        assert actual_files == manifest_files, (
            f"Untracked: {actual_files - manifest_files}, Missing: {manifest_files - actual_files}"
        )


class TestCLAUDEmdLineCounts:
    _TARGETS = {
        "speedrun": 65,
        "standard": 100,
        "spec-driven": 120,
        "gtd-lite": 120,
        "verify-heavy": 125,
    }

    @pytest.mark.parametrize("workflow", BUILTIN_WORKFLOWS)
    def test_line_count_within_target(self, workflow, tmp_path):
        output = tmp_path / "output"
        _generate_full("fastapi", workflow, output)
        content = (output / "CLAUDE.md").read_text()
        line_count = content.count("\n") + 1
        target = self._TARGETS[workflow]
        assert line_count <= target, f"{workflow}: {line_count} lines > target {target}"
