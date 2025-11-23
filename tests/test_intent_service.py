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


class _DummyClient:
    def __init__(self, content: str):
        self.chat = _DummyChat(content)


def test_llm_intent_service_accepts_listed_intent(monkeypatch):
    client = _DummyClient("ask_order")
    svc = LLMIntentService(api_base="http://example", api_key="k", model="m", client=client)

    result = asyncio.run(svc.identify("我要查订单", "routing", ["ask_order", "ask_flight"]))
    assert result == "ask_order"


def test_llm_intent_service_tokenizes_and_strips(monkeypatch):
    client = _DummyClient("ask_order!!! extra text")
    svc = LLMIntentService(api_base="http://example", api_key="k", model="m", client=client)

    result = asyncio.run(svc.identify("hi", "routing", ["ask_order", "ask_flight"]))
    assert result == "ask_order"


def test_llm_intent_service_unknown_returns_none(monkeypatch):
    client = _DummyClient("none")
    svc = LLMIntentService(api_base="http://example", api_key="k", model="m", client=client)

    result = asyncio.run(svc.identify("hi", "start", ["greeting"]))
    assert result is None
