from __future__ import annotations

import asyncio
import inspect
import logging
from typing import List, Optional

from .intent_service import IntentService
from .model import Scenario, State, Transition

logger = logging.getLogger(__name__)


class Interpreter:
    def __init__(self, scenario: Scenario, intent_service: IntentService):
        self.scenario = scenario
        self.intent_service = intent_service
        self._current_state = scenario.initial_state
        self._ended = False

    @property
    def current_state(self) -> str:
        return self._current_state

    @property
    def ended(self) -> bool:
        return self._ended

    def reset(self) -> None:
        self._current_state = self.scenario.initial_state
        self._ended = False

    def process_input(self, user_text: str) -> str:
        if self._ended:
            raise RuntimeError("Conversation already ended")

        state = self.scenario.get_state(self._current_state)
        available_intents: List[str] = list(state.intents.keys())
        intent = self._resolve_intent(user_text, state.name, available_intents)
        transition: Transition

        if intent and intent in state.intents:
            transition = state.intents[intent]
            matched = intent
        else:
            transition = state.default
            matched = "default"

        reply = transition.response.replace("{user_input}", user_text)

        if transition.next_state is None:
            self._ended = True
            next_state = None
        else:
            next_state = transition.next_state
            self._current_state = next_state

        logger.info(
            "state=%s intent=%s next=%s ended=%s",
            state.name,
            matched,
            next_state if next_state is not None else "end",
            self._ended,
        )
        return reply

    def _resolve_intent(self, user_text: str, state: str, intents: List[str]) -> Optional[str]:
        result = self.intent_service.identify(user_text, state, intents)
        if inspect.isawaitable(result):
            result = asyncio.run(result)
        if result is None:
            return None
        normalized = result.strip().lower()
        if not normalized:
            return None
        return normalized
