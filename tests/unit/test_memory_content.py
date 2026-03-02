"""Tests for memory file content — validates structure, not just existence."""

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.memory import MEMORY_FILE_TEMPLATES, generate_memory


def _generate(tmp_path, template="fastapi", workflow="standard"):
    config = compute_defaults(template, workflow, project_name="test")
    files = generate_memory(config, tmp_path)
    return config, files


class TestMemoryFileContent:
    """Validate content of each generated memory file."""

    def test_decisions_has_correct_header(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "decisions.md").read_text()
        assert content.startswith("# Decisions")

    def test_decisions_has_format_spec(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "decisions.md").read_text()
        assert "[YYYY-MM-DD]" in content
        assert "Decision:" in content
        assert "Reason:" in content

    def test_patterns_has_correct_header(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "patterns.md").read_text()
        assert content.startswith("# Patterns")

    def test_patterns_has_format_spec(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "patterns.md").read_text()
        assert "[YYYY-MM-DD]" in content
        assert "Pattern:" in content

    def test_gotchas_has_correct_header(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "gotchas.md").read_text()
        assert content.startswith("# Gotchas")

    def test_gotchas_has_format_spec(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "gotchas.md").read_text()
        assert "[YYYY-MM-DD]" in content
        assert "Gotcha:" in content
        assert "Fix:" in content

    def test_people_has_correct_header(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "people.md").read_text()
        assert content.startswith("# People")

    def test_people_has_format_spec(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "people.md").read_text()
        assert "[YYYY-MM-DD]" in content
        assert "owns" in content

    def test_session_log_has_correct_header(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "session-log.md").read_text()
        assert content.startswith("# Session Log")

    def test_session_log_has_rotation_rule(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "session-log.md").read_text()
        assert "last 20" in content
        assert "history" in content


class TestAntiBallooning:
    """Validate one-line entry format is enforced in templates."""

    def test_all_files_say_one_line(self, tmp_path):
        _generate(tmp_path)
        for filename in MEMORY_FILE_TEMPLATES:
            content = (tmp_path / "memory" / filename).read_text()
            assert "One line per entry" in content or "one-line" in content, (
                f"{filename} missing anti-ballooning one-line rule"
            )

    def test_all_files_have_entry_marker(self, tmp_path):
        _generate(tmp_path)
        for filename in MEMORY_FILE_TEMPLATES:
            content = (tmp_path / "memory" / filename).read_text()
            assert "<!-- Entries below -->" in content, f"{filename} missing entry marker"


class TestMemoryReadme:
    """Validate MEMORY-README.md instructions."""

    def test_readme_exists(self, tmp_path):
        _generate(tmp_path)
        assert (tmp_path / "memory" / "MEMORY-README.md").exists()

    def test_explains_two_systems(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "MEMORY-README.md").read_text()
        assert "Auto-memory" in content
        assert "Team memory" in content

    def test_has_anti_ballooning_rules(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "MEMORY-README.md").read_text()
        assert "Anti-Ballooning" in content
        assert "One line per entry" in content
        assert "last 20" in content

    def test_has_pointer_loading_instruction(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "MEMORY-README.md").read_text()
        assert "Read tool" in content
        assert "Do NOT put" in content or "not here" in content

    def test_has_file_purposes_table(self, tmp_path):
        _generate(tmp_path)
        content = (tmp_path / "memory" / "MEMORY-README.md").read_text()
        assert "decisions.md" in content
        assert "patterns.md" in content
        assert "gotchas.md" in content
        assert "people.md" in content
        assert "session-log.md" in content

    def test_no_memory_when_disabled(self, tmp_path):
        config = compute_defaults("fastapi", "speedrun", project_name="test")
        files = generate_memory(config, tmp_path)
        assert files == []
        assert not (tmp_path / "memory").exists()
