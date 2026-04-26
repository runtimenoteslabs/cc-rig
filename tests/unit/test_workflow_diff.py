"""Tests for cross-workflow content differences.

Generates output for different workflows and explicitly compares them
to verify they produce meaningfully different content.
"""

from cc_rig.config.defaults import compute_defaults
from cc_rig.generators.orchestrator import generate_all


def _gen(tmp_path, workflow, template="fastapi"):
    out = tmp_path / workflow
    config = compute_defaults(template, workflow, project_name="test")
    manifest = generate_all(config, out)
    return config, manifest, out


class TestSpeedrunVsStandard:
    """Speedrun should be a strict subset of standard."""

    def test_standard_has_more_hooks(self, tmp_path):
        sr_cfg, _, _ = _gen(tmp_path, "speedrun")
        st_cfg, _, _ = _gen(tmp_path, "standard")
        assert len(st_cfg.hooks) > len(sr_cfg.hooks)

    def test_standard_has_more_agents(self, tmp_path):
        sr_cfg, _, _ = _gen(tmp_path, "speedrun")
        st_cfg, _, _ = _gen(tmp_path, "standard")
        assert len(st_cfg.agents) > len(sr_cfg.agents)

    def test_standard_has_more_commands(self, tmp_path):
        sr_cfg, _, _ = _gen(tmp_path, "speedrun")
        st_cfg, _, _ = _gen(tmp_path, "standard")
        assert len(st_cfg.commands) > len(sr_cfg.commands)

    def test_standard_has_more_files(self, tmp_path):
        _, sr_m, _ = _gen(tmp_path, "speedrun")
        _, st_m, _ = _gen(tmp_path, "standard")
        assert len(st_m["files"]) > len(sr_m["files"])

    def test_standard_has_memory_speedrun_does_not(self, tmp_path):
        sr_cfg, _, sr_out = _gen(tmp_path, "speedrun")
        st_cfg, _, st_out = _gen(tmp_path, "standard")
        assert st_cfg.features.memory is True
        assert sr_cfg.features.memory is False
        assert (st_out / "memory" / "decisions.md").exists()
        assert not (sr_out / "memory").exists()


class TestStandardVsVerifyHeavy:
    """Verify-heavy should be a superset of standard."""

    def test_verify_heavy_has_more_agents(self, tmp_path):
        st_cfg, _, _ = _gen(tmp_path, "standard")
        vh_cfg, _, _ = _gen(tmp_path, "verify-heavy")
        assert len(vh_cfg.agents) > len(st_cfg.agents)

    def test_verify_heavy_has_security_auditor(self, tmp_path):
        st_cfg, _, _ = _gen(tmp_path, "standard")
        vh_cfg, _, _ = _gen(tmp_path, "verify-heavy")
        assert "security-auditor" in vh_cfg.agents
        assert "security-auditor" not in st_cfg.agents

    def test_verify_heavy_has_more_hooks(self, tmp_path):
        st_cfg, _, _ = _gen(tmp_path, "standard")
        vh_cfg, _, _ = _gen(tmp_path, "verify-heavy")
        assert len(vh_cfg.hooks) > len(st_cfg.hooks)

    def test_verify_heavy_has_more_files(self, tmp_path):
        _, st_m, _ = _gen(tmp_path, "standard")
        _, vh_m, _ = _gen(tmp_path, "verify-heavy")
        assert len(vh_m["files"]) > len(st_m["files"])


class TestSpecDrivenUnique:
    """Spec-driven should include spec workflow components."""

    def test_has_spec_agents(self, tmp_path):
        sd_cfg, _, _ = _gen(tmp_path, "spec-driven")
        assert "pm-spec" in sd_cfg.agents
        assert "implementer" in sd_cfg.agents

    def test_has_spec_commands(self, tmp_path):
        sd_cfg, _, _ = _gen(tmp_path, "spec-driven")
        assert "spec-create" in sd_cfg.commands
        assert "spec-execute" in sd_cfg.commands

    def test_standard_lacks_spec_components(self, tmp_path):
        st_cfg, _, _ = _gen(tmp_path, "standard")
        assert "pm-spec" not in st_cfg.agents
        assert "spec-create" not in st_cfg.commands


class TestGtdLiteUnique:
    """gtd-lite resolves to the standard tier with a gtd process pack."""

    def test_has_standard_tier_commands(self, tmp_path):
        """gtd-lite maps to standard tier; standard commands are present."""
        gtd_cfg, _, _ = _gen(tmp_path, "gtd-lite")
        assert gtd_cfg.workflow == "standard"
        assert gtd_cfg.process_pack == "gtd"
        assert "remember" in gtd_cfg.commands
        assert "fix-issue" in gtd_cfg.commands

    def test_no_gtd_specific_commands_by_default(self, tmp_path):
        """GTD commands require features.gtd=True; not set by the gtd-lite alias."""
        gtd_cfg, _, _ = _gen(tmp_path, "gtd-lite")
        assert "gtd-capture" not in gtd_cfg.commands
        assert "gtd-process" not in gtd_cfg.commands

    def test_standard_lacks_gtd_components(self, tmp_path):
        st_cfg, _, _ = _gen(tmp_path, "standard")
        assert "gtd-capture" not in st_cfg.commands

    def test_has_gtd_feature_flag(self, tmp_path):
        """gtd-lite resolves to standard tier; gtd feature flag is off by default."""
        gtd_cfg, _, _ = _gen(tmp_path, "gtd-lite")
        assert gtd_cfg.features.gtd is False


class TestCLAUDEMdDiffers:
    """CLAUDE.md content should vary by workflow."""

    def test_speedrun_shorter_than_verify_heavy(self, tmp_path):
        _, _, sr_out = _gen(tmp_path, "speedrun")
        _, _, vh_out = _gen(tmp_path, "verify-heavy")
        sr_lines = len((sr_out / "CLAUDE.md").read_text().splitlines())
        vh_lines = len((vh_out / "CLAUDE.md").read_text().splitlines())
        assert vh_lines > sr_lines

    def test_verify_heavy_mentions_security(self, tmp_path):
        _, _, vh_out = _gen(tmp_path, "verify-heavy")
        content = (vh_out / "CLAUDE.md").read_text().lower()
        assert "security" in content or "verify" in content
