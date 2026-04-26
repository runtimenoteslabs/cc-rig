"""Tests for addon file generator: specs template and GTD task files."""

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.addons import generate_addons
from cc_rig.generators.fileops import FileTracker


def _generate_addons(template, workflow, tmp_path, *, use_tracker=False):
    config = compute_defaults(template, workflow, project_name="test-project")
    tracker = FileTracker(tmp_path) if use_tracker else None
    files = generate_addons(config, tmp_path, tracker=tracker)
    return config, files, tracker


def _generate_addons_with_gtd(template, tmp_path, *, use_tracker=False):
    """Generate addons with GTD features explicitly enabled."""
    config = compute_defaults(template, "standard", project_name="test-project")
    config.features.gtd = True
    config.features.worktrees = True
    tracker = FileTracker(tmp_path) if use_tracker else None
    files = generate_addons(config, tmp_path, tracker=tracker)
    return config, files, tracker


# ── Specs Template ────────────────────────────────────────────────────


class TestSpecsTemplate:
    """Verify specs/TEMPLATE.md content when spec_workflow is enabled."""

    def test_generated_when_spec_workflow_enabled(self, tmp_path):
        _, files, _ = _generate_addons("fastapi", "spec-driven", tmp_path)
        assert "specs/TEMPLATE.md" in files

    def test_not_generated_when_spec_workflow_disabled(self, tmp_path):
        _, files, _ = _generate_addons("fastapi", "standard", tmp_path)
        assert "specs/TEMPLATE.md" not in files

    def test_has_summary_section(self, tmp_path):
        _generate_addons("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / "specs" / "TEMPLATE.md").read_text()
        assert "## Summary" in content

    def test_has_user_stories_section(self, tmp_path):
        _generate_addons("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / "specs" / "TEMPLATE.md").read_text()
        assert "## User Stories" in content

    def test_has_acceptance_criteria_section(self, tmp_path):
        _generate_addons("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / "specs" / "TEMPLATE.md").read_text()
        assert "## Acceptance Criteria" in content

    def test_has_task_breakdown_section(self, tmp_path):
        _generate_addons("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / "specs" / "TEMPLATE.md").read_text()
        assert "## Task Breakdown" in content

    def test_has_out_of_scope_section(self, tmp_path):
        _generate_addons("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / "specs" / "TEMPLATE.md").read_text()
        assert "## Out of Scope" in content

    def test_has_open_questions_section(self, tmp_path):
        _generate_addons("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / "specs" / "TEMPLATE.md").read_text()
        assert "## Open Questions" in content

    def test_has_user_story_format(self, tmp_path):
        _generate_addons("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / "specs" / "TEMPLATE.md").read_text()
        assert "As a" in content

    def test_has_acceptance_criteria_format(self, tmp_path):
        _generate_addons("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / "specs" / "TEMPLATE.md").read_text()
        assert "Given" in content

    def test_has_task_checkboxes(self, tmp_path):
        _generate_addons("fastapi", "spec-driven", tmp_path)
        content = (tmp_path / "specs" / "TEMPLATE.md").read_text()
        assert "- [ ] Task" in content


# ── GTD Files ─────────────────────────────────────────────────────────


class TestGtdFiles:
    """Verify GTD task file content when gtd is enabled.

    GTD files require features.gtd=True; gtd-lite now maps to the
    standard tier which does not enable gtd by default.
    """

    def test_all_three_files_generated_when_gtd_enabled(self, tmp_path):
        _, files, _ = _generate_addons_with_gtd("fastapi", tmp_path)
        assert "tasks/inbox.md" in files
        assert "tasks/todo.md" in files
        assert "tasks/someday.md" in files

    def test_no_files_when_gtd_disabled(self, tmp_path):
        _, files, _ = _generate_addons("fastapi", "standard", tmp_path)
        gtd_files = [f for f in files if f.startswith("tasks/")]
        assert gtd_files == []

    def test_inbox_starts_with_heading(self, tmp_path):
        _generate_addons_with_gtd("fastapi", tmp_path)
        content = (tmp_path / "tasks" / "inbox.md").read_text()
        assert content.startswith("# Inbox")

    def test_inbox_references_gtd_process(self, tmp_path):
        _generate_addons_with_gtd("fastapi", tmp_path)
        content = (tmp_path / "tasks" / "inbox.md").read_text()
        assert "/gtd-process" in content

    def test_inbox_has_date_format(self, tmp_path):
        _generate_addons_with_gtd("fastapi", tmp_path)
        content = (tmp_path / "tasks" / "inbox.md").read_text()
        assert "YYYY-MM-DD" in content

    def test_todo_starts_with_heading(self, tmp_path):
        _generate_addons_with_gtd("fastapi", tmp_path)
        content = (tmp_path / "tasks" / "todo.md").read_text()
        assert content.startswith("# Todo")

    def test_todo_has_next_format(self, tmp_path):
        _generate_addons_with_gtd("fastapi", tmp_path)
        content = (tmp_path / "tasks" / "todo.md").read_text()
        assert "Next:" in content

    def test_someday_starts_with_heading(self, tmp_path):
        _generate_addons_with_gtd("fastapi", tmp_path)
        content = (tmp_path / "tasks" / "someday.md").read_text()
        assert content.startswith("# Someday")

    def test_someday_mentions_weekly_review(self, tmp_path):
        _generate_addons_with_gtd("fastapi", tmp_path)
        content = (tmp_path / "tasks" / "someday.md").read_text()
        assert "weekly" in content.lower()

    def test_preexisting_files_not_overwritten(self, tmp_path):
        """User-customized GTD files must be preserved."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "inbox.md").write_text("# My Custom Inbox\n")

        _generate_addons_with_gtd("fastapi", tmp_path)

        content = (tasks_dir / "inbox.md").read_text()
        assert content == "# My Custom Inbox\n"


# ── Preserve on Clean ─────────────────────────────────────────────────


class TestPreserveOnClean:
    """Verify preserve_on_clean flag is set via FileTracker."""

    def test_specs_template_marked_preserve(self, tmp_path):
        _, _, tracker = _generate_addons("fastapi", "spec-driven", tmp_path, use_tracker=True)
        meta = tracker.metadata()
        assert meta["specs/TEMPLATE.md"].get("preserve_on_clean") is True

    def test_gtd_files_marked_preserve(self, tmp_path):
        _, _, tracker = _generate_addons_with_gtd("fastapi", tmp_path, use_tracker=True)
        meta = tracker.metadata()
        for rel in ("tasks/inbox.md", "tasks/todo.md", "tasks/someday.md"):
            assert meta[rel].get("preserve_on_clean") is True, f"{rel} missing preserve_on_clean"
