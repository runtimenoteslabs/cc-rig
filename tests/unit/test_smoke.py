"""Smoke tests: import, version, CLI basics."""

import subprocess
import sys

import cc_rig
from cc_rig.cli import build_parser


def test_version_exists():
    assert hasattr(cc_rig, "__version__")
    assert isinstance(cc_rig.__version__, str)
    # Version should be a valid semver string
    parts = cc_rig.__version__.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_parser_version(capsys):
    parser = build_parser()
    try:
        parser.parse_args(["--version"])
    except SystemExit as e:
        assert e.code == 0
    captured = capsys.readouterr()
    assert "cc-rig" in captured.out
    assert cc_rig.__version__ in captured.out


def test_parser_subcommands():
    parser = build_parser()
    for cmd in ("init", "config", "preset", "doctor", "clean"):
        args = parser.parse_args([cmd])
        assert args.command == cmd


def test_parser_init_flags():
    parser = build_parser()
    args = parser.parse_args(
        [
            "init",
            "--template",
            "fastapi",
            "--workflow",
            "standard",
            "--name",
            "myproj",
            "-o",
            "/tmp/out",
        ]
    )
    assert args.template == "fastapi"
    assert args.workflow == "standard"
    assert args.name == "myproj"
    assert args.output == "/tmp/out"
    assert args.command == "init"


def test_python_m_cc_rig():
    result = subprocess.run(
        [sys.executable, "-m", "cc_rig", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert cc_rig.__version__ in result.stdout
