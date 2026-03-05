"""Tests for cc_rig/data/ JSON data files (commands.json, agents.json)."""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "cc_rig" / "data"

_COMMAND_REQUIRED_FIELDS = {"description", "allowed_tools", "body"}
_AGENT_REQUIRED_FIELDS = {"description", "model", "tools", "body"}
_AGENT_OPTIONAL_FIELDS = {
    "permission_mode",
    "max_turns",
    "background",
    "isolation",
    "agent_memory",
    "disallowed_tools",
}
_AGENT_ALL_FIELDS = _AGENT_REQUIRED_FIELDS | _AGENT_OPTIONAL_FIELDS


class TestCommandsJson:
    """Tests for commands.json data file."""

    def test_file_exists(self) -> None:
        assert (DATA_DIR / "commands.json").exists()

    def test_valid_json(self) -> None:
        data = json.loads((DATA_DIR / "commands.json").read_text())
        assert isinstance(data, dict)
        assert len(data) >= 19

    def test_schema(self) -> None:
        data = json.loads((DATA_DIR / "commands.json").read_text())
        for name, entry in data.items():
            assert isinstance(name, str), f"Key must be string: {name}"
            assert set(entry.keys()) == _COMMAND_REQUIRED_FIELDS, (
                f"Command {name!r} has unexpected fields: {set(entry.keys())}"
            )
            for field in _COMMAND_REQUIRED_FIELDS:
                assert isinstance(entry[field], str), f"Command {name!r}.{field} must be string"

    def test_round_trip(self) -> None:
        """Verify _load_command_defs() produces matching keys."""
        from cc_rig.generators.commands import _COMMAND_DEFS, _load_command_defs

        loaded = _load_command_defs()
        assert set(loaded.keys()) == set(_COMMAND_DEFS.keys())
        for name, (desc, tools, body) in loaded.items():
            assert isinstance(desc, str)
            assert isinstance(tools, str)
            assert isinstance(body, str)


class TestAgentsJson:
    """Tests for agents.json data file."""

    def test_file_exists(self) -> None:
        assert (DATA_DIR / "agents.json").exists()

    def test_valid_json(self) -> None:
        data = json.loads((DATA_DIR / "agents.json").read_text())
        assert isinstance(data, dict)
        assert len(data) >= 13

    def test_schema(self) -> None:
        data = json.loads((DATA_DIR / "agents.json").read_text())
        for name, entry in data.items():
            assert isinstance(name, str), f"Key must be string: {name}"
            for field in _AGENT_REQUIRED_FIELDS:
                assert field in entry, f"Agent {name!r} missing {field}"
                assert isinstance(entry[field], str), f"Agent {name!r}.{field} must be string"

    def test_no_unknown_fields(self) -> None:
        data = json.loads((DATA_DIR / "agents.json").read_text())
        for name, entry in data.items():
            extra = set(entry.keys()) - _AGENT_ALL_FIELDS
            assert not extra, f"Agent {name!r} has unknown fields: {extra}"

    def test_optional_fields_types(self) -> None:
        """Optional fields have correct types when present."""
        data = json.loads((DATA_DIR / "agents.json").read_text())
        for name, entry in data.items():
            if "permission_mode" in entry:
                assert isinstance(entry["permission_mode"], str)
            if "max_turns" in entry:
                assert isinstance(entry["max_turns"], int)
            if "background" in entry:
                assert isinstance(entry["background"], bool)
            if "isolation" in entry:
                assert isinstance(entry["isolation"], str)
            if "agent_memory" in entry:
                assert isinstance(entry["agent_memory"], str)
            if "disallowed_tools" in entry:
                assert isinstance(entry["disallowed_tools"], str)

    def test_round_trip(self) -> None:
        """Verify _load_agent_defs() produces matching keys and types."""
        from cc_rig.generators.agents import _AGENT_DEFS, AgentDef, _load_agent_defs

        loaded = _load_agent_defs()
        assert set(loaded.keys()) == set(_AGENT_DEFS.keys())
        for name, defn in loaded.items():
            assert isinstance(defn, AgentDef)
            assert isinstance(defn.description, str)
            assert isinstance(defn.model, str)
            assert isinstance(defn.tools, str)
            assert isinstance(defn.body, str)

    def test_parallel_worker_has_optional_fields(self) -> None:
        """parallel-worker agent should have background and isolation set."""
        data = json.loads((DATA_DIR / "agents.json").read_text())
        pw = data.get("parallel-worker")
        assert pw is not None
        assert pw["background"] is True
        assert pw["isolation"] == "worktree"
