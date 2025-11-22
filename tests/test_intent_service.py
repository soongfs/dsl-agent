import asyncio

from dsl_agent.intent_service import LLMIntentService


class _DummyResp:
    def __init__(self, content: str):
        self.choices = [type("Choice", (), {"message": type("Msg", (), {"content": content})})()]


class _DummyCompletions:
    def __init__(self, content: str):
        self._content = content

    def create(self, **_: object):
        return _DummyResp(self._content)


class _DummyChat:
    def __init__(self, content: str):
        self.completions = _DummyCompletions(content)


def test_llm_intent_service_accepts_listed_intent(monkeypatch):
    svc = LLMIntentService(api_base="http://example", api_key="k", model="m")
    # 替换 client.chat 以避免真实网络调用
    svc.client.chat = _DummyChat("ask_order")

    result = asyncio.run(svc.identify("我要查订单", "routing", ["ask_order", "ask_flight"]))
    assert result == "ask_order"


def test_llm_intent_service_unknown_returns_none(monkeypatch):
    svc = LLMIntentService(api_base="http://example", api_key="k", model="m")
    svc.client.chat = _DummyChat("unknown_label")

    result = asyncio.run(svc.identify("hi", "start", ["greeting"]))
    assert result is None
