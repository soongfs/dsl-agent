import pathlib
from typing import List, Tuple

from dsl_agent import parser
from dsl_agent.interpreter import Interpreter
from dsl_agent.intent_service import StubIntentService


def load_scenario(name: str):
    return parser.parse_script(pathlib.Path(__file__).parent / "data" / name)


def run_golden(
    scenario_name: str,
    steps: List[Tuple[str, str, str, bool]],
    intent_mapping,
):
    scenario = load_scenario(scenario_name)
    stub = StubIntentService(mapping=intent_mapping)
    bot = Interpreter(scenario, stub)

    for user_text, expect_reply_fragment, expect_state, expect_end in steps:
        reply = bot.process_input(user_text)
        assert expect_reply_fragment in reply
        assert bot.ended == expect_end
        if not bot.ended:
            assert bot.current_state == expect_state


def test_demo_bot_golden():
    steps = [
        ("hi", "您好，我能为您做什么？", "routing", False),
        ("order", "好的，请提供您的订单号。", "order", False),
        ("2024-001", "已收到订单号：2024-001", "order", True),
    ]
    mapping = {
        "start": {"hi": "greeting"},
        "routing": {"order": "ask_order"},
        "order": {"2024-001": "provide_order"},
    }
    run_golden("travel_bot.dsl", steps, mapping)


def test_refund_bot_golden():
    steps = [
        ("你好", "退款助手", "wait_order", False),
        ("2024-001", "已收到订单号", "wait_reason", False),
        ("质量问题", "已记录原因", "confirm", False),
        ("确认", "退款申请已提交", "confirm", True),
    ]
    mapping = {
        "start": {"你好": "greeting"},
        "wait_order": {"2024-001": "provide_order"},
        "wait_reason": {"质量问题": "provide_reason"},
        "confirm": {"确认": "confirm"},
    }
    run_golden("refund_bot.dsl", steps, mapping)


def test_support_bot_golden():
    steps = [
        ("你好", "技术支持", "triage", False),
        ("网络", "网络已连接", "confirm", False),
        ("未解决", "升级到人工", "confirm", True),
    ]
    mapping = {
        "start": {"你好": "greeting"},
        "triage": {"网络": "connectivity"},
        "confirm": {"未解决": "reject"},
    }
    run_golden("support_bot.dsl", steps, mapping)


def test_faq_bot_golden():
    steps = [
        ("你好", "常见问题助手", "faq", False),
        ("配送", "标准配送", "faq", True),
    ]
    mapping = {
        "start": {"你好": "greeting", "配送": "shipping"},
        "faq": {"配送": "shipping"},
    }
    run_golden("faq_bot.dsl", steps, mapping)


def test_appointment_bot_golden():
    steps = [
        ("你好", "预约助手", "service", False),
        ("医生", "预约医生", "date", False),
        ("2024-12-01", "收到日期", "confirm", False),
        ("确认", "已提交预约", "confirm", True),
    ]
    mapping = {
        "start": {"你好": "greeting"},
        "service": {"医生": "doctor"},
        "date": {"2024-12-01": "provide_date"},
        "confirm": {"确认": "confirm"},
    }
    run_golden("appointment_bot.dsl", steps, mapping)
