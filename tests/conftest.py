"""Shared test fixtures and helpers for cc-rig."""

from cc_rig.config.defaults import compute_defaults
from cc_rig.config.project import Features, ProjectConfig, SkillRecommendation
from cc_rig.generators.orchestrator import generate_all
from cc_rig.ui.prompts import IO


def make_io(inputs: list[str]) -> IO:
    """Create an IO with pre-canned input responses."""
    it = iter(inputs)
    output: list[str] = []
    io = IO(
        input_fn=lambda _prompt: next(it),
        print_fn=lambda *args: output.append(str(args[0]) if args else ""),
    )
    io._output = output  # for inspection
    return io


def make_valid_config(**overrides) -> ProjectConfig:
    """Create a minimal valid ProjectConfig."""
    defaults = {
        "project_name": "test-project",
        "project_desc": "A test project",
        "output_dir": "/tmp/test",
        "language": "python",
        "framework": "fastapi",
        "project_type": "api",
        "test_cmd": "pytest",
        "lint_cmd": "ruff check .",
        "format_cmd": "ruff format .",
        "typecheck_cmd": "mypy .",
        "build_cmd": "",
        "source_dir": "app",
        "test_dir": "tests",
        "workflow": "standard",
        "agents": ["code-reviewer", "test-writer", "explorer", "architect", "refactorer"],
        "commands": [
            "fix-issue",
            "review",
            "test",
            "plan",
            "learn",
            "assumptions",
            "remember",
            "refactor",
        ],
        "hooks": [
            "format",
            "lint",
            "typecheck",
            "block-rm-rf",
            "block-env",
            "block-main",
            "session-context",
            "stop-validator",
            "memory-precompact",
        ],
        "features": Features(memory=True),
        "permission_mode": "permissive",
        "recommended_skills": [
            SkillRecommendation(
                name="modern-python",
                sdlc_phase="coding",
                source="trailofbits/skills",
                install="npx skills add trailofbits/skills --skill modern-python",
                description="Modern Python with uv, ruff, ty, pytest",
            ),
            SkillRecommendation(
                name="insecure-defaults",
                sdlc_phase="security",
                source="trailofbits/skills",
                install="npx skills add trailofbits/skills --skill insecure-defaults",
                description="Detect hardcoded credentials",
            ),
        ],
        "default_mcps": ["github", "postgres"],
        "claude_plan": "pro",
        "model_overrides": {},
        "cc_rig_version": "1.0.0",
        "created_at": "2026-02-22T00:00:00Z",
        "template_preset": "fastapi",
        "workflow_preset": "standard",
    }
    defaults.update(overrides)
    return ProjectConfig(**defaults)


def generate_project(tmp_path, template="fastapi", workflow="standard"):
    """Generate a full project in tmp_path and return config."""
    config = compute_defaults(template, workflow, project_name="test-proj")
    manifest = generate_all(config, tmp_path)
    return config, manifest
