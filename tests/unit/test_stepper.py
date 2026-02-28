"""Tests for wizard step-based navigation: back, forward, cancel, state."""

from cc_rig.wizard.stepper import BACK, StepAction, StepResult, StepRunner
from tests.conftest import make_io as _make_io


class _FakeStep:
    """Configurable step for testing."""

    def __init__(self, name: str, title: str, results=None):
        self._name = name
        self._title = title
        self._results = iter(results or [StepResult()])
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def title(self) -> str:
        return self._title

    def execute(self, state, io):
        self.call_count += 1
        return next(self._results)


class TestStepRunner:
    def test_forward_through_all_steps(self):
        io = _make_io([])
        s1 = _FakeStep("a", "Step A", [StepResult(data={"x": 1})])
        s2 = _FakeStep("b", "Step B", [StepResult(data={"y": 2})])
        runner = StepRunner([s1, s2], io)
        action, state = runner.run()
        assert action == StepAction.FORWARD
        assert state == {"x": 1, "y": 2}
        assert s1.call_count == 1
        assert s2.call_count == 1

    def test_cancel_aborts(self):
        io = _make_io([])
        s1 = _FakeStep("a", "Step A", [StepResult(action=StepAction.CANCEL)])
        s2 = _FakeStep("b", "Step B")
        runner = StepRunner([s1, s2], io)
        action, state = runner.run()
        assert action == StepAction.CANCEL
        assert s2.call_count == 0

    def test_back_returns_to_previous(self):
        io = _make_io([])
        # Step 1 runs once forward, then re-runs after back
        s1 = _FakeStep(
            "a",
            "Step A",
            [
                StepResult(data={"x": 1}),
                StepResult(data={"x": 10}),
            ],
        )
        # Step 2 first sends BACK, then on re-visit goes forward
        s2 = _FakeStep(
            "b",
            "Step B",
            [
                StepResult(action=StepAction.BACK),
                StepResult(data={"y": 2}),
            ],
        )
        runner = StepRunner([s1, s2], io)
        action, state = runner.run()
        assert action == StepAction.FORWARD
        assert s1.call_count == 2
        assert s2.call_count == 2
        assert state["x"] == 10
        assert state["y"] == 2

    def test_back_at_first_step_re_runs(self):
        io = _make_io([])
        # First run returns BACK, second run goes forward
        s1 = _FakeStep(
            "a",
            "Step A",
            [
                StepResult(action=StepAction.BACK),
                StepResult(data={"done": True}),
            ],
        )
        runner = StepRunner([s1], io)
        action, state = runner.run()
        assert action == StepAction.FORWARD
        assert s1.call_count == 2
        assert state["done"] is True

    def test_state_restored_on_back(self):
        io = _make_io([])
        # Step A sets x=1
        s1 = _FakeStep(
            "a",
            "Step A",
            [
                StepResult(data={"x": 1}),
                StepResult(data={"x": 1}),
            ],
        )

        class _CheckStep:
            name = "b"
            title = "Step B"

            def __init__(self):
                self.seen_states = []
                self._calls = 0

            def execute(self, state, io):
                self.seen_states.append(dict(state))
                self._calls += 1
                if self._calls == 1:
                    # Mutate state then go back
                    state["mutated"] = True
                    return StepResult(action=StepAction.BACK)
                return StepResult(data={"y": 2})

        s2 = _CheckStep()
        runner = StepRunner([s1, s2], io)
        action, state = runner.run()
        assert action == StepAction.FORWARD
        # Second time step B sees state, 'mutated' should be gone
        # because state was restored from snapshot
        assert "mutated" not in s2.seen_states[1]

    def test_step_indicator_shown(self):
        io = _make_io([])
        s1 = _FakeStep("a", "Step A")
        s2 = _FakeStep("b", "Step B")
        runner = StepRunner([s1, s2], io)
        runner.run()
        output = "\n".join(io._output)
        assert "[1/2] Step A" in output
        assert "[2/2] Step B" in output
        assert "─" in output

    def test_empty_step_list(self):
        io = _make_io([])
        runner = StepRunner([], io)
        action, state = runner.run()
        assert action == StepAction.FORWARD
        assert state == {}

    def test_initial_state_preserved(self):
        io = _make_io([])

        class _ReadState:
            name = "reader"
            title = "Read"

            def __init__(self):
                self.saw = None

            def execute(self, state, io):
                self.saw = dict(state)
                return StepResult()

        s = _ReadState()
        runner = StepRunner([s], io)
        runner.run({"initial": True})
        assert s.saw["initial"] is True


class TestBACKSentinel:
    def test_back_is_singleton(self):
        from cc_rig.wizard.stepper import _BackSentinel

        assert BACK is _BackSentinel()

    def test_back_is_falsy(self):
        assert not BACK

    def test_back_repr(self):
        assert repr(BACK) == "BACK"
