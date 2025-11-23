import pathlib

import pytest

from dsl_agent import parser
from dsl_agent.intent_service import StubIntentService
from dsl_agent.interpreter import Interpreter


def load_scenario(name: str):
    path = pathlib.Path(__file__).parent / "data" / name
    return parser.parse_script(path)


def test_happy_path_and_end():
    scenario = load_scenario("travel_bot.dsl")
    stub = StubIntentService(
        mapping={
            "start": {"hi": "greeting"},
            "routing": {"order": "ask_order"},
            "order": {"123": "provide_order"},
        }
    )
    bot = Interpreter(scenario, stub)

    reply1 = bot.process_input("hi")
    assert "您好" in reply1
    assert bot.current_state == "routing"
    assert not bot.ended

    reply2 = bot.process_input("order")
    assert "订单号" in reply2
    assert bot.current_state == "order"

    reply3 = bot.process_input("123")
    assert "123" in reply3  # templating
    assert bot.ended is True

    with pytest.raises(RuntimeError):
        bot.process_input("anything")


def test_default_and_loop():
    scenario = load_scenario("travel_bot.dsl")
    stub = StubIntentService(mapping={})
    bot = Interpreter(scenario, stub)

    reply = bot.process_input("???")
    assert "哪一项" in reply  # default in start
    assert bot.current_state == "routing"
    assert bot.ended is False


def test_reset():
    scenario = load_scenario("travel_bot.dsl")
    stub = StubIntentService(mapping={"start": {"hi": "greeting"}})
    bot = Interpreter(scenario, stub)

    bot.process_input("hi")
    assert bot.current_state == "routing"
    bot.reset()
    assert bot.current_state == scenario.initial_state
    assert bot.ended is False
