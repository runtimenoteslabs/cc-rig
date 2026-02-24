"""Configuration data model, validation, and project detection."""

from cc_rig.config.project import Features, ProjectConfig
from cc_rig.config.schema import validate_config

__all__ = ["Features", "ProjectConfig", "validate_config"]
