"""E2E Test Matrix for cc-rig init — 19 scenarios covering all dimensions.

Tests every template, workflow, harness level, feature flag, and flow type
at least once. Uses the Python API (compute_defaults + generate_all) for
reliable non-interactive testing.

Scenario Matrix:
  S01: FastAPI + Standard + B0 (baseline)
  S02: FastAPI + Verify-Heavy + B3 (maximum rigor)
  S03: FastAPI + GTD-Lite + B0 (GTD features)
  S04: FastAPI + Speedrun + B0 (minimal config)
  S05: NextJS + Standard + B2 (non-Python template)
  S06: Gin + Spec-Driven + B0 (Go template + specs)
  S07: Rust-CLI + Standard + B3 (Rust + autonomy)
  S08: FastAPI + Standard + B0 + Expert customization
  S09: FastAPI + Verify-Heavy + B0 + Feature mutual exclusion
  S10: Django + Speedrun + B0 (Django minimal)
  S11: Rerun — Standard → Verify-Heavy (orphan cleanup)
  S12: Clean after init (full cleanup)
  S14: Rust-Web (Axum) + Standard + B0 (Rust web template)
  S15: Rails + Standard + B0 (Ruby/Rails template)
  S16: Spring Boot + Standard + B0 (Java/Spring template)
  S17: .NET/ASP.NET + Standard + B0 (C#/ASP.NET template)
  S18: Laravel + Standard + B0 (PHP/Laravel template)
  S19: Express + Standard + B0 (TypeScript/Express template)
  S20: Phoenix + Standard + B0 (Elixir/Phoenix template)
  S21: go-std + Standard + B0 (Go stdlib template)
  S22: Generic + Standard + B0 (language-agnostic template)
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from cc_rig.clean import cleanup_files, load_manifest, run_clean
from cc_rig.config.defaults import compute_defaults
from cc_rig.config.project import HarnessConfig, ProjectConfig
from cc_rig.generators.orchestrator import generate_all
from cc_rig.skills.downloader import SkillInstallReport
from cc_rig.skills.registry import SKILL_PACKS

# ── Mock skill downloads ──────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _mock_skill_downloads():
    """Mock skill downloads to avoid network calls in E2E tests."""
    report = SkillInstallReport()
    object.__setattr__(report, "_files", [])
    with patch("cc_rig.generators.skills.download_skills", return_value=report):
        yield


# ── Helpers ───────────────────────────────────────────────────────────


def _generate(
    tmp_path: Path,
    template: str,
    workflow: str,
    *,
    harness_level: str = "none",
    name: str = "test-proj",
    skill_packs: list[str] | None = None,
) -> tuple[ProjectConfig, dict]:
    """Generate a project with optional harness level and skill packs."""
    config = compute_defaults(template, workflow, project_name=name, skill_packs=skill_packs)
    if harness_level != "none":
        config.harness = HarnessConfig(level=harness_level)
    manifest = generate_all(config, tmp_path)
    return config, manifest


def _files_on_disk(root: Path) -> set[str]:
    """Return all file paths relative to root, excluding .git/."""
    result = set()
    for p in root.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(root))
            if not rel.startswith(".git/") and rel != ".git":
                result.add(rel)
    return result


def _list_dir(root: Path, subdir: str) -> list[str]:
    """List file basenames in a subdirectory."""
    d = root / subdir
    if not d.is_dir():
        return []
    return sorted(f.name for f in d.iterdir() if f.is_file())


def _assert_no_duplicates(root: Path, subdir: str) -> None:
    """Assert no duplicate filenames in a directory."""
    names = _list_dir(root, subdir)
    dupes = [n for n in names if names.count(n) > 1]
    assert not dupes, f"Duplicate files in {subdir}: {dupes}"


def _assert_hooks_executable(root: Path) -> None:
    """Assert all .sh hook scripts are executable."""
    hooks_dir = root / ".claude" / "hooks"
    if not hooks_dir.is_dir():
        return
    for sh in hooks_dir.glob("*.sh"):
        mode = sh.stat().st_mode
        assert mode & stat.S_IXUSR, f"Hook not executable: {sh.name}"


def _assert_manifest_consistent(root: Path) -> None:
    """Assert every file in the manifest exists on disk."""
    manifest = load_manifest(root)
    assert manifest is not None, "Manifest missing"
    for f in manifest["files"]:
        assert (root / f).exists(), f"Manifest lists missing file: {f}"


def _assert_no_bak_pollution(root: Path) -> None:
    """Assert no .bak files outside the backup directory."""
    for p in root.rglob("*.bak"):
        rel = str(p.relative_to(root))
        if not rel.startswith(".cc-rig-backup/"):
            pytest.fail(f"Unexpected .bak file: {rel}")


def _read_claude_md(root: Path) -> str:
    """Read CLAUDE.md content."""
    return (root / "CLAUDE.md").read_text()


def _read_settings(root: Path) -> dict:
    """Read .claude/settings.json."""
    return json.loads((root / ".claude" / "settings.json").read_text())


# ── S01: FastAPI + Standard + B0 ─────────────────────────────────────


class TestS01FastapiStandardB0:
    """Baseline — most common path, default everything."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "fastapi", "standard")

    def test_file_count(self):
        files = self.manifest["files"]
        assert len(files) == 41, f"Expected 41 files, got {len(files)}: {sorted(files)}"

    def test_agents(self):
        agents = _list_dir(self.root, ".claude/agents")
        expected = [
            "architect.md",
            "code-reviewer.md",
            "explorer.md",
            "refactorer.md",
            "test-writer.md",
        ]
        assert agents == expected

    def test_commands(self):
        commands = _list_dir(self.root, ".claude/commands")
        expected = [
            "assumptions.md",
            "fix-issue.md",
            "learn.md",
            "plan.md",
            "refactor.md",
            "remember.md",
            "research.md",
            "review.md",
            "test.md",
        ]
        assert commands == expected

    def test_hooks(self):
        hooks = _list_dir(self.root, ".claude/hooks")
        expected = [
            "block-env.sh",
            "block-main.sh",
            "block-rm-rf.sh",
            "format.sh",
            "lint.sh",
            "memory-precompact.sh",
            "session-context.sh",
            "stop-validator.sh",
            "typecheck.sh",
        ]
        assert hooks == expected

    def test_memory_files(self):
        mem_files = _list_dir(self.root, "memory")
        assert "decisions.md" in mem_files
        assert "patterns.md" in mem_files
        assert "gotchas.md" in mem_files
        assert "people.md" in mem_files
        assert "session-log.md" in mem_files
        assert "MEMORY-README.md" in mem_files
        assert len(mem_files) == 6

    def test_no_specs(self):
        assert not (self.root / "specs").exists()

    def test_no_tasks(self):
        assert not (self.root / "tasks").exists()

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")

    def test_no_duplicate_skills(self):
        skills = list((self.root / ".claude" / "skills").rglob("SKILL.md"))
        names = [s.parent.name for s in skills]
        assert len(names) == len(set(names)), f"Duplicate skills: {names}"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_bak_pollution(self):
        _assert_no_bak_pollution(self.root)

    def test_claude_md_has_memory_section(self):
        content = _read_claude_md(self.root)
        assert "memory" in content.lower()

    def test_claude_md_has_fastapi_reference(self):
        content = _read_claude_md(self.root)
        assert "fastapi" in content.lower()

    def test_mcp_json_present(self):
        assert (self.root / ".mcp.json").exists()

    def test_cc_rig_json_present(self):
        assert (self.root / ".cc-rig.json").exists()

    def test_settings_permissions_permissive(self):
        settings = _read_settings(self.root)
        allow = settings["permissions"]["allow"]
        assert "Bash" in allow
        assert "Task" in allow

    def test_agent_docs_present(self):
        docs = _list_dir(self.root, "agent_docs")
        assert "architecture.md" in docs
        assert "conventions.md" in docs
        assert "testing.md" in docs
        assert "deployment.md" in docs
        assert "cache-friendly-workflow.md" in docs
        assert len(docs) == 5

    def test_skills_present(self):
        skills_dir = self.root / ".claude" / "skills"
        assert (skills_dir / "project-patterns" / "SKILL.md").exists()
        # tdd/debug are only generated as fallbacks for speedrun or failed downloads
        assert not (skills_dir / "deployment-checklist" / "SKILL.md").exists()

    def test_no_recommended_skills_doc(self):
        """recommended-skills.md is no longer generated (skills auto-installed)."""
        assert not (self.root / "docs" / "recommended-skills.md").exists()

    def test_no_harness_files(self):
        assert not (self.root / "loop.sh").exists()
        assert not (self.root / "PROMPT.md").exists()
        assert not (self.root / ".claude" / "harness-config.json").exists()

    def test_claude_local_md_present(self):
        assert (self.root / "CLAUDE.local.md").exists()
        content = (self.root / "CLAUDE.local.md").read_text()
        assert "Personal Preferences" in content

    def test_agent_docs_uses_at_imports(self):
        content = _read_claude_md(self.root)
        assert "@agent_docs/architecture.md" in content
        assert "@agent_docs/conventions.md" in content

    def test_memory_section_explains_both_systems(self):
        content = _read_claude_md(self.root)
        assert "Auto-memory" in content
        assert "Team memory" in content

    def test_session_context_says_team_memory(self):
        content = (self.root / ".claude" / "hooks" / "session-context.sh").read_text()
        assert "Team memory" in content


# ── S02: FastAPI + Verify-Heavy + B3 ─────────────────────────────────


class TestS02FastapiVerifyHeavyB3:
    """Maximum rigor — all agents, all commands, autonomy harness."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(
            tmp_path, "fastapi", "verify-heavy", harness_level="autonomy"
        )

    def test_agents(self):
        agents = _list_dir(self.root, ".claude/agents")
        # 12 from workflow + parallel-worker auto-added = 13
        assert len(agents) == 13, f"Expected 13 agents, got {len(agents)}: {agents}"
        assert "security-auditor.md" in agents
        assert "doc-writer.md" in agents
        assert "techdebt-hunter.md" in agents
        assert "db-reader.md" in agents
        assert "pm-spec.md" in agents
        assert "implementer.md" in agents
        assert "parallel-worker.md" in agents

    def test_commands_no_gtd(self):
        commands = _list_dir(self.root, ".claude/commands")
        # gtd=false, so GTD commands stripped
        assert "gtd-capture.md" not in commands
        assert "gtd-process.md" not in commands
        assert "daily-plan.md" not in commands

    def test_commands_spec_present(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "spec-create.md" in commands
        assert "spec-execute.md" in commands

    def test_commands_worktree_present(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "worktree.md" in commands

    def test_command_count(self):
        commands = _list_dir(self.root, ".claude/commands")
        # 19 - 3 gtd commands = 16
        assert len(commands) == 16, f"Expected 16 commands, got {len(commands)}: {commands}"

    def test_memory_present(self):
        assert (self.root / "memory" / "decisions.md").exists()

    def test_specs_present(self):
        assert (self.root / "specs" / "TEMPLATE.md").exists()

    def test_no_gtd_tasks(self):
        # tasks/inbox.md and tasks/someday.md should NOT exist (gtd=false)
        assert not (self.root / "tasks" / "inbox.md").exists()
        assert not (self.root / "tasks" / "someday.md").exists()

    def test_harness_b1_files(self):
        assert (self.root / "tasks" / "todo.md").exists()
        assert (self.root / "agent_docs" / "harness.md").exists()

    def test_harness_b2_files(self):
        content = (self.root / "agent_docs" / "harness.md").read_text()
        assert "Verification Gates" in content
        assert (self.root / ".claude" / "hooks" / "init-sh.sh").exists()

    def test_harness_b3_files(self):
        assert (self.root / "PROMPT.md").exists()
        assert (self.root / "claude-progress.txt").exists()
        assert (self.root / "loop.sh").exists()
        assert (self.root / ".claude" / "harness-config.json").exists()
        content = (self.root / "agent_docs" / "harness.md").read_text()
        assert "Autonomy Loop" in content

    def test_loop_sh_executable(self):
        mode = (self.root / "loop.sh").stat().st_mode
        assert mode & stat.S_IXUSR

    def test_harness_config_json(self):
        data = json.loads((self.root / ".claude" / "harness-config.json").read_text())
        assert data["harness_level"] == "autonomy"
        assert data["max_iterations"] == 20

    def test_harness_hooks(self):
        hooks = _list_dir(self.root, ".claude/hooks")
        assert "budget-reminder.sh" in hooks
        assert "session-tasks.sh" in hooks
        assert "commit-gate.sh" in hooks

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)


# ── S03: FastAPI + GTD-Lite + B0 ─────────────────────────────────────


class TestS03FastapiGtdLiteB0:
    """GTD feature path + no harness."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "fastapi", "gtd-lite")

    def test_agents(self):
        agents = _list_dir(self.root, ".claude/agents")
        assert len(agents) == 8, f"Expected 8 agents, got {len(agents)}: {agents}"
        assert "parallel-worker.md" in agents

    def test_gtd_commands_present(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "gtd-capture.md" in commands
        assert "gtd-process.md" in commands
        assert "daily-plan.md" in commands

    def test_no_spec_commands(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "spec-create.md" not in commands
        assert "spec-execute.md" not in commands

    def test_worktree_command_present(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "worktree.md" in commands

    def test_command_count(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert len(commands) == 13, f"Expected 13 commands, got {len(commands)}: {commands}"

    def test_gtd_task_files(self):
        assert (self.root / "tasks" / "inbox.md").exists()
        assert (self.root / "tasks" / "todo.md").exists()
        assert (self.root / "tasks" / "someday.md").exists()

    def test_memory_present(self):
        assert (self.root / "memory" / "decisions.md").exists()

    def test_no_specs(self):
        assert not (self.root / "specs").exists()

    def test_no_harness_files(self):
        assert not (self.root / "loop.sh").exists()
        assert not (self.root / "PROMPT.md").exists()

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)


# ── S04: FastAPI + Speedrun + B0 ─────────────────────────────────────


class TestS04FastapiSpeedrunB0:
    """Minimal config — fewest files, no features."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "fastapi", "speedrun")

    def test_file_count(self):
        files = self.manifest["files"]
        assert len(files) == 29, f"Expected 29 files, got {len(files)}: {sorted(files)}"

    def test_agents(self):
        agents = _list_dir(self.root, ".claude/agents")
        expected = ["code-reviewer.md", "explorer.md", "test-writer.md"]
        assert agents == expected

    def test_commands(self):
        commands = _list_dir(self.root, ".claude/commands")
        expected = [
            "assumptions.md",
            "fix-issue.md",
            "learn.md",
            "plan.md",
            "review.md",
            "test.md",
        ]
        assert commands == expected

    def test_no_remember_command(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "remember.md" not in commands

    def test_no_refactor_command(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "refactor.md" not in commands

    def test_hooks_minimal(self):
        hooks = _list_dir(self.root, ".claude/hooks")
        expected = [
            "block-env.sh",
            "block-main.sh",
            "block-rm-rf.sh",
            "format.sh",
            "lint.sh",
            "session-context.sh",
        ]
        assert hooks == expected

    def test_no_typecheck_hook(self):
        hooks = _list_dir(self.root, ".claude/hooks")
        assert "typecheck.sh" not in hooks

    def test_no_memory(self):
        assert not (self.root / "memory").exists()

    def test_no_specs(self):
        assert not (self.root / "specs").exists()

    def test_no_tasks(self):
        assert not (self.root / "tasks").exists()

    def test_claude_md_no_memory_section(self):
        content = _read_claude_md(self.root)
        # Memory section header should not be present
        assert "## Memory" not in content

    def test_settings_permissions_default(self):
        settings = _read_settings(self.root)
        allow = settings["permissions"]["allow"]
        assert "Bash" not in allow
        assert "Read" in allow

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)


# ── S05: NextJS + Standard + B2 ──────────────────────────────────────


class TestS05NextjsStandardB2:
    """Non-Python template — verify template-specific hooks/commands."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(
            tmp_path, "nextjs", "standard", harness_level="standard"
        )

    def test_format_hook_uses_prettier(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "prettier" in content.lower()

    def test_lint_hook_uses_npm(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "npm run lint" in content

    def test_typecheck_hook_uses_tsc(self):
        content = (self.root / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "tsc" in content

    def test_claude_md_references_typescript(self):
        content = _read_claude_md(self.root)
        assert "typescript" in content.lower()

    def test_claude_md_references_nextjs(self):
        content = _read_claude_md(self.root)
        assert "nextjs" in content.lower() or "next" in content.lower()

    def test_harness_b1_files(self):
        assert (self.root / "tasks" / "todo.md").exists()
        assert (self.root / "agent_docs" / "harness.md").exists()

    def test_harness_b2_files(self):
        content = (self.root / "agent_docs" / "harness.md").read_text()
        assert "Verification Gates" in content
        assert (self.root / ".claude" / "hooks" / "init-sh.sh").exists()

    def test_no_b3_files(self):
        assert not (self.root / "loop.sh").exists()
        assert not (self.root / "PROMPT.md").exists()
        assert not (self.root / ".claude" / "harness-config.json").exists()

    def test_harness_hooks(self):
        hooks = _list_dir(self.root, ".claude/hooks")
        assert "budget-reminder.sh" in hooks
        assert "session-tasks.sh" in hooks
        assert "commit-gate.sh" in hooks

    def test_memory_present(self):
        assert (self.root / "memory" / "decisions.md").exists()

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S06: Gin + Spec-Driven + B0 ──────────────────────────────────────


class TestS06GinSpecDrivenB0:
    """Go template + spec workflow features."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "gin", "spec-driven")

    def test_format_hook_uses_go(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "goimports" in content

    def test_lint_hook_uses_golangci(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "golangci-lint" in content

    def test_typecheck_hook_uses_go_vet(self):
        content = (self.root / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "go vet" in content

    def test_specs_template_present(self):
        assert (self.root / "specs" / "TEMPLATE.md").exists()

    def test_spec_commands_present(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "spec-create.md" in commands
        assert "spec-execute.md" in commands

    def test_no_gtd_commands(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "gtd-capture.md" not in commands
        assert "gtd-process.md" not in commands
        assert "daily-plan.md" not in commands

    def test_worktree_command_present(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "worktree.md" in commands

    def test_agents_include_spec_agents(self):
        agents = _list_dir(self.root, ".claude/agents")
        assert "pm-spec.md" in agents
        assert "implementer.md" in agents
        assert "parallel-worker.md" in agents
        # 8 from workflow + parallel-worker = 9
        assert len(agents) == 9, f"Expected 9 agents, got {len(agents)}: {agents}"

    def test_claude_md_references_go_gin(self):
        content = _read_claude_md(self.root)
        assert "gin" in content.lower()
        assert "go" in content.lower()

    def test_memory_present(self):
        assert (self.root / "memory" / "decisions.md").exists()

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)


# ── S07: Rust-CLI + Standard + B3 ────────────────────────────────────


class TestS07RustCliStandardB3:
    """Rust template + autonomy loop."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(
            tmp_path, "rust-cli", "standard", harness_level="autonomy"
        )

    def test_format_hook_uses_cargo_fmt(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "cargo fmt" in content

    def test_lint_hook_uses_cargo_clippy(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "cargo clippy" in content

    def test_typecheck_hook_uses_cargo_check(self):
        content = (self.root / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "cargo check" in content

    def test_loop_sh_present_and_executable(self):
        loop = self.root / "loop.sh"
        assert loop.exists()
        assert loop.stat().st_mode & stat.S_IXUSR

    def test_prompt_md_present(self):
        assert (self.root / "PROMPT.md").exists()

    def test_progress_file_present(self):
        assert (self.root / "claude-progress.txt").exists()

    def test_harness_md_has_autonomy(self):
        content = (self.root / "agent_docs" / "harness.md").read_text()
        assert "Autonomy Loop" in content

    def test_harness_config(self):
        path = self.root / ".claude" / "harness-config.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["harness_level"] == "autonomy"

    def test_claude_md_references_rust(self):
        content = _read_claude_md(self.root)
        assert "rust" in content.lower()

    def test_stop_validator_uses_cargo_test(self):
        content = (self.root / ".claude" / "hooks" / "stop-validator.sh").read_text()
        assert "cargo test" in content

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S08: FastAPI + Standard + Expert Customization ────────────────────


class TestS08ExpertCustomization:
    """Expert mode — remove agents, add features via modified config."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        # Start from standard defaults, then customize
        config = compute_defaults("fastapi", "standard", project_name="expert-proj")
        # Expert: remove architect, refactorer
        config.agents = [a for a in config.agents if a not in ("architect", "refactorer")]
        # Expert: enable spec_workflow
        config.features.spec_workflow = True
        # Auto-add spec components (simulating compute_defaults phase 1)
        if "pm-spec" not in config.agents:
            config.agents.append("pm-spec")
        if "implementer" not in config.agents:
            config.agents.append("implementer")
        if "spec-create" not in config.commands:
            config.commands.append("spec-create")
        if "spec-execute" not in config.commands:
            config.commands.append("spec-execute")
        self.manifest = generate_all(config, tmp_path)
        self.config = config

    def test_agents_no_architect_refactorer(self):
        agents = _list_dir(self.root, ".claude/agents")
        assert "architect.md" not in agents
        assert "refactorer.md" not in agents

    def test_agents_spec_agents_added(self):
        agents = _list_dir(self.root, ".claude/agents")
        assert "pm-spec.md" in agents
        assert "implementer.md" in agents

    def test_agent_count(self):
        agents = _list_dir(self.root, ".claude/agents")
        # code-reviewer, test-writer, explorer + pm-spec, implementer = 5
        assert len(agents) == 5, f"Expected 5 agents, got {len(agents)}: {agents}"

    def test_spec_commands_present(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert "spec-create.md" in commands
        assert "spec-execute.md" in commands

    def test_specs_template_present(self):
        assert (self.root / "specs" / "TEMPLATE.md").exists()

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)


# ── S09: FastAPI + Verify-Heavy + Feature Mutual Exclusion ────────────


class TestS09FeatureMutualExclusion:
    """Verify spec_workflow and gtd mutual exclusion behavior."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        # Start from verify-heavy (spec_workflow=true, gtd=false)
        config = compute_defaults("fastapi", "verify-heavy", project_name="mutex-proj")
        self.config_spec = config
        # Verify the defaults
        assert config.features.spec_workflow is True
        assert config.features.gtd is False

    def test_spec_workflow_default_on(self):
        """Verify-heavy has spec_workflow=true by default."""
        assert self.config_spec.features.spec_workflow is True

    def test_gtd_default_off(self):
        """Verify-heavy has gtd=false by default."""
        assert self.config_spec.features.gtd is False

    def test_toggling_gtd_on_produces_correct_commands(self, tmp_path):
        """If user enables GTD and disables spec, commands update correctly."""
        config = compute_defaults("fastapi", "verify-heavy", project_name="mutex2")
        # Simulate expert toggle: turn off spec, turn on gtd
        config.features.spec_workflow = False
        config.features.gtd = True
        # Strip spec commands, add GTD commands
        config.commands = [c for c in config.commands if c not in ("spec-create", "spec-execute")]
        for cmd in ("gtd-capture", "gtd-process", "daily-plan"):
            if cmd not in config.commands:
                config.commands.append(cmd)

        root = tmp_path / "mutex2"
        root.mkdir()
        generate_all(config, root)

        commands = _list_dir(root, ".claude/commands")
        assert "gtd-capture.md" in commands
        assert "gtd-process.md" in commands
        assert "daily-plan.md" in commands
        assert "spec-create.md" not in commands
        assert "spec-execute.md" not in commands

        # GTD task files should be generated
        assert (root / "tasks" / "inbox.md").exists()
        assert (root / "tasks" / "todo.md").exists()
        assert (root / "tasks" / "someday.md").exists()

        # specs/ should NOT be generated
        assert not (root / "specs").exists()


# ── S10: Django + Speedrun + B0 ──────────────────────────────────────


class TestS10DjangoSpeedrunB0:
    """Different Python template + minimal config."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "django", "speedrun")

    def test_claude_md_references_django(self):
        content = _read_claude_md(self.root)
        assert "django" in content.lower()

    def test_claude_md_references_python(self):
        content = _read_claude_md(self.root)
        assert "python" in content.lower()

    def test_test_cmd_uses_manage_py(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert "manage.py test" in data["test_cmd"]

    def test_minimal_agents(self):
        agents = _list_dir(self.root, ".claude/agents")
        assert len(agents) == 3

    def test_minimal_commands(self):
        commands = _list_dir(self.root, ".claude/commands")
        assert len(commands) == 6

    def test_no_memory(self):
        assert not (self.root / "memory").exists()

    def test_no_specs(self):
        assert not (self.root / "specs").exists()

    def test_no_tasks(self):
        assert not (self.root / "tasks").exists()

    def test_default_permissions(self):
        settings = _read_settings(self.root)
        allow = settings["permissions"]["allow"]
        assert "Bash" not in allow

    def test_file_count(self):
        files = self.manifest["files"]
        assert len(files) == 29, f"Expected 29 files, got {len(files)}: {sorted(files)}"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)


# ── S11: Rerun — Standard → Verify-Heavy ─────────────────────────────


class TestS11Rerun:
    """Re-init over existing config — verify orphan cleanup."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        # Step 1: Generate with standard workflow
        self.config_old, self.manifest_old = _generate(tmp_path, "fastapi", "standard")
        self.old_files = set(self.manifest_old["files"])

    def test_rerun_with_different_workflow(self):
        # Step 2: Re-generate with verify-heavy (different workflow)
        config_new = compute_defaults("fastapi", "verify-heavy", project_name="rerun-proj")
        manifest_new = generate_all(config_new, self.root)
        new_files = set(manifest_new["files"])

        # Orphan cleanup happens during run_generation, but here we test
        # generate_all which overwrites files. Verify the new manifest.
        assert len(new_files) > len(self.old_files), "verify-heavy should produce more files"

        # Verify new agents exist
        agents = _list_dir(self.root, ".claude/agents")
        assert "security-auditor.md" in agents
        assert "doc-writer.md" in agents

        # Verify new commands exist
        commands = _list_dir(self.root, ".claude/commands")
        assert "security.md" in commands
        assert "document.md" in commands

    def test_orphan_cleanup(self):
        """Simulate orphan cleanup logic from run_generation."""
        # Generate new config (verify-heavy)
        config_new = compute_defaults("fastapi", "verify-heavy", project_name="rerun-proj")
        manifest_new = generate_all(config_new, self.root)

        # Compute orphans: files in old manifest but not in new
        orphans = sorted(set(self.manifest_old["files"]) - set(manifest_new["files"]))
        old_metadata = self.manifest_old.get("file_metadata", {})
        result = cleanup_files(self.root, orphans, old_metadata)

        # Any orphans should have been cleaned up
        for f in result.removed:
            assert not (self.root / f).exists(), f"Orphan not removed: {f}"

    def test_no_duplicate_files_after_rerun(self):
        config_new = compute_defaults("fastapi", "verify-heavy", project_name="rerun-proj")
        generate_all(config_new, self.root)

        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")

    def test_manifest_reflects_new_config(self):
        config_new = compute_defaults("fastapi", "verify-heavy", project_name="rerun-proj")
        manifest_new = generate_all(config_new, self.root)

        assert manifest_new["workflow_preset"] == "verify-heavy"
        _assert_manifest_consistent(self.root)


# ── S12: Clean After Init ────────────────────────────────────────────


class TestS12Clean:
    """Verify cc-rig clean removes everything properly."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        # Generate largest config: verify-heavy + B3
        self.config, self.manifest = _generate(
            tmp_path, "fastapi", "verify-heavy", harness_level="autonomy"
        )
        # Create a dummy pre-existing file to verify it's preserved
        (tmp_path / "README.md").write_text("# My Project\n")

    def test_clean_removes_generated_files(self):
        result = run_clean(self.root, force=True)

        assert result.total_removed > 0, "No files removed"

        # Core generated files should be gone
        assert not (self.root / "CLAUDE.md").exists()
        assert not (self.root / ".mcp.json").exists()
        assert not (self.root / "loop.sh").exists()
        assert not (self.root / "PROMPT.md").exists()

    def test_clean_removes_empty_dirs(self):
        run_clean(self.root, force=True)

        # Managed directories should be removed if empty
        for d in [".claude", "memory", "agent_docs", "docs", "specs", "tasks"]:
            path = self.root / d
            if path.exists():
                # Should only exist if it has non-generated files
                assert any(path.iterdir()), f"Empty managed dir not cleaned: {d}"

    def test_clean_preserves_readme(self):
        run_clean(self.root, force=True)
        assert (self.root / "README.md").exists()
        assert (self.root / "README.md").read_text() == "# My Project\n"

    def test_clean_removes_backup_dir(self):
        run_clean(self.root, force=True)
        assert not (self.root / ".cc-rig-backup").exists()

    def test_clean_removes_cc_rig_json(self):
        run_clean(self.root, force=True)
        assert not (self.root / ".cc-rig.json").exists()

    def test_manifest_gone_after_clean(self):
        run_clean(self.root, force=True)
        assert load_manifest(self.root) is None


# ── Cross-cutting: All templates produce valid output ─────────────────


TEMPLATES = [
    "generic",
    "fastapi",
    "django",
    "flask",
    "gin",
    "echo",
    "nextjs",
    "rust-cli",
    "rust-web",
    "rails",
    "spring",
    "dotnet",
    "laravel",
    "express",
    "phoenix",
    "go-std",
]
WORKFLOWS = ["speedrun", "standard", "spec-driven", "gtd-lite", "verify-heavy"]


@pytest.mark.parametrize("template", TEMPLATES)
def test_every_template_generates_successfully(tmp_path, template):
    """Every template produces valid output with standard workflow."""
    config, manifest = _generate(tmp_path, template, "standard")
    assert len(manifest["files"]) > 20
    _assert_manifest_consistent(tmp_path)
    _assert_hooks_executable(tmp_path)
    _assert_no_duplicates(tmp_path, ".claude/commands")
    _assert_no_duplicates(tmp_path, ".claude/agents")


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_every_workflow_generates_successfully(tmp_path, workflow):
    """Every workflow produces valid output with fastapi template."""
    config, manifest = _generate(tmp_path, "fastapi", workflow)
    assert len(manifest["files"]) > 20
    _assert_manifest_consistent(tmp_path)
    _assert_hooks_executable(tmp_path)
    _assert_no_duplicates(tmp_path, ".claude/commands")
    _assert_no_duplicates(tmp_path, ".claude/agents")


@pytest.mark.parametrize("template", TEMPLATES)
@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_full_cross_product(tmp_path, template, workflow):
    """Every template x workflow combination generates without error."""
    config, manifest = _generate(tmp_path, template, workflow)
    assert len(manifest["files"]) > 0
    _assert_manifest_consistent(tmp_path)


@pytest.mark.parametrize(
    "level",
    ["none", "lite", "standard", "autonomy"],
)
def test_every_harness_level(tmp_path, level):
    """Every harness level generates appropriate files."""
    config, manifest = _generate(tmp_path, "fastapi", "standard", harness_level=level)

    if level == "none":
        assert not (tmp_path / "tasks" / "todo.md").exists()
        assert not (tmp_path / "loop.sh").exists()
    elif level == "lite":
        assert (tmp_path / "tasks" / "todo.md").exists()
        assert (tmp_path / "agent_docs" / "harness.md").exists()
        assert not (tmp_path / ".claude" / "hooks" / "init-sh.sh").exists()
    elif level == "standard":
        assert (tmp_path / "tasks" / "todo.md").exists()
        assert (tmp_path / "agent_docs" / "harness.md").exists()
        harness_content = (tmp_path / "agent_docs" / "harness.md").read_text()
        assert "Verification Gates" in harness_content
        assert (tmp_path / ".claude" / "hooks" / "init-sh.sh").exists()
        assert not (tmp_path / "loop.sh").exists()
    elif level == "autonomy":
        assert (tmp_path / "tasks" / "todo.md").exists()
        assert (tmp_path / "agent_docs" / "harness.md").exists()
        assert (tmp_path / ".claude" / "hooks" / "init-sh.sh").exists()
        assert (tmp_path / "loop.sh").exists()
        assert (tmp_path / "PROMPT.md").exists()
        assert (tmp_path / "claude-progress.txt").exists()
        assert (tmp_path / ".claude" / "harness-config.json").exists()

    _assert_manifest_consistent(tmp_path)


# ── Feature flag isolation tests ──────────────────────────────────────


def test_memory_false_produces_no_memory_files(tmp_path):
    """When memory=false, no memory files or hooks are generated."""
    config, manifest = _generate(tmp_path, "fastapi", "speedrun")
    assert not (tmp_path / "memory").exists()
    assert "remember.md" not in [f.name for f in (tmp_path / ".claude" / "commands").iterdir()]


def test_memory_true_produces_all_memory_files(tmp_path):
    """When memory=true, all 6 memory files are generated."""
    config, manifest = _generate(tmp_path, "fastapi", "standard")
    mem_files = _list_dir(tmp_path, "memory")
    assert len(mem_files) == 6


def test_spec_workflow_produces_spec_files(tmp_path):
    """When spec_workflow=true, spec template and commands exist."""
    config, manifest = _generate(tmp_path, "fastapi", "spec-driven")
    assert (tmp_path / "specs" / "TEMPLATE.md").exists()
    commands = _list_dir(tmp_path, ".claude/commands")
    assert "spec-create.md" in commands
    assert "spec-execute.md" in commands


def test_gtd_produces_task_files(tmp_path):
    """When gtd=true, GTD task files and commands exist."""
    config, manifest = _generate(tmp_path, "fastapi", "gtd-lite")
    assert (tmp_path / "tasks" / "inbox.md").exists()
    assert (tmp_path / "tasks" / "todo.md").exists()
    assert (tmp_path / "tasks" / "someday.md").exists()
    commands = _list_dir(tmp_path, ".claude/commands")
    assert "gtd-capture.md" in commands


def test_worktrees_produces_worktree_command(tmp_path):
    """When worktrees=true, worktree command and parallel-worker agent exist."""
    config, manifest = _generate(tmp_path, "fastapi", "spec-driven")
    assert config.features.worktrees is True
    commands = _list_dir(tmp_path, ".claude/commands")
    assert "worktree.md" in commands
    agents = _list_dir(tmp_path, ".claude/agents")
    assert "parallel-worker.md" in agents


# ── S14: Rust-Web (Axum) + Standard + B0 ──────────────────────────────


class TestS14RustWebStandardB0:
    """Rust web (Axum) template — verifies second Rust template coexists."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "rust-web", "standard")

    def test_claude_md_references_axum(self):
        content = _read_claude_md(self.root)
        assert "axum" in content.lower()

    def test_claude_md_references_rust(self):
        content = _read_claude_md(self.root)
        assert "rust" in content.lower()

    def test_format_hook_uses_cargo_fmt(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "cargo fmt" in content

    def test_lint_hook_uses_clippy(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "clippy" in content

    def test_typecheck_hook_uses_cargo_check(self):
        content = (self.root / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "cargo check" in content

    def test_agent_docs_contain_axum(self):
        content = (self.root / "agent_docs" / "architecture.md").read_text()
        assert "axum" in content.lower() or "router" in content.lower()

    def test_project_type_is_api(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["project_type"] == "api"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S15: Rails + Standard + B0 ───────────────────────────────────────


class TestS15RailsStandardB0:
    """Ruby/Rails template — verifies new language + no typecheck hook."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "rails", "standard")

    def test_claude_md_references_rails(self):
        content = _read_claude_md(self.root)
        assert "rails" in content.lower()

    def test_claude_md_references_ruby(self):
        content = _read_claude_md(self.root)
        assert "ruby" in content.lower()

    def test_format_hook_uses_rubocop(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "rubocop" in content

    def test_lint_hook_uses_rubocop(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "rubocop" in content

    def test_no_typecheck_hook(self):
        """Rails has no typecheck command — hook should be absent."""
        assert not (self.root / ".claude" / "hooks" / "typecheck.sh").exists()

    def test_agent_docs_contain_rails(self):
        content = (self.root / "agent_docs" / "architecture.md").read_text()
        assert "rails" in content.lower() or "mvc" in content.lower()

    def test_project_type_is_web_fullstack(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["project_type"] == "web_fullstack"

    def test_test_dir_is_singular(self):
        """Rails convention: test/ not tests/."""
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["test_dir"] == "test"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S16: Spring Boot + Standard + B0 ─────────────────────────────────


class TestS16SpringStandardB0:
    """Java/Spring Boot template — verifies new language + no typecheck hook."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "spring", "standard")

    def test_claude_md_references_spring(self):
        content = _read_claude_md(self.root)
        assert "spring" in content.lower()

    def test_claude_md_references_java(self):
        content = _read_claude_md(self.root)
        assert "java" in content.lower()

    def test_format_hook_uses_spotless(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "spotless" in content

    def test_lint_hook_uses_checkstyle(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "checkstyle" in content

    def test_no_typecheck_hook(self):
        """Spring Boot (compiled) has no typecheck command — hook should be absent."""
        assert not (self.root / ".claude" / "hooks" / "typecheck.sh").exists()

    def test_agent_docs_contain_spring(self):
        content = (self.root / "agent_docs" / "architecture.md").read_text()
        assert "spring" in content.lower() or "controller" in content.lower()

    def test_project_type_is_api(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["project_type"] == "api"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S17: .NET/ASP.NET + Standard + B0 ────────────────────────────────


class TestS17DotnetStandardB0:
    """C#/ASP.NET Core template — verifies new language + no typecheck hook."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "dotnet", "standard")

    def test_claude_md_references_aspnet(self):
        content = _read_claude_md(self.root)
        assert "asp.net" in content.lower() or "aspnet" in content.lower()

    def test_claude_md_references_csharp(self):
        content = _read_claude_md(self.root)
        assert "c#" in content.lower() or "csharp" in content.lower()

    def test_format_hook_uses_dotnet_format(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "dotnet format" in content

    def test_lint_hook_uses_dotnet_format(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "dotnet format" in content

    def test_no_typecheck_hook(self):
        """ASP.NET (compiled) has no typecheck command — hook should be absent."""
        assert not (self.root / ".claude" / "hooks" / "typecheck.sh").exists()

    def test_agent_docs_contain_aspnet(self):
        content = (self.root / "agent_docs" / "architecture.md").read_text()
        assert "asp.net" in content.lower() or "controller" in content.lower()

    def test_project_type_is_api(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["project_type"] == "api"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S18: Laravel + Standard + B0 ──────────────────────────────────────


class TestS18LaravelStandardB0:
    """PHP/Laravel template — verifies new language + no typecheck hook."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "laravel", "standard")

    def test_claude_md_references_laravel(self):
        content = _read_claude_md(self.root)
        assert "laravel" in content.lower()

    def test_claude_md_references_php(self):
        content = _read_claude_md(self.root)
        assert "php" in content.lower()

    def test_format_hook_uses_pint(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "pint" in content

    def test_lint_hook_uses_pint(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "pint" in content

    def test_no_typecheck_hook(self):
        """Laravel (PHP) has no typecheck command — hook should be absent."""
        assert not (self.root / ".claude" / "hooks" / "typecheck.sh").exists()

    def test_agent_docs_contain_laravel(self):
        content = (self.root / "agent_docs" / "architecture.md").read_text()
        assert "laravel" in content.lower() or "eloquent" in content.lower()

    def test_project_type_is_web_fullstack(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["project_type"] == "web_fullstack"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S19: Express + Standard + B0 ─────────────────────────────────────


class TestS19ExpressStandardB0:
    """TypeScript/Express template — verifies Express with tsc typecheck."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "express", "standard")

    def test_claude_md_references_express(self):
        content = _read_claude_md(self.root)
        assert "express" in content.lower()

    def test_claude_md_references_typescript(self):
        content = _read_claude_md(self.root)
        assert "typescript" in content.lower()

    def test_format_hook_uses_prettier(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "prettier" in content

    def test_lint_hook_uses_npm(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "npm run lint" in content

    def test_typecheck_hook_uses_tsc(self):
        content = (self.root / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "tsc" in content

    def test_agent_docs_contain_express(self):
        content = (self.root / "agent_docs" / "architecture.md").read_text()
        assert "express" in content.lower() or "router" in content.lower()

    def test_project_type_is_api(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["project_type"] == "api"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S20: Phoenix + Standard + B0 ─────────────────────────────────────


class TestS20PhoenixStandardB0:
    """Elixir/Phoenix template — verifies new language + no typecheck hook."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "phoenix", "standard")

    def test_claude_md_references_phoenix(self):
        content = _read_claude_md(self.root)
        assert "phoenix" in content.lower()

    def test_claude_md_references_elixir(self):
        content = _read_claude_md(self.root)
        assert "elixir" in content.lower()

    def test_format_hook_uses_mix_format(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "mix format" in content

    def test_lint_hook_uses_credo(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "credo" in content

    def test_no_typecheck_hook(self):
        """Phoenix (Elixir) has no typecheck command — hook should be absent."""
        assert not (self.root / ".claude" / "hooks" / "typecheck.sh").exists()

    def test_agent_docs_contain_phoenix(self):
        content = (self.root / "agent_docs" / "architecture.md").read_text()
        assert "phoenix" in content.lower() or "context" in content.lower()

    def test_project_type_is_web_fullstack(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["project_type"] == "web_fullstack"

    def test_test_dir_is_singular(self):
        """Elixir/Phoenix convention: test/ not tests/."""
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["test_dir"] == "test"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S21: go-std + Standard + B0 ──────────────────────────────────────


class TestS21GoStdStandardB0:
    """Go stdlib template — verifies Go without framework."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "go-std", "standard")

    def test_claude_md_references_go(self):
        content = _read_claude_md(self.root)
        assert "go" in content.lower()

    def test_claude_md_references_net_http(self):
        content = _read_claude_md(self.root)
        assert "net/http" in content.lower() or "stdlib" in content.lower()

    def test_format_hook_uses_goimports(self):
        content = (self.root / ".claude" / "hooks" / "format.sh").read_text()
        assert "goimports" in content

    def test_lint_hook_uses_golangci(self):
        content = (self.root / ".claude" / "hooks" / "lint.sh").read_text()
        assert "golangci-lint" in content

    def test_typecheck_hook_uses_go_vet(self):
        content = (self.root / ".claude" / "hooks" / "typecheck.sh").read_text()
        assert "go vet" in content

    def test_agent_docs_contain_net_http(self):
        content = (self.root / "agent_docs" / "architecture.md").read_text()
        assert "net/http" in content.lower() or "servemux" in content.lower()

    def test_project_type_is_api(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["project_type"] == "api"

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S22: Generic + Standard + B0 ─────────────────────────────────────


class TestS22GenericStandardB0:
    """Generic template — language-agnostic project."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.root = tmp_path
        self.config, self.manifest = _generate(tmp_path, "generic", "standard")

    def test_claude_md_has_project_rules(self):
        content = _read_claude_md(self.root)
        assert "Project Rules" in content

    def test_claude_md_no_empty_commands(self):
        """No empty command entries like '- **Test**: ``'."""
        content = _read_claude_md(self.root)
        assert "**: ``" not in content

    def test_commands_section_is_empty(self):
        """Generic has no tool commands — Commands section has no entries."""
        content = _read_claude_md(self.root)
        # Commands section exists but has no bullet points
        lines = content.split("\n")
        in_commands = False
        cmd_lines = []
        for line in lines:
            if line.strip() == "## Commands":
                in_commands = True
                continue
            if in_commands:
                if line.startswith("## "):
                    break
                if line.startswith("- **"):
                    cmd_lines.append(line)
        assert len(cmd_lines) == 0, f"Expected no commands, got: {cmd_lines}"

    def test_no_format_hook(self):
        assert not (self.root / ".claude" / "hooks" / "format.sh").exists()

    def test_no_lint_hook(self):
        assert not (self.root / ".claude" / "hooks" / "lint.sh").exists()

    def test_no_typecheck_hook(self):
        assert not (self.root / ".claude" / "hooks" / "typecheck.sh").exists()

    def test_mcp_json_has_github_only(self):
        data = json.loads((self.root / ".mcp.json").read_text())
        servers = list(data.get("mcpServers", {}).keys())
        assert "github" in servers
        assert "postgres" not in servers

    def test_project_type_is_generic(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["project_type"] == "generic"

    def test_language_is_generic(self):
        data = json.loads((self.root / ".cc-rig.json").read_text())
        assert data["language"] == "generic"

    def test_agent_docs_present(self):
        docs = sorted((self.root / "agent_docs").iterdir())
        doc_names = [d.name for d in docs]
        assert "architecture.md" in doc_names
        assert "conventions.md" in doc_names
        assert "testing.md" in doc_names

    def test_hooks_executable(self):
        _assert_hooks_executable(self.root)

    def test_manifest_consistent(self):
        _assert_manifest_consistent(self.root)

    def test_no_duplicates(self):
        _assert_no_duplicates(self.root, ".claude/commands")
        _assert_no_duplicates(self.root, ".claude/agents")


# ── S13: Skill Pack Resolution ────────────────────────────────────────


ALL_PACK_NAMES = list(SKILL_PACKS.keys())


class TestS13SkillPackResolution:
    """Verify skill packs produce correct results through full pipeline."""

    # -- CLAUDE.md lists pack skills --

    def test_security_pack_skills_in_claude_md(self, tmp_path):
        """Security pack skills appear in CLAUDE.md Installed Skills section."""
        config, manifest = _generate(tmp_path, "fastapi", "standard", skill_packs=["security"])
        content = _read_claude_md(tmp_path)
        assert "supply-chain-risk-auditor" in content
        assert "variant-analysis" in content
        assert "sharp-edges" in content
        assert "differential-review" in content

    def test_devops_pack_skills_in_claude_md(self, tmp_path):
        config, manifest = _generate(tmp_path, "fastapi", "standard", skill_packs=["devops"])
        content = _read_claude_md(tmp_path)
        assert "iac-terraform" in content
        assert "k8s-troubleshooter" in content
        assert "monitoring-observability" in content
        assert "gitops-workflows" in content

    def test_web_quality_pack_skills_in_claude_md(self, tmp_path):
        config, manifest = _generate(tmp_path, "nextjs", "standard", skill_packs=["web-quality"])
        content = _read_claude_md(tmp_path)
        assert "web-quality-audit" in content
        assert "accessibility" in content
        assert "performance" in content

    def test_database_pro_pack_skills_in_claude_md(self, tmp_path):
        config, manifest = _generate(tmp_path, "fastapi", "standard", skill_packs=["database-pro"])
        content = _read_claude_md(tmp_path)
        assert "database-migrations" in content
        assert "query-efficiency-auditor" in content

    def test_multi_pack_skills_in_claude_md(self, tmp_path):
        config, manifest = _generate(
            tmp_path,
            "fastapi",
            "standard",
            skill_packs=["security", "devops"],
        )
        content = _read_claude_md(tmp_path)
        # Security pack
        assert "supply-chain-risk-auditor" in content
        # DevOps pack
        assert "iac-terraform" in content

    def test_no_packs_no_pack_skills_in_claude_md(self, tmp_path):
        """Without packs, pack-only skills should not appear in CLAUDE.md."""
        config, manifest = _generate(tmp_path, "fastapi", "standard")
        content = _read_claude_md(tmp_path)
        assert "supply-chain-risk-auditor" not in content
        assert "iac-terraform" not in content
        assert "web-quality-audit" not in content
        assert "database-migrations" not in content

    # -- .cc-rig.json persistence --

    def test_cc_rig_json_persists_skill_packs(self, tmp_path):
        config, manifest = _generate(
            tmp_path, "fastapi", "standard", skill_packs=["security", "devops"]
        )
        data = json.loads((tmp_path / ".cc-rig.json").read_text())
        assert data["skill_packs"] == ["security", "devops"]

    def test_cc_rig_json_empty_packs_by_default(self, tmp_path):
        config, manifest = _generate(tmp_path, "fastapi", "standard")
        data = json.loads((tmp_path / ".cc-rig.json").read_text())
        assert data["skill_packs"] == []

    # -- Phase gating bypass --

    def test_security_pack_bypasses_speedrun_gating(self, tmp_path):
        """Pack skills appear even in speedrun (which has security=False)."""
        config, manifest = _generate(tmp_path, "fastapi", "speedrun", skill_packs=["security"])
        content = _read_claude_md(tmp_path)
        assert "supply-chain-risk-auditor" in content
        assert "variant-analysis" in content

    def test_devops_pack_bypasses_speedrun_gating(self, tmp_path):
        config, manifest = _generate(tmp_path, "fastapi", "speedrun", skill_packs=["devops"])
        content = _read_claude_md(tmp_path)
        assert "iac-terraform" in content
        assert "k8s-troubleshooter" in content

    # -- Base skills preserved with packs --

    def test_base_skills_preserved_with_packs(self, tmp_path):
        """Adding packs does not remove base workflow/template skills."""
        config_base, _ = _generate(tmp_path / "base", "fastapi", "standard")
        config_packs, _ = _generate(
            tmp_path / "packs",
            "fastapi",
            "standard",
            skill_packs=["security"],
        )
        base_md = _read_claude_md(tmp_path / "base")
        packs_md = _read_claude_md(tmp_path / "packs")
        # Base skills still present
        assert "owasp-security" in packs_md
        assert "modern-python" in packs_md
        # Pack skills added
        assert "supply-chain-risk-auditor" in packs_md
        # Base didn't have pack skills
        assert "supply-chain-risk-auditor" not in base_md

    # -- No duplicate skills --

    def test_no_duplicate_skills_with_packs(self, tmp_path):
        config, manifest = _generate(
            tmp_path,
            "fastapi",
            "standard",
            skill_packs=["security", "devops", "web-quality", "database-pro"],
        )
        content = _read_claude_md(tmp_path)
        # Count skill mentions in the Installed Skills section
        skills_section = content.split("## Installed Skills")[-1].split("##")[0]
        lines = [ln.strip() for ln in skills_section.splitlines() if ln.strip().startswith("-")]
        skill_names = []
        for line in lines:
            # Each line like "- **Phase**: skill-name (repo)" or "  - skill-name (repo)"
            line = line.lstrip("- ").lstrip("*").strip()
            if "(" in line:
                name = line.split("(")[0].strip().rstrip("*").strip()
                skill_names.append(name)
        # No duplicates
        assert len(skill_names) == len(set(skill_names)), (
            f"Duplicate skills in CLAUDE.md: {[n for n in skill_names if skill_names.count(n) > 1]}"
        )

    # -- Manifest consistency --

    def test_manifest_consistent_with_packs(self, tmp_path):
        config, manifest = _generate(tmp_path, "fastapi", "standard", skill_packs=["security"])
        _assert_manifest_consistent(tmp_path)

    def test_hooks_executable_with_packs(self, tmp_path):
        config, manifest = _generate(tmp_path, "fastapi", "standard", skill_packs=["security"])
        _assert_hooks_executable(tmp_path)

    def test_no_bak_pollution_with_packs(self, tmp_path):
        config, manifest = _generate(tmp_path, "fastapi", "standard", skill_packs=["security"])
        _assert_no_bak_pollution(tmp_path)

    # -- config.skill_packs round-trip through pipeline --

    def test_config_skill_packs_matches_input(self, tmp_path):
        packs = ["security", "database-pro"]
        config, manifest = _generate(tmp_path, "fastapi", "standard", skill_packs=packs)
        assert config.skill_packs == packs

    # -- All packs combined --

    def test_all_packs_combined(self, tmp_path):
        config, manifest = _generate(tmp_path, "fastapi", "standard", skill_packs=ALL_PACK_NAMES)
        content = _read_claude_md(tmp_path)
        # At least one skill from each pack
        assert "supply-chain-risk-auditor" in content  # security
        assert "iac-terraform" in content  # devops
        assert "web-quality-audit" in content  # web-quality
        assert "database-migrations" in content  # database-pro
        _assert_manifest_consistent(tmp_path)


# ── S13 cross-product: Packs × Templates × Workflows ─────────────────


@pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
@pytest.mark.parametrize("template", TEMPLATES)
def test_pack_generates_valid_output_per_template(tmp_path, pack_name, template):
    """Every pack × template combination generates without error."""
    config, manifest = _generate(tmp_path, template, "standard", skill_packs=[pack_name])
    assert len(manifest["files"]) > 0
    _assert_manifest_consistent(tmp_path)


@pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_pack_generates_valid_output_per_workflow(tmp_path, pack_name, workflow):
    """Every pack × workflow combination generates without error."""
    config, manifest = _generate(tmp_path, "fastapi", workflow, skill_packs=[pack_name])
    assert len(manifest["files"]) > 0
    _assert_manifest_consistent(tmp_path)


@pytest.mark.parametrize("pack_name", ALL_PACK_NAMES)
def test_pack_skills_in_claude_md_per_pack(tmp_path, pack_name):
    """Each pack's skills appear in CLAUDE.md when the pack is selected."""
    config, manifest = _generate(tmp_path, "fastapi", "standard", skill_packs=[pack_name])
    content = _read_claude_md(tmp_path)
    pack = SKILL_PACKS[pack_name]
    for skill_name in pack.skill_names:
        assert skill_name in content, (
            f"Pack {pack_name!r} skill {skill_name!r} missing from CLAUDE.md"
        )
