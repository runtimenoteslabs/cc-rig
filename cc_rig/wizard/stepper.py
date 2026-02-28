"""Step-based wizard engine with back navigation.

Provides a ``StepRunner`` that loops over ``WizardStep`` instances,
handling forward/back/cancel transitions and displaying progress.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from cc_rig.ui.prompts import IO


# ── Sentinel & types ──────────────────────────────────────────────


class _BackSentinel:
    """Sentinel value returned by prompts to signal 'go back'."""

    _instance: _BackSentinel | None = None

    def __new__(cls) -> _BackSentinel:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "BACK"

    def __bool__(self) -> bool:
        return False


BACK = _BackSentinel()


class StepAction(enum.Enum):
    """What happened after executing a step."""

    FORWARD = "forward"
    BACK = "back"
    CANCEL = "cancel"


@dataclass
class StepResult:
    """Result of executing a single wizard step."""

    action: StepAction = StepAction.FORWARD
    data: dict[str, Any] = field(default_factory=dict)


# ── WizardStep protocol ──────────────────────────────────────────


class WizardStep(Protocol):
    """Protocol that wizard steps must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def title(self) -> str: ...

    def execute(self, state: dict[str, Any], io: IO) -> StepResult: ...


# ── StepRunner ────────────────────────────────────────────────────


class StepRunner:
    """Run a list of steps with back/forward navigation.

    State is a shared dict that steps read from and write to.
    Going back restores the state snapshot taken *before* the
    step being returned to was originally executed.
    """

    def __init__(self, steps: list[WizardStep], io: IO) -> None:
        self._steps = steps
        self._io = io

    def run(self, state: dict[str, Any] | None = None) -> tuple[StepAction, dict[str, Any]]:
        """Execute steps in sequence.

        Returns:
            (final_action, final_state)  — FORWARD means the wizard
            completed; CANCEL means the user aborted.
        """
        state = state if state is not None else {}
        # Snapshots[i] = state copy *before* step i was executed.
        snapshots: list[dict[str, Any]] = []
        idx = 0

        while idx < len(self._steps):
            step = self._steps[idx]
            total = len(self._steps)

            # Show step indicator with separator
            self._io.say(f"\n{'─' * 40}")
            self._io.say(f"[{idx + 1}/{total}] {step.title}")

            # Save state snapshot before this step
            if idx >= len(snapshots):
                snapshots.append(_deep_copy_state(state))
            else:
                # Re-executing after back: overwrite snapshot
                snapshots[idx] = _deep_copy_state(state)

            result = step.execute(state, self._io)

            if result.action == StepAction.CANCEL:
                return StepAction.CANCEL, state

            if result.action == StepAction.BACK:
                if idx > 0:
                    idx -= 1
                    # Restore snapshot from before the step we're going back to
                    state = _deep_copy_state(snapshots[idx])
                # If already at first step, just re-run it
                continue

            # FORWARD — merge any data the step produced
            state.update(result.data)
            idx += 1

        return StepAction.FORWARD, state


def _deep_copy_state(state: dict[str, Any]) -> dict[str, Any]:
    """Shallow-copy the state dict (values are primitives or lists)."""
    out: dict[str, Any] = {}
    for k, v in state.items():
        if isinstance(v, list):
            out[k] = list(v)
        elif isinstance(v, dict):
            out[k] = dict(v)
        else:
            out[k] = v
    return out
