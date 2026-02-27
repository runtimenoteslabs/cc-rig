"""Skills subsystem — curated skill catalog, resolution, and auto-download."""

from cc_rig.skills.registry import (
    SKILL_CATALOG,
    TEMPLATE_SKILLS,
    WORKFLOW_PHASES,
    WORKFLOW_SKILLS,
    SkillSpec,
    resolve_skills,
)

__all__ = [
    "SKILL_CATALOG",
    "TEMPLATE_SKILLS",
    "WORKFLOW_PHASES",
    "WORKFLOW_SKILLS",
    "SkillSpec",
    "resolve_skills",
]
