"""ProjectConfig dataclass — the single data structure that flows through the entire system."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Features:
    """Feature flags toggled by workflow presets."""

    memory: bool = False
    spec_workflow: bool = False
    gtd: bool = False
    worktrees: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory": self.memory,
            "spec_workflow": self.spec_workflow,
            "gtd": self.gtd,
            "worktrees": self.worktrees,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Features:
        return cls(
            memory=data.get("memory", False),
            spec_workflow=data.get("spec_workflow", False),
            gtd=data.get("gtd", False),
            worktrees=data.get("worktrees", False),
        )


@dataclass
class SkillRecommendation:
    """A recommended community skill with install metadata."""

    name: str = ""
    sdlc_phase: str = ""  # planning, coding, testing, review, security, database, devops
    source: str = ""  # e.g. "trailofbits/skills"
    install: str = ""  # e.g. "npx skills add trailofbits/skills --skill modern-python"
    description: str = ""  # One-line description

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sdlc_phase": self.sdlc_phase,
            "source": self.source,
            "install": self.install,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillRecommendation:
        return cls(
            name=data.get("name", ""),
            sdlc_phase=data.get("sdlc_phase", ""),
            source=data.get("source", ""),
            install=data.get("install", ""),
            description=data.get("description", ""),
        )


@dataclass
class PluginRecommendation:
    """A recommended official Claude Code plugin."""

    name: str = ""
    marketplace: str = "claude-plugins-official"
    category: str = ""
    description: str = ""
    requires_binary: str = ""
    replaces_mcp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "marketplace": self.marketplace,
            "category": self.category,
            "description": self.description,
            "requires_binary": self.requires_binary,
            "replaces_mcp": self.replaces_mcp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginRecommendation:
        return cls(
            name=data.get("name", ""),
            marketplace=data.get("marketplace", "claude-plugins-official"),
            category=data.get("category", ""),
            description=data.get("description", ""),
            requires_binary=data.get("requires_binary", ""),
            replaces_mcp=data.get("replaces_mcp", ""),
        )


@dataclass
class HarnessConfig:
    """Runtime harness configuration (Axis B: B0-B3 + custom).

    B0 = scaffold only (no harness), B1 = lite, B2 = standard, B3 = autonomy.
    "custom" = à la carte feature selection via individual flags.
    """

    level: str = "none"  # "none", "lite", "standard", "autonomy", "custom"

    # À la carte feature flags (derived from level in __post_init__)
    task_tracking: bool = False  # B1: todo.md + session-tasks hook
    budget_awareness: bool = False  # B1: budget-reminder hook + budget section
    verification_gates: bool = False  # B2: commit-gate hook + gates section
    autonomy_loop: bool = False  # B3: PROMPT.md + loop.sh + progress + config
    ralph_loop_plugin: bool = False  # Alternative to autonomy_loop (official plugin)
    context_awareness: bool = False  # B1+: PreCompact survival hook + context docs
    session_telemetry: bool = False  # B2+: Stop telemetry hook + /health command

    # Budget (B1+)
    budget_per_run_tokens: int | None = None
    budget_warn_at_percent: int = 80

    # Verification gates (B2+)
    require_tests_pass: bool = True
    require_lint_pass: bool = True

    # Autonomy (B3 only)
    max_iterations: int = 20
    checkpoint_commits: bool = True
    if_blocked: str = "stop"  # "stop" or "skip"

    def __post_init__(self) -> None:
        """Derive feature flags from level unless individually set (custom)."""
        if self.level == "custom":
            # Auto-dependency: autonomy_loop needs task_tracking
            if self.autonomy_loop:
                self.task_tracking = True
            return
        if self.level == "ralph-loop":
            # Ralph-loop is plugin-based autonomy — individual flags from user
            self.ralph_loop_plugin = True
            return

        # Derive flags from level
        _LEVEL_FLAGS: dict[str, tuple[bool, bool, bool, bool, bool, bool]] = {
            "none": (False, False, False, False, False, False),
            "lite": (True, True, False, False, True, False),
            "standard": (True, True, True, False, True, True),
            "autonomy": (True, True, True, True, True, True),
        }
        flags = _LEVEL_FLAGS.get(self.level, (False, False, False, False, False, False))
        self.task_tracking = flags[0]
        self.budget_awareness = flags[1]
        self.verification_gates = flags[2]
        self.autonomy_loop = flags[3]
        self.context_awareness = flags[4]
        self.session_telemetry = flags[5]

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "task_tracking": self.task_tracking,
            "budget_awareness": self.budget_awareness,
            "verification_gates": self.verification_gates,
            "autonomy_loop": self.autonomy_loop,
            "ralph_loop_plugin": self.ralph_loop_plugin,
            "context_awareness": self.context_awareness,
            "session_telemetry": self.session_telemetry,
            "budget_per_run_tokens": self.budget_per_run_tokens,
            "budget_warn_at_percent": self.budget_warn_at_percent,
            "require_tests_pass": self.require_tests_pass,
            "require_lint_pass": self.require_lint_pass,
            "max_iterations": self.max_iterations,
            "checkpoint_commits": self.checkpoint_commits,
            "if_blocked": self.if_blocked,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarnessConfig:
        kwargs: dict[str, Any] = {
            "level": data.get("level", "none"),
            "budget_per_run_tokens": data.get("budget_per_run_tokens"),
            "budget_warn_at_percent": data.get("budget_warn_at_percent", 80),
            "require_tests_pass": data.get("require_tests_pass", True),
            "require_lint_pass": data.get("require_lint_pass", True),
            "max_iterations": data.get("max_iterations", 20),
            "checkpoint_commits": data.get("checkpoint_commits", True),
            "if_blocked": data.get("if_blocked", "stop"),
        }
        # Only pass flag kwargs if present in data (backward compat:
        # old configs without flags derive them from level via __post_init__)
        if "task_tracking" in data:
            kwargs["task_tracking"] = data["task_tracking"]
            kwargs["budget_awareness"] = data.get("budget_awareness", False)
            kwargs["verification_gates"] = data.get("verification_gates", False)
            kwargs["autonomy_loop"] = data.get("autonomy_loop", False)
            kwargs["context_awareness"] = data.get("context_awareness", False)
            kwargs["session_telemetry"] = data.get("session_telemetry", False)
        if "ralph_loop_plugin" in data:
            kwargs["ralph_loop_plugin"] = data["ralph_loop_plugin"]
        return cls(**kwargs)


def _parse_plugins(raw: list[Any]) -> list[PluginRecommendation]:
    """Parse a list of plugins from dicts or PluginRecommendation objects."""
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(PluginRecommendation.from_dict(item))
        elif isinstance(item, PluginRecommendation):
            result.append(item)
    return result


def _parse_skills(raw: list[Any]) -> list[SkillRecommendation]:
    """Parse a list of skills from either rich dicts or bare strings."""
    result = []
    for item in raw:
        if isinstance(item, dict):
            result.append(SkillRecommendation.from_dict(item))
        elif isinstance(item, str):
            result.append(SkillRecommendation(name=item))
        elif isinstance(item, SkillRecommendation):
            result.append(item)
    return result


@dataclass
class ProjectConfig:
    """Fully resolved project configuration.

    Created by compute_defaults(), consumed by generators.
    """

    # Identity
    project_name: str = ""
    project_desc: str = ""
    output_dir: str = "."

    # Template (stack)
    language: str = ""
    framework: str = ""
    project_type: str = ""

    # Tool commands (from template)
    test_cmd: str = ""
    lint_cmd: str = ""
    format_cmd: str = ""
    typecheck_cmd: str = ""
    build_cmd: str = ""
    source_dir: str = "."
    test_dir: str = "tests"

    # Workflow (process)
    workflow: str = ""
    agents: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)

    # Features
    features: Features = field(default_factory=Features)
    permission_mode: str = "default"

    # Harness (Axis B runtime discipline)
    harness: HarnessConfig = field(default_factory=HarnessConfig)

    # Stack-specific recommendations
    recommended_skills: list[SkillRecommendation] = field(default_factory=list)
    recommended_plugins: list[PluginRecommendation] = field(default_factory=list)
    default_mcps: list[str] = field(default_factory=list)
    skill_packs: list[str] = field(default_factory=list)

    # Model routing
    claude_plan: str = "pro"
    model_overrides: dict[str, str] = field(default_factory=dict)

    # Process skills (v2: workflow-specific community skills)
    process_skills: list[str] = field(default_factory=list)
    workflow_source: str = "cc-rig"
    workflow_source_url: str = ""

    # Metadata
    cc_rig_version: str = ""
    created_at: str = ""
    template_preset: str = ""
    workflow_preset: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_desc": self.project_desc,
            "output_dir": self.output_dir,
            "language": self.language,
            "framework": self.framework,
            "project_type": self.project_type,
            "test_cmd": self.test_cmd,
            "lint_cmd": self.lint_cmd,
            "format_cmd": self.format_cmd,
            "typecheck_cmd": self.typecheck_cmd,
            "build_cmd": self.build_cmd,
            "source_dir": self.source_dir,
            "test_dir": self.test_dir,
            "workflow": self.workflow,
            "agents": list(self.agents),
            "commands": list(self.commands),
            "hooks": list(self.hooks),
            "features": self.features.to_dict(),
            "permission_mode": self.permission_mode,
            "harness": self.harness.to_dict(),
            "recommended_skills": [s.to_dict() for s in self.recommended_skills],
            "recommended_plugins": [p.to_dict() for p in self.recommended_plugins],
            "default_mcps": list(self.default_mcps),
            "skill_packs": list(self.skill_packs),
            "claude_plan": self.claude_plan,
            "model_overrides": dict(self.model_overrides),
            "process_skills": list(self.process_skills),
            "workflow_source": self.workflow_source,
            "workflow_source_url": self.workflow_source_url,
            "cc_rig_version": self.cc_rig_version,
            "created_at": self.created_at,
            "template_preset": self.template_preset,
            "workflow_preset": self.workflow_preset,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectConfig:
        features_data = data.get("features", {})
        features = (
            Features.from_dict(features_data) if isinstance(features_data, dict) else Features()
        )

        harness_data = data.get("harness", {})
        harness = (
            HarnessConfig.from_dict(harness_data)
            if isinstance(harness_data, dict)
            else HarnessConfig()
        )

        return cls(
            project_name=data.get("project_name", ""),
            project_desc=data.get("project_desc", ""),
            output_dir=data.get("output_dir", "."),
            language=data.get("language", ""),
            framework=data.get("framework", ""),
            project_type=data.get("project_type", ""),
            test_cmd=data.get("test_cmd", ""),
            lint_cmd=data.get("lint_cmd", ""),
            format_cmd=data.get("format_cmd", ""),
            typecheck_cmd=data.get("typecheck_cmd", ""),
            build_cmd=data.get("build_cmd", ""),
            source_dir=data.get("source_dir", "."),
            test_dir=data.get("test_dir", "tests"),
            workflow=data.get("workflow", ""),
            agents=list(data.get("agents", [])),
            commands=list(data.get("commands", [])),
            hooks=list(data.get("hooks", [])),
            features=features,
            permission_mode=data.get("permission_mode", "default"),
            harness=harness,
            recommended_skills=_parse_skills(data.get("recommended_skills", [])),
            recommended_plugins=_parse_plugins(data.get("recommended_plugins", [])),
            default_mcps=list(data.get("default_mcps", [])),
            skill_packs=list(data.get("skill_packs", [])),
            claude_plan=data.get("claude_plan", "pro"),
            model_overrides=dict(data.get("model_overrides", {})),
            process_skills=list(data.get("process_skills", [])),
            workflow_source=data.get("workflow_source", "cc-rig"),
            workflow_source_url=data.get("workflow_source_url", ""),
            cc_rig_version=data.get("cc_rig_version", ""),
            created_at=data.get("created_at", ""),
            template_preset=data.get("template_preset", ""),
            workflow_preset=data.get("workflow_preset", ""),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> ProjectConfig:
        return cls.from_dict(json.loads(json_str))
