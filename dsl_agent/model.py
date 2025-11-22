from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Transition:
    """Represents a reply and next action."""

    response: str
    next_state: Optional[str]  # None means end


@dataclass
class State:
    """Represents a conversation state and its intent routing."""

    name: str
    intents: Dict[str, Transition] = field(default_factory=dict)
    default: Transition = None  # type: ignore[assignment]

    def set_default(self, transition: Transition) -> None:
        if self.default is not None:
            raise ValueError(f"State '{self.name}' already has a default transition")
        self.default = transition


@dataclass
class Scenario:
    """Top-level scenario parsed from a DSL script."""

    name: str
    states: Dict[str, State]
    initial_state: str

    def get_state(self, name: str) -> State:
        try:
            return self.states[name]
        except KeyError as exc:
            raise KeyError(f"State '{name}' not found in scenario '{self.name}'") from exc
