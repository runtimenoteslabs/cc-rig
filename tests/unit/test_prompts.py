"""Tests for UI prompts: IO injection, ask_choice, ask_input, confirm, ask_multi."""

from cc_rig.ui.prompts import ask_choice, ask_input, ask_multi, confirm
from cc_rig.wizard.stepper import BACK
from tests.conftest import make_io as _make_io


class TestAskChoice:
    def test_select_by_number(self):
        io = _make_io(["2"])
        result = ask_choice(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            io=io,
        )
        assert result == "b"

    def test_select_first(self):
        io = _make_io(["1"])
        result = ask_choice(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            io=io,
        )
        assert result == "a"

    def test_select_by_name(self):
        io = _make_io(["beta"])
        result = ask_choice(
            "Pick:",
            [("alpha", "Alpha"), ("beta", "Beta")],
            io=io,
        )
        assert result == "beta"

    def test_default_on_empty(self):
        io = _make_io([""])
        result = ask_choice(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            default="b",
            io=io,
        )
        assert result == "b"

    def test_invalid_then_valid(self):
        io = _make_io(["99", "1"])
        result = ask_choice(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            io=io,
        )
        assert result == "a"

    def test_back_returns_sentinel(self):
        io = _make_io(["back"])
        result = ask_choice(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            io=io,
            allow_back=True,
        )
        assert result is BACK

    def test_back_ignored_when_not_allowed(self):
        io = _make_io(["back", "1"])
        result = ask_choice(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            io=io,
            allow_back=False,
        )
        # "back" is not a valid selection, falls through to "1"
        assert result == "a"


class TestAskInput:
    def test_returns_input(self):
        io = _make_io(["my-project"])
        result = ask_input("Name", io=io)
        assert result == "my-project"

    def test_returns_default_on_empty(self):
        io = _make_io([""])
        result = ask_input("Name", default="fallback", io=io)
        assert result == "fallback"

    def test_strips_whitespace(self):
        io = _make_io(["  trimmed  "])
        result = ask_input("Name", io=io)
        assert result == "trimmed"

    def test_back_returns_sentinel(self):
        io = _make_io(["back"])
        result = ask_input("Name", io=io, allow_back=True)
        assert result is BACK

    def test_require_explicit_rejects_empty(self):
        io = _make_io(["", "actual-value"])
        result = ask_input("Name", default="fallback", io=io, require_explicit=True)
        assert result == "actual-value"

    def test_require_explicit_with_no_default(self):
        io = _make_io(["", "typed"])
        result = ask_input("Name", io=io, require_explicit=True)
        assert result == "typed"


class TestConfirm:
    def test_yes(self):
        io = _make_io(["y"])
        assert confirm("OK?", io=io) is True

    def test_no(self):
        io = _make_io(["n"])
        assert confirm("OK?", io=io) is False

    def test_default_yes(self):
        io = _make_io([""])
        assert confirm("OK?", default=True, io=io) is True

    def test_default_no(self):
        io = _make_io([""])
        assert confirm("OK?", default=False, io=io) is False

    def test_yes_full_word(self):
        io = _make_io(["yes"])
        assert confirm("OK?", io=io) is True

    def test_back_returns_sentinel(self):
        io = _make_io(["back"])
        result = confirm("OK?", io=io, allow_back=True)
        assert result is BACK


class TestAskMulti:
    def test_select_multiple(self):
        io = _make_io(["1,3"])
        result = ask_multi(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta"), ("c", "Charlie")],
            io=io,
        )
        assert result == ["a", "c"]

    def test_select_all(self):
        io = _make_io(["all"])
        result = ask_multi(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            io=io,
        )
        assert result == ["a", "b"]

    def test_select_none(self):
        io = _make_io(["none"])
        result = ask_multi(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            io=io,
        )
        assert result == []

    def test_defaults_on_empty(self):
        io = _make_io([""])
        result = ask_multi(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta"), ("c", "Charlie")],
            defaults=["a", "c"],
            io=io,
        )
        assert result == ["a", "c"]

    def test_invalid_then_valid(self):
        io = _make_io(["99", "1"])
        result = ask_multi(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            io=io,
        )
        assert result == ["a"]

    def test_back_returns_sentinel(self):
        io = _make_io(["back"])
        result = ask_multi(
            "Pick:",
            [("a", "Alpha"), ("b", "Beta")],
            io=io,
            allow_back=True,
        )
        assert result is BACK
