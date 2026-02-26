"""E2E Test Matrix for cc-rig init — 12 scenarios covering all dimensions.

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
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from cc_rig.clean import cleanup_files, load_manifest, run_clean
from cc_rig.config.defaults import compute_defaults
from cc_rig.config.project import HarnessConfig, ProjectConfig
from cc_rig.generators.orchestrator import generate_all

# ── Helpers ───────────────────────────────────────────────────────────


def _generate(
    tmp_path: Path,
    template: str,
    workflow: str,
    *,
    harness_level: str = "none",
    name: str = "test-proj",
) -> tuple[ProjectConfig, dict]:
    """Generate a project with optional harness level."""
    config = compute_defaults(template, workflow, project_name=name)
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
        assert len(files) == 44, f"Expected 44 files, got {len(files)}: {sorted(files)}"

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
        assert (skills_dir / "tdd" / "SKILL.md").exists()
        assert (skills_dir / "systematic-debug" / "SKILL.md").exists()
        assert (skills_dir / "project-patterns" / "SKILL.md").exists()
        assert (skills_dir / "deployment-checklist" / "SKILL.md").exists()

    def test_recommended_skills_doc(self):
        assert (self.root / "docs" / "recommended-skills.md").exists()

    def test_no_harness_files(self):
        assert not (self.root / "loop.sh").exists()
        assert not (self.root / "PROMPT.md").exists()
        assert not (self.root / ".claude" / "harness-config.json").exists()


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
        assert (self.root / "agent_docs" / "budget-guide.md").exists()

    def test_harness_b2_files(self):
        assert (self.root / "agent_docs" / "verification-gates.md").exists()
        assert (self.root / "agent_docs" / "review-notes.md").exists()

    def test_harness_b3_files(self):
        assert (self.root / "agent_docs" / "autonomy-loop.md").exists()
        assert (self.root / "PROMPT.md").exists()
        assert (self.root / "loop.sh").exists()
        assert (self.root / ".claude" / "harness-config.json").exists()

    def test_loop_sh_executable(self):
        mode = (self.root / "loop.sh").stat().st_mode
        assert mode & stat.S_IXUSR

    def test_harness_config_json(self):
        data = json.loads((self.root / ".claude" / "harness-config.json").read_text())
        assert data["harness_level"] == "autonomy"
        assert data["max_iterations"] == 20

    def test_budget_reminder_hook(self):
        hooks = _list_dir(self.root, ".claude/hooks")
        assert "budget-reminder.sh" in hooks

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
        assert len(files) == 30, f"Expected 30 files, got {len(files)}: {sorted(files)}"

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

    def test_harness_b2_files(self):
        assert (self.root / "agent_docs" / "verification-gates.md").exists()
        assert (self.root / "agent_docs" / "review-notes.md").exists()

    def test_harness_b1_files(self):
        assert (self.root / "tasks" / "todo.md").exists()
        assert (self.root / "agent_docs" / "budget-guide.md").exists()

    def test_no_b3_files(self):
        assert not (self.root / "loop.sh").exists()
        assert not (self.root / "PROMPT.md").exists()
        assert not (self.root / ".claude" / "harness-config.json").exists()

    def test_budget_reminder_hook(self):
        hooks = _list_dir(self.root, ".claude/hooks")
        assert "budget-reminder.sh" in hooks

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

    def test_autonomy_loop_doc(self):
        assert (self.root / "agent_docs" / "autonomy-loop.md").exists()

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
        assert len(files) == 30, f"Expected 30 files, got {len(files)}: {sorted(files)}"

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


TEMPLATES = ["fastapi", "django", "flask", "gin", "echo", "nextjs", "rust-cli"]
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
        assert (tmp_path / "agent_docs" / "budget-guide.md").exists()
        assert not (tmp_path / "agent_docs" / "verification-gates.md").exists()
    elif level == "standard":
        assert (tmp_path / "tasks" / "todo.md").exists()
        assert (tmp_path / "agent_docs" / "verification-gates.md").exists()
        assert not (tmp_path / "loop.sh").exists()
    elif level == "autonomy":
        assert (tmp_path / "tasks" / "todo.md").exists()
        assert (tmp_path / "agent_docs" / "verification-gates.md").exists()
        assert (tmp_path / "loop.sh").exists()
        assert (tmp_path / "PROMPT.md").exists()
        assert (tmp_path / ".claude" / "harness-config.json").exists()

    _assert_manifest_consistent(tmp_path)


# ── Feature flag isolation tests ──────────────────────────────────────


def test_memory_false_produces_no_memory_files(tmp_path):
    """When memory=false, no memory files or hooks are generated."""
    config, manifest = _generate(tmp_path, "fastapi", "speedrun")
    assert not (tmp_path / "memory").exists()
    assert "remember.md" not in [
        f.name for f in (tmp_path / ".claude" / "commands").iterdir()
    ]


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
