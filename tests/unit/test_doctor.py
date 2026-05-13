"""Tests for doctor command: health checks and --fix."""

import os
import stat
import time

from cc_rig.cli import main
from cc_rig.doctor import DoctorResult, run_doctor
from tests.conftest import generate_project


class TestDoctorHealthy:
    def test_healthy_project_passes(self, tmp_path):
        generate_project(tmp_path)
        result = run_doctor(tmp_path)
        # Should have no errors (warnings about line counts are ok)
        assert result.passed

    def test_healthy_returns_doctor_result(self, tmp_path):
        generate_project(tmp_path)
        result = run_doctor(tmp_path)
        assert isinstance(result, DoctorResult)


class TestDoctorMissingConfig:
    def test_no_cc_rig_json(self, tmp_path):
        result = run_doctor(tmp_path)
        assert not result.passed
        assert any(".cc-rig.json" in e for e in result.errors)

    def test_invalid_cc_rig_json(self, tmp_path):
        (tmp_path / ".cc-rig.json").write_text("{bad json")
        result = run_doctor(tmp_path)
        assert not result.passed
        assert any("invalid" in e.lower() for e in result.errors)


class TestDoctorMissingManifest:
    def test_missing_manifest_warns(self, tmp_path):
        generate_project(tmp_path)
        # Remove manifest
        manifest = tmp_path / ".claude" / ".cc-rig-manifest.json"
        manifest.unlink()
        result = run_doctor(tmp_path)
        assert any("manifest" in w.lower() for w in result.warnings)


class TestDoctorMissingFiles:
    def test_missing_claude_md(self, tmp_path):
        generate_project(tmp_path)
        (tmp_path / "CLAUDE.md").unlink()
        result = run_doctor(tmp_path)
        assert not result.passed
        assert any("CLAUDE.md" in e for e in result.errors)

    def test_missing_agent_file(self, tmp_path):
        config, _ = generate_project(tmp_path)
        # Remove one agent file
        agent_name = config.agents[0]
        (tmp_path / ".claude" / "agents" / f"{agent_name}.md").unlink()
        result = run_doctor(tmp_path)
        assert not result.passed
        assert any(agent_name in e for e in result.errors)

    def test_missing_command_file(self, tmp_path):
        config, _ = generate_project(tmp_path)
        # Remove one command file
        cmd_name = config.commands[0]
        (tmp_path / ".claude" / "commands" / f"{cmd_name}.md").unlink()
        result = run_doctor(tmp_path)
        assert not result.passed


class TestDoctorMemory:
    def test_missing_memory_file_detected(self, tmp_path):
        generate_project(tmp_path, workflow="standard")
        # standard workflow always enables memory
        assert (tmp_path / "memory" / "decisions.md").exists()
        (tmp_path / "memory" / "decisions.md").unlink()
        result = run_doctor(tmp_path)
        assert not result.passed

    def test_fix_creates_missing_memory(self, tmp_path):
        generate_project(tmp_path, workflow="verify-heavy")
        decisions = tmp_path / "memory" / "decisions.md"
        # verify-heavy always enables memory
        assert decisions.exists()
        decisions.unlink()
        result = run_doctor(tmp_path, fix=True)
        assert decisions.exists()
        assert any("memory" in f.lower() for f in result.fixes)


class TestDoctorHookPermissions:
    def test_non_executable_hook_warns(self, tmp_path):
        generate_project(tmp_path)
        hooks_dir = tmp_path / ".claude" / "hooks"
        # standard workflow always generates hook scripts
        assert hooks_dir.exists() and list(hooks_dir.glob("*.sh"))
        script = next(hooks_dir.glob("*.sh"))
        script.chmod(0o644)
        result = run_doctor(tmp_path)
        assert any("executable" in w.lower() for w in result.warnings)

    def test_fix_makes_hooks_executable(self, tmp_path):
        generate_project(tmp_path)
        hooks_dir = tmp_path / ".claude" / "hooks"
        assert hooks_dir.exists() and list(hooks_dir.glob("*.sh"))
        script = next(hooks_dir.glob("*.sh"))
        script.chmod(0o644)
        result = run_doctor(tmp_path, fix=True)
        assert script.stat().st_mode & stat.S_IXUSR
        assert any("permission" in f.lower() for f in result.fixes)


class TestDoctorOrphanedFiles:
    def test_orphaned_file_in_claude_dir(self, tmp_path):
        generate_project(tmp_path)
        # Add an untracked file
        orphan = tmp_path / ".claude" / "stray-file.txt"
        orphan.write_text("I shouldn't be here")
        result = run_doctor(tmp_path)
        assert any("orphan" in w.lower() for w in result.warnings)


class TestDoctorSessionLogStaleness:
    def test_stale_session_log(self, tmp_path):
        generate_project(tmp_path, workflow="verify-heavy")
        session_log = tmp_path / "memory" / "session-log.md"
        assert session_log.exists()
        # Set mtime to 30 days ago
        old_time = time.time() - (30 * 86400)
        os.utime(session_log, (old_time, old_time))
        result = run_doctor(tmp_path)
        assert any("session log" in w.lower() for w in result.warnings)


class TestDoctorInvalidJSON:
    def test_corrupt_settings_json(self, tmp_path):
        generate_project(tmp_path)
        settings = tmp_path / ".claude" / "settings.json"
        settings.write_text("{not valid}")
        result = run_doctor(tmp_path)
        assert not result.passed
        assert any("json" in e.lower() for e in result.errors)


class TestDoctorCacheFriendliness:
    """CLAUDE.md cache-friendliness check detects anti-patterns in static zone."""

    def test_healthy_project_no_cache_warnings(self, tmp_path):
        generate_project(tmp_path)
        result = run_doctor(tmp_path)
        # Generated CLAUDE.md should be cache-friendly by default
        cache_warnings = [w for w in result.warnings if "static section" in w.lower()]
        assert len(cache_warnings) == 0

    def test_timestamp_in_static_section_warns(self, tmp_path):
        generate_project(tmp_path)
        claude_md = tmp_path / "CLAUDE.md"
        content = claude_md.read_text()
        # Inject a timestamp marker in the static section (before Current Context)
        content = content.replace(
            "## Guardrails",
            "Updated: 2026-04-01\n\n## Guardrails",
        )
        claude_md.write_text(content)
        result = run_doctor(tmp_path)
        assert any("static section" in w.lower() for w in result.warnings)

    def test_date_in_static_section_warns(self, tmp_path):
        generate_project(tmp_path)
        claude_md = tmp_path / "CLAUDE.md"
        content = claude_md.read_text()
        content = content.replace(
            "## Guardrails",
            "Last modified 2026-03-15\n\n## Guardrails",
        )
        claude_md.write_text(content)
        result = run_doctor(tmp_path)
        assert any("static section" in w.lower() for w in result.warnings)

    def test_date_in_dynamic_section_ok(self, tmp_path):
        generate_project(tmp_path)
        claude_md = tmp_path / "CLAUDE.md"
        content = claude_md.read_text()
        # Date in Current Context (dynamic section) is fine
        content = content.replace(
            "- **Current task**: (none)",
            "- **Current task**: Fix bug (2026-04-01)",
        )
        claude_md.write_text(content)
        result = run_doctor(tmp_path)
        cache_warnings = [w for w in result.warnings if "static section" in w.lower()]
        assert len(cache_warnings) == 0


class TestDoctorCacheHealth:
    """Cache health check parses session JSONL files."""

    def test_no_session_data_no_warning(self, tmp_path):
        """No session data directory means no warning (graceful skip)."""
        generate_project(tmp_path)
        result = run_doctor(tmp_path)
        assert not any("cache health" in w.lower() for w in result.warnings)

    def test_low_cache_ratio_warns(self, tmp_path, monkeypatch):
        """Session with poor cache hit ratio should warn."""
        import json as json_mod

        from cc_rig.doctor import _get_session_dir

        generate_project(tmp_path)

        # Create a fake session directory and JSONL file
        session_dir = _get_session_dir(tmp_path)
        session_dir.mkdir(parents=True, exist_ok=True)
        jsonl = session_dir / "session.jsonl"

        # Write entries with poor cache ratio (30% reads, 70% creation)
        entries = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "usage": {
                        "cache_read_input_tokens": 300,
                        "cache_creation_input_tokens": 700,
                    },
                },
            },
        ]
        jsonl.write_text("\n".join(json_mod.dumps(e) for e in entries) + "\n")

        result = run_doctor(tmp_path)
        assert any("cache health" in w.lower() for w in result.warnings)

    def test_good_cache_ratio_no_warning(self, tmp_path):
        """Session with healthy cache ratio should not warn."""
        import json as json_mod

        from cc_rig.doctor import _get_session_dir

        generate_project(tmp_path)

        session_dir = _get_session_dir(tmp_path)
        session_dir.mkdir(parents=True, exist_ok=True)
        jsonl = session_dir / "session.jsonl"

        # Write entries with good cache ratio (90% reads)
        entries = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "usage": {
                        "cache_read_input_tokens": 9000,
                        "cache_creation_input_tokens": 1000,
                    },
                },
            },
        ]
        jsonl.write_text("\n".join(json_mod.dumps(e) for e in entries) + "\n")

        result = run_doctor(tmp_path)
        assert not any("cache health" in w.lower() for w in result.warnings)


class TestDoctorJsonlAccounting:
    """JSONL accounting integrity check detects PRELIM entry inflation."""

    def test_no_session_data_no_info(self, tmp_path):
        """No session data directory means no info entry."""
        generate_project(tmp_path)
        result = run_doctor(tmp_path)
        assert not any("jsonl accounting" in n.lower() for n in result.info)

    def test_no_duplicates_reports_ratio_1(self, tmp_path):
        """Session with unique cache keys reports ratio 1.00x."""
        import json as json_mod

        from cc_rig.doctor import _get_session_dir

        generate_project(tmp_path)

        session_dir = _get_session_dir(tmp_path)
        session_dir.mkdir(parents=True, exist_ok=True)
        jsonl = session_dir / "session.jsonl"

        entries = [
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "usage": {
                        "cache_read_input_tokens": 1000,
                        "cache_creation_input_tokens": 500,
                    },
                },
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "usage": {
                        "cache_read_input_tokens": 2000,
                        "cache_creation_input_tokens": 100,
                    },
                },
            },
        ]
        jsonl.write_text("\n".join(json_mod.dumps(e) for e in entries) + "\n")

        result = run_doctor(tmp_path)
        info_msgs = [n for n in result.info if "jsonl accounting" in n.lower()]
        assert len(info_msgs) == 1
        assert "1.00x" in info_msgs[0]
        assert "PRELIM" not in info_msgs[0]

    def test_duplicates_reports_inflation(self, tmp_path):
        """Consecutive entries with identical cache keys report inflation."""
        import json as json_mod

        from cc_rig.doctor import _get_session_dir

        generate_project(tmp_path)

        session_dir = _get_session_dir(tmp_path)
        session_dir.mkdir(parents=True, exist_ok=True)
        jsonl = session_dir / "session.jsonl"

        # 3 consecutive entries with same cache key (1 FINAL + 2 PRELIM)
        same_usage = {
            "cache_read_input_tokens": 5000,
            "cache_creation_input_tokens": 200,
        }
        entries = [
            {"type": "assistant", "message": {"role": "assistant", "usage": same_usage}},
            {"type": "assistant", "message": {"role": "assistant", "usage": same_usage}},
            {"type": "assistant", "message": {"role": "assistant", "usage": same_usage}},
        ]
        jsonl.write_text("\n".join(json_mod.dumps(e) for e in entries) + "\n")

        result = run_doctor(tmp_path)
        info_msgs = [n for n in result.info if "jsonl accounting" in n.lower()]
        assert len(info_msgs) == 1
        assert "3.00x" in info_msgs[0]
        assert "2 PRELIM" in info_msgs[0]

    def test_mixed_entries_correct_counting(self, tmp_path):
        """Non-assistant entries break dedup runs."""
        import json as json_mod

        from cc_rig.doctor import _get_session_dir

        generate_project(tmp_path)

        session_dir = _get_session_dir(tmp_path)
        session_dir.mkdir(parents=True, exist_ok=True)
        jsonl = session_dir / "session.jsonl"

        same_usage = {
            "cache_read_input_tokens": 1000,
            "cache_creation_input_tokens": 100,
        }
        entries = [
            {"type": "assistant", "message": {"role": "assistant", "usage": same_usage}},
            {"type": "assistant", "message": {"role": "assistant", "usage": same_usage}},
            {"type": "human", "message": {"role": "human"}},
            {"type": "assistant", "message": {"role": "assistant", "usage": same_usage}},
        ]
        jsonl.write_text("\n".join(json_mod.dumps(e) for e in entries) + "\n")

        result = run_doctor(tmp_path)
        info_msgs = [n for n in result.info if "jsonl accounting" in n.lower()]
        assert len(info_msgs) == 1
        # 3 raw assistant entries, but human breaks the run:
        # run1: 2 entries -> 1 deduped, run2: 1 entry -> 1 deduped = 2 deduped total
        assert "3 entries" in info_msgs[0]
        assert "2 after dedup" in info_msgs[0]


class TestDoctorSettingsKeyValidity:
    """v3.1 Check 17: settings.json keys validated against pinned CC schema."""

    def test_clean_settings_passes(self, tmp_path):
        generate_project(tmp_path)
        result = run_doctor(tmp_path)
        assert result.passed
        info = " ".join(result.info)
        assert "all valid for CC v2.1.126" in info

    def test_unknown_key_warns(self, tmp_path):
        import json

        generate_project(tmp_path)
        settings_path = tmp_path / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())
        data["totallyMadeUpKey"] = "value"
        settings_path.write_text(json.dumps(data, indent=2))
        result = run_doctor(tmp_path)
        assert any("totallyMadeUpKey" in w and "v2.1.126" in w for w in result.warnings), (
            f"expected warning about unknown key, got: {result.warnings}"
        )

    def test_known_v3_3_keys_pass(self, tmp_path):
        import json

        generate_project(tmp_path)
        settings_path = tmp_path / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())
        # All these are now in the pinned schema
        data["language"] = "en"
        data["prUrlTemplate"] = "https://github.com/owner/repo/pull/{n}"
        data["autoMemoryEnabled"] = True
        settings_path.write_text(json.dumps(data, indent=2))
        result = run_doctor(tmp_path)
        unknown_warnings = [w for w in result.warnings if "v2.1.126 schema" in w]
        assert not unknown_warnings, f"expected no schema warnings, got: {unknown_warnings}"


class TestDoctorModelIdValidity:
    """v3.1 Check 19: agent model frontmatter validates against known IDs."""

    def test_clean_agents_pass(self, tmp_path):
        generate_project(tmp_path)
        result = run_doctor(tmp_path)
        info = " ".join(result.info)
        assert "Agent model IDs:" in info
        assert "valid" in info

    def test_unknown_model_warns(self, tmp_path):
        generate_project(tmp_path)
        agent = next((tmp_path / ".claude" / "agents").glob("*.md"))
        content = agent.read_text()
        # Replace model line with garbage
        content = content.replace("model: sonnet", "model: gpt-5")
        content = content.replace("model: opus", "model: gpt-5")
        content = content.replace("model: haiku", "model: gpt-5")
        agent.write_text(content)
        result = run_doctor(tmp_path)
        assert any("unrecognized model" in w.lower() for w in result.warnings)

    def test_full_id_accepted(self, tmp_path):
        generate_project(tmp_path)
        agent = next((tmp_path / ".claude" / "agents").glob("*.md"))
        content = agent.read_text()
        for alias in ("model: sonnet", "model: opus", "model: haiku"):
            content = content.replace(alias, "model: claude-opus-4-7")
        agent.write_text(content)
        result = run_doctor(tmp_path)
        warnings = [w for w in result.warnings if "unrecognized model" in w.lower()]
        assert not warnings, f"full ID should be accepted: {warnings}"

    def test_1m_variant_accepted(self, tmp_path):
        import re

        generate_project(tmp_path)
        agent = next((tmp_path / ".claude" / "agents").glob("*.md"))
        content = agent.read_text()
        # Replace any `model: <alias>` line (single regex pass; avoid chained
        # replaces that would re-match the inserted text).
        content = re.sub(
            r"^model: (sonnet|opus|haiku)$", "model: opus[1m]", content, flags=re.MULTILINE
        )
        agent.write_text(content)
        result = run_doctor(tmp_path)
        warnings = [w for w in result.warnings if "unrecognized model" in w.lower()]
        assert not warnings, f"[1m] variant should be accepted: {warnings}"


class TestDoctorPluginMarketplaceFormat:
    """v3.1 Check 20: enabledPlugins keys match name@marketplace."""

    def test_clean_settings_pass(self, tmp_path):
        import json

        generate_project(tmp_path)
        settings_path = tmp_path / ".claude" / "settings.json"
        # Ensure at least one plugin so the check has something to validate
        data = json.loads(settings_path.read_text())
        if not data.get("enabledPlugins"):
            data["enabledPlugins"] = {"github@claude-plugins-official": True}
        settings_path.write_text(json.dumps(data, indent=2))
        result = run_doctor(tmp_path)
        info = " ".join(result.info)
        assert "format clean" in info

    def test_malformed_key_warns(self, tmp_path):
        import json

        generate_project(tmp_path)
        settings_path = tmp_path / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())
        # No @marketplace suffix
        data["enabledPlugins"] = {"just-a-name": True}
        settings_path.write_text(json.dumps(data, indent=2))
        result = run_doctor(tmp_path)
        assert any("name@marketplace" in w for w in result.warnings)

    def test_uppercase_key_warns(self, tmp_path):
        import json

        generate_project(tmp_path)
        settings_path = tmp_path / ".claude" / "settings.json"
        data = json.loads(settings_path.read_text())
        data["enabledPlugins"] = {"BadName@marketplace": True}
        settings_path.write_text(json.dumps(data, indent=2))
        result = run_doctor(tmp_path)
        assert any("name@marketplace" in w for w in result.warnings)


class TestDoctorCLI:
    def test_doctor_runs(self, capsys, tmp_path):
        generate_project(tmp_path)
        rc = main(["doctor", "-d", str(tmp_path)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "passed" in captured.out.lower() or "warning" in captured.out.lower()

    def test_doctor_no_project(self, capsys, tmp_path):
        rc = main(["doctor", "-d", str(tmp_path)])
        assert rc == 1

    def test_doctor_fix_flag(self, capsys, tmp_path):
        generate_project(tmp_path)
        rc = main(["doctor", "--fix", "-d", str(tmp_path)])
        assert rc == 0
