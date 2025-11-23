from __future__ import annotations

import asyncio
import logging
import re
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
    增强提示：只输出一个标签；不确定输出 none；附带可选意图描述。
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str,
        timeout: float = 15.0,
        max_tokens: int = 8,
        temperature: float = 0.0,
        max_retries: int = 1,
        intent_descriptions: Optional[Dict[str, str]] = None,
        client: Optional[OpenAI] = None,
    ) -> None:
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.intent_descriptions = intent_descriptions or {}
        self.client = client or OpenAI(api_key=api_key, base_url=api_base)

    async def identify(self, text: str, state: str, intents: List[str]) -> Optional[str]:
        sanitized = text.strip()[:200]
        prompt = self._build_prompt(state, intents, sanitized)
        content = await asyncio.to_thread(self._call_llm, prompt)
        if content is None:
            return None
        return self._normalize_result(content, intents)

    def _call_llm(self, prompt: str) -> Optional[str]:
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an intent classifier. "
                                "Pick exactly one label from the allowed list. "
                                "If unsure, answer 'none'. "
                                "Do not add punctuation or explanation."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    timeout=self.timeout,
                )
                return completion.choices[0].message.content
            except Exception as exc:  # pragma: no cover - network errors vary
                last_exc = exc
                logger.warning("LLM intent call failed (attempt %s): %s", attempt + 1, exc)
        if last_exc:
            logger.error("LLM intent call failed after retries: %s", last_exc)
        return None

    def _build_prompt(self, state: str, intents: List[str], text: str) -> str:
        # 构造带描述的意图列表
        parts = []
        for intent in intents:
            desc = self.intent_descriptions.get(intent, "")
            if desc:
                parts.append(f"{intent}: {desc}")
            else:
                parts.append(intent)
        intent_list = "; ".join(parts)
        return (
            f"Current state: {state}. Allowed intents: [{intent_list}]. "
            f"User said: \"{text}\". Respond with exactly one intent label from the allowed intents, "
            f"or 'none' if you are not sure."
        )

    def _normalize_result(self, content: str, intents: List[str]) -> Optional[str]:
        if content is None:
            return None
        normalized = content.strip().lower()
        if normalized == "none":
            return None
        if normalized in intents:
            return normalized
        # 只取第一个由字母数字下划线组成的 token
        tokens = re.findall(r"[a-z0-9_]+", normalized)
        if not tokens:
            return None
        first = tokens[0]
        if first in intents:
            return first
        return None
