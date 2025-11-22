from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


class IntentService(Protocol):
    async def identify(self, text: str, state: str, intents: List[str]) -> Optional[str]:
        """
        Return an intent label or None when unknown/unclassified.
        Implementations must not raise for normal uncertainty.
        """


class StubIntentService:
    """
    Deterministic intent resolver for tests and offline use.

    mapping: state -> (trigger -> intent)
    - If a trigger matches exactly the user text (case-sensitive), that intent is returned.
    - If no trigger matches, returns default_intent if provided; otherwise None.
    """

    def __init__(
        self,
        mapping: Optional[Dict[str, Dict[str, str]]] = None,
        default_intent: Optional[str] = None,
    ) -> None:
        self.mapping = mapping or {}
        self.default_intent = default_intent

    async def identify(self, text: str, state: str, intents: List[str]) -> Optional[str]:
        state_map = self.mapping.get(state, {})
        intent = state_map.get(text)
        if intent and intent in intents:
            return intent.lower()
        if self.default_intent and self.default_intent in intents:
            return self.default_intent.lower()
        return None


class LLMIntentService:
    """
    Placeholder LLM-backed intent classifier.

    In restricted/offline environments this returns None. To integrate a real model,
    implement the API call in `identify` using the provided configuration.
    """

    def __init__(self, api_base: str, api_key: str, model: str) -> None:
        self.api_base = api_base
        self.api_key = api_key
        self.model = model

    async def identify(self, text: str, state: str, intents: List[str]) -> Optional[str]:
        logger.warning("LLMIntentService is not implemented; returning None")
        await asyncio.sleep(0)  # make this a true coroutine
        return None
