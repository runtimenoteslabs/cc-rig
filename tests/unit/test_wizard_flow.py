"""Tests for wizard flows: guided, quick, expert, migrate."""

import json
from types import SimpleNamespace

from cc_rig.wizard.flow import run_wizard
from tests.conftest import make_io as _make_io


def _make_args(**kwargs):
    """Create a mock args namespace with defaults."""
    defaults = {
        "template": None,
        "workflow": None,
        "name": None,
        "output": None,
        "quick": False,
        "expert": False,
        "config": None,
        "migrate": False,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestZeroConfigFlow:
    def test_generates_output(self, tmp_path):
        output = tmp_path / "out"
        io = _make_io([])
        args = _make_args(
            template="fastapi",
            workflow="standard",
            name="test",
            output=str(output),
        )
        rc = run_wizard(args, io)
        assert rc == 0
        assert (output / "CLAUDE.md").exists()

    def test_error_on_bad_template(self, tmp_path):
        io = _make_io([])
        args = _make_args(
            template="nope",
            workflow="standard",
            output=str(tmp_path / "out"),
        )
        rc = run_wizard(args, io)
        assert rc == 1


class TestGuidedFlow:
    def test_full_guided_generates(self, tmp_path):
        output = tmp_path / "out"
        # Inputs: launcher, name, description, no-detection → template pick,
        # workflow pick, no-customize, no-harness, yes-generate
        io = _make_io(
            [
                "1",  # launcher: fresh project
                "my-project",  # project name
                "A test project",  # description
                "2",  # template: fastapi (index 2)
                "2",  # workflow: standard (index 2)
                "n",  # customize? no
                "n",  # add runtime harness? no
                "y",  # generate? yes
            ]
        )
        args = _make_args(output=str(output))
        rc = run_wizard(args, io)
        assert rc == 0
        assert (output / "CLAUDE.md").exists()
        data = json.loads((output / ".cc-rig.json").read_text())
        assert data["framework"] == "fastapi"
        assert data["workflow"] == "standard"

    def test_guided_cancel(self, tmp_path):
        output = tmp_path / "out"
        io = _make_io(
            [
                "1",  # launcher: fresh project
                "my-project",
                "",
                "1",  # template
                "1",  # workflow
                "n",  # customize? no
                "n",  # add runtime harness? no
                "n",  # generate? NO
            ]
        )
        args = _make_args(output=str(output))
        rc = run_wizard(args, io)
        assert rc == 0
        assert not (output / "CLAUDE.md").exists()


class TestQuickFlow:
    def test_quick_generates(self, tmp_path):
        output = tmp_path / "out"
        # Inputs: template pick, workflow pick, name
        io = _make_io(
            [
                "2",  # template: fastapi
                "2",  # workflow: standard
                "quick-proj",  # name
            ]
        )
        args = _make_args(quick=True, output=str(output))
        rc = run_wizard(args, io)
        assert rc == 0
        assert (output / "CLAUDE.md").exists()


class TestExpertFlow:
    def test_expert_with_no_customization(self, tmp_path):
        output = tmp_path / "out"
        # Guided flow + expert mode but decline all customization
        io = _make_io(
            [
                "1",  # launcher: fresh project
                "expert-proj",  # name
                "",  # description
                "2",  # template: fastapi
                "2",  # workflow: standard
                "n",  # customize agents? no
                "n",  # customize commands? no
                "n",  # customize hooks? no
                "n",  # customize features? no
                "n",  # customize permission? no
                "n",  # add runtime harness? no
                "y",  # generate? yes
            ]
        )
        args = _make_args(expert=True, output=str(output))
        rc = run_wizard(args, io)
        assert rc == 0
        assert (output / "CLAUDE.md").exists()


class TestConfigLoadFlow:
    def test_load_generates(self, tmp_path):
        # First create a config file
        output1 = tmp_path / "first"
        io1 = _make_io([])
        args1 = _make_args(
            template="gin",
            workflow="speedrun",
            name="gin-app",
            output=str(output1),
        )
        run_wizard(args1, io1)
        config_path = output1 / ".cc-rig.json"

        # Load it
        output2 = tmp_path / "second"
        io2 = _make_io([])  # no prompts needed for config load
        args2 = _make_args(
            config=str(config_path),
            output=str(output2),
        )
        rc = run_wizard(args2, io2)
        assert rc == 0
        assert (output2 / "CLAUDE.md").exists()


class TestMigrateFlow:
    def test_migrate_detects_python(self, tmp_path):
        # Create a python project marker
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        pyproject = project_dir / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "myapp"\n[project.dependencies]\nfastapi = ">=0.100"\n'
        )

        io = _make_io(["standard", "y"])  # pick workflow, confirm apply
        args = _make_args(migrate=True, output=str(project_dir))
        rc = run_wizard(args, io)
        assert rc == 0
        assert (project_dir / "CLAUDE.md").exists()

    def test_migrate_no_detection_falls_back_to_picker(self, tmp_path):
        # Empty dir: no framework detected, user picks template + workflow + confirms
        # Inputs: "fastapi" (template), "standard" (workflow), "y" (confirm)
        io = _make_io(["fastapi", "standard", "y"])
        args = _make_args(migrate=True, output=str(tmp_path))
        rc = run_wizard(args, io)
        assert rc == 0
        assert (tmp_path / "CLAUDE.md").exists()

    def test_migrate_no_detection_user_cancels(self, tmp_path):
        # Empty dir: no framework detected, user picks template + workflow, declines
        io = _make_io(["fastapi", "standard", "n"])
        args = _make_args(migrate=True, output=str(tmp_path))
        rc = run_wizard(args, io)
        assert rc == 0
        assert not (tmp_path / "CLAUDE.md").exists()
