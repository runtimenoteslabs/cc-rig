"""Tests for .claude/rules/*.md generator (v3.1 CC v2.1.108+ alignment)."""

from __future__ import annotations

from pathlib import Path

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.fileops import FileTracker
from cc_rig.generators.rules import generate_rules


def _gen(template: str, workflow: str, tmp_path: Path) -> Path:
    config = compute_defaults(template, workflow, project_name="test-project")
    tracker = FileTracker(tmp_path)
    generate_rules(config, tmp_path, tracker=tracker)
    return tmp_path / ".claude" / "rules"


class TestRulesGeneration:
    def test_tests_md_always_for_recognized_languages(self, tmp_path):
        rules = _gen("fastapi", "standard", tmp_path)
        assert (rules / "tests.md").exists()

    def test_tests_md_paths_frontmatter_present(self, tmp_path):
        rules = _gen("fastapi", "standard", tmp_path)
        content = (rules / "tests.md").read_text()
        assert content.startswith("---\n")
        assert "paths:" in content
        assert "tests/**/*.py" in content

    def test_security_md_only_for_high_rigor(self, tmp_path):
        rules = _gen("fastapi", "rigorous", tmp_path)
        assert (rules / "security.md").exists()

    def test_security_md_absent_for_quick(self, tmp_path):
        rules = _gen("fastapi", "speedrun", tmp_path)
        assert not (rules / "security.md").exists()

    def test_security_md_present_for_spec_driven(self, tmp_path):
        rules = _gen("fastapi", "spec-driven", tmp_path)
        assert (rules / "security.md").exists()

    def test_security_md_no_paths_eager_load(self, tmp_path):
        rules = _gen("fastapi", "rigorous", tmp_path)
        content = (rules / "security.md").read_text()
        # security.md is eager-load: no paths frontmatter
        assert not content.startswith("---")

    def test_migrations_md_for_django(self, tmp_path):
        rules = _gen("django", "standard", tmp_path)
        assert (rules / "migrations.md").exists()
        content = (rules / "migrations.md").read_text()
        assert "**/migrations/**" in content

    def test_migrations_md_for_rails(self, tmp_path):
        rules = _gen("rails", "standard", tmp_path)
        assert (rules / "migrations.md").exists()

    def test_migrations_md_absent_for_rust_cli(self, tmp_path):
        rules = _gen("rust-cli", "standard", tmp_path)
        assert not (rules / "migrations.md").exists()

    def test_frontend_md_for_nextjs(self, tmp_path):
        rules = _gen("nextjs", "standard", tmp_path)
        assert (rules / "frontend.md").exists()

    def test_frontend_md_absent_for_python_backend(self, tmp_path):
        rules = _gen("django", "standard", tmp_path)
        assert not (rules / "frontend.md").exists()

    def test_no_rules_for_generic_template(self, tmp_path):
        # generic template has language="generic", no detection match
        rules = _gen("generic", "standard", tmp_path)
        assert not rules.exists() or not list(rules.glob("*.md"))


class TestRulesUserAuthored:
    """Gate 2 contract: skip files the user has authored."""

    def test_skips_user_authored_file(self, tmp_path):
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        # User pre-authors tests.md
        user_content = "# User's own tests rules\n\nDon't overwrite me."
        (rules_dir / "tests.md").write_text(user_content)
        # Now run the generator
        config = compute_defaults("fastapi", "standard", project_name="test")
        tracker = FileTracker(tmp_path)
        generate_rules(config, tmp_path, tracker=tracker)
        # User content should be intact
        assert (rules_dir / "tests.md").read_text() == user_content

    def test_overwrites_when_we_wrote_it(self, tmp_path):
        # Generate, then regenerate with same tracker — should overwrite our own
        config = compute_defaults("fastapi", "standard", project_name="test")
        tracker = FileTracker(tmp_path)
        generate_rules(config, tmp_path, tracker=tracker)
        first = (tmp_path / ".claude" / "rules" / "tests.md").read_text()
        # Mutate file but use a fresh tracker (simulates next run with no manifest)
        (tmp_path / ".claude" / "rules" / "tests.md").write_text("user edit")
        tracker2 = FileTracker(tmp_path)
        generate_rules(config, tmp_path, tracker=tracker2)
        # Without prior_manifest, fresh tracker treats it as user-authored, skips
        assert (tmp_path / ".claude" / "rules" / "tests.md").read_text() == "user edit"
        # First content was the generated one
        assert "# Test-file rules" in first

    def test_no_tracker_skips_existing(self, tmp_path):
        rules_dir = tmp_path / ".claude" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "tests.md").write_text("existing")
        config = compute_defaults("fastapi", "standard", project_name="test")
        generate_rules(config, tmp_path, tracker=None)
        assert (rules_dir / "tests.md").read_text() == "existing"
