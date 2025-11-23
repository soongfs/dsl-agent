import json
import pathlib
from typing import Any, Dict, List

from dsl_agent import parser
from dsl_agent.interpreter import Interpreter
from dsl_agent.intent_service import StubIntentService

DATA_DIR = pathlib.Path(__file__).parent / "data"


def load_case(name: str) -> Dict[str, Any]:
    with open(DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


def run_golden(case: Dict[str, Any]) -> None:
    scenario_file = case["scenario"]
    mapping = case["mapping"]
    steps: List[Dict[str, Any]] = case["steps"]

    scenario = parser.parse_script(DATA_DIR / scenario_file)
    stub = StubIntentService(mapping=mapping)
    bot = Interpreter(scenario, stub)

    for step in steps:
        reply = bot.process_input(step["user"])
        assert step["expect_reply"] in reply
        assert bot.ended == step["expect_end"]
        if not bot.ended:
            assert bot.current_state == step["expect_state"]


def test_travel_bot_golden():
    run_golden(load_case("golden_travel.json"))


def test_refund_bot_golden():
    run_golden(load_case("golden_refund.json"))


def test_support_bot_golden():
    run_golden(load_case("golden_support.json"))


def test_faq_bot_golden():
    run_golden(load_case("golden_faq.json"))


def test_appointment_bot_golden():
    run_golden(load_case("golden_appointment.json"))
