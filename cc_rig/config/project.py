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
class HarnessConfig:
    """Runtime harness configuration (Axis B: B0-B3).

    B0 = scaffold only (no harness), B1 = lite, B2 = standard, B3 = autonomy.
    """

    level: str = "none"  # "none", "lite", "standard", "autonomy"

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
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
        return cls(
            level=data.get("level", "none"),
            budget_per_run_tokens=data.get("budget_per_run_tokens"),
            budget_warn_at_percent=data.get("budget_warn_at_percent", 80),
            require_tests_pass=data.get("require_tests_pass", True),
            require_lint_pass=data.get("require_lint_pass", True),
            max_iterations=data.get("max_iterations", 20),
            checkpoint_commits=data.get("checkpoint_commits", True),
            if_blocked=data.get("if_blocked", "stop"),
        )


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
    default_mcps: list[str] = field(default_factory=list)
    skill_packs: list[str] = field(default_factory=list)

    # Model routing
    claude_plan: str = "pro"
    model_overrides: dict[str, str] = field(default_factory=dict)

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
            "default_mcps": list(self.default_mcps),
            "skill_packs": list(self.skill_packs),
            "claude_plan": self.claude_plan,
            "model_overrides": dict(self.model_overrides),
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
            default_mcps=list(data.get("default_mcps", [])),
            skill_packs=list(data.get("skill_packs", [])),
            claude_plan=data.get("claude_plan", "pro"),
            model_overrides=dict(data.get("model_overrides", {})),
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
