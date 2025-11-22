from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional, Protocol

from openai import OpenAI

logger = logging.getLogger(__name__)


class IntentService(Protocol):
    async def identify(self, text: str, state: str, intents: List[str]) -> Optional[str]:
        """
        返回意图标签或 None（未知/无法分类）。
        实现应对不确定性返回 None，而不是抛异常。
        """


class StubIntentService:
    """
    可配置的确定性意图解析，供测试/离线模式使用。

    mapping: state -> (trigger -> intent)
    - 完全匹配 trigger 返回对应 intent。
    - 无匹配则返回 default_intent（若提供且在 intents 中），否则 None。
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
    基于 OpenAI 兼容接口的意图分类实现（适配阿里云百炼/通义千问）。
    """

    def __init__(self, api_base: str, api_key: str, model: str, timeout: float = 15.0) -> None:
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.client = OpenAI(api_key=api_key, base_url=api_base)

    async def identify(self, text: str, state: str, intents: List[str]) -> Optional[str]:
        prompt = self._build_prompt(state, intents, text)
        try:
            # OpenAI SDK 目前为同步调用，这里直接在协程中调用；若需避免阻塞可改为 asyncio.to_thread
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intent classifier. Choose exactly one label from the provided list, or say 'none' if unknown."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=10,
                temperature=0,
                timeout=self.timeout,
            )
            content = completion.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("LLM intent call failed: %s", exc)
            return None

        normalized = content.lower().strip()
        if normalized in intents:
            return normalized
        # 有些模型可能返回带说明文字，尝试截取首个词
        first_token = normalized.split()[0]
        if first_token in intents:
            return first_token
        return None

    def _build_prompt(self, state: str, intents: List[str], text: str) -> str:
        options = ", ".join(intents)
        return (
            f"Current state: {state}. Allowed intents: [{options}]. "
            f"User said: \"{text}\". Reply with exactly one intent label from the list, "
            f"or 'none' if you are not sure."
        )
