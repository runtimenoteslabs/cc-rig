"""Tests for GitHub Actions workflow generation."""

from __future__ import annotations

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.github_actions import generate_github_actions


def _make_config(
    template: str = "fastapi",
    workflow: str = "standard",
    **overrides,
):
    config = compute_defaults(template, workflow, project_name="test-proj")
    config.features.github_actions = True
    for k, v in overrides.items():
        setattr(config, k, v)
    return config


# ── Feature gate ────────────────────────────────────────────────────


class TestFeatureGate:
    def test_disabled_returns_empty(self, tmp_path):
        config = _make_config()
        config.features.github_actions = False
        files = generate_github_actions(config, tmp_path)
        assert files == []
        assert not (tmp_path / ".github" / "workflows" / "claude.yml").exists()

    def test_enabled_generates_file(self, tmp_path):
        config = _make_config()
        files = generate_github_actions(config, tmp_path)
        assert files == [".github/workflows/claude.yml"]
        assert (tmp_path / ".github" / "workflows" / "claude.yml").exists()


# ── YAML content ────────────────────────────────────────────────────


class TestYamlContent:
    def test_has_pull_request_trigger(self, tmp_path):
        config = _make_config()
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "pull_request:" in content
        assert "opened, synchronize" in content

    def test_has_issue_comment_trigger(self, tmp_path):
        config = _make_config()
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "issue_comment:" in content
        assert "@claude" in content

    def test_has_permissions(self, tmp_path):
        config = _make_config()
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "contents: read" in content
        assert "pull-requests: write" in content
        assert "issues: write" in content

    def test_uses_claude_code_action(self, tmp_path):
        config = _make_config()
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "anthropics/claude-code-action@v1" in content

    def test_uses_api_key_secret(self, tmp_path):
        config = _make_config()
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "secrets.ANTHROPIC_API_KEY" in content

    def test_has_checkout_step(self, tmp_path):
        config = _make_config()
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "actions/checkout@v4" in content


# ── Security review job ─────────────────────────────────────────────


class TestSecurityReview:
    def test_verify_heavy_has_security_review(self, tmp_path):
        config = _make_config(workflow="verify-heavy")
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "security-review:" in content
        assert "security auditor" in content.lower()

    def test_superpowers_has_security_review(self, tmp_path):
        config = _make_config(workflow="superpowers")
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "security-review:" in content

    def test_standard_no_security_review(self, tmp_path):
        config = _make_config(workflow="standard")
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "security-review:" not in content

    def test_speedrun_no_security_review(self, tmp_path):
        config = _make_config(workflow="speedrun")
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "security-review:" not in content

    def test_security_review_checks_common_issues(self, tmp_path):
        config = _make_config(workflow="superpowers")
        generate_github_actions(config, tmp_path)
        content = (tmp_path / ".github" / "workflows" / "claude.yml").read_text()
        assert "SQL injection" in content
        assert "XSS" in content
        assert "CSRF" in content


# ── FileTracker integration ─────────────────────────────────────────


class TestFileTracker:
    def test_with_tracker(self, tmp_path):
        from cc_rig.generators.fileops import FileTracker

        config = _make_config()
        tracker = FileTracker(tmp_path)
        files = generate_github_actions(config, tmp_path, tracker=tracker)
        assert files == [".github/workflows/claude.yml"]
        assert (tmp_path / ".github" / "workflows" / "claude.yml").exists()
        assert ".github/workflows/claude.yml" in tracker.metadata()

    def test_creates_directory_without_tracker(self, tmp_path):
        config = _make_config()
        generate_github_actions(config, tmp_path)
        assert (tmp_path / ".github" / "workflows").is_dir()
