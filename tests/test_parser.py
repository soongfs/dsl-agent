import pathlib

import pytest

from dsl_agent import parser
from dsl_agent.model import Scenario


def load_data(name: str) -> pathlib.Path:
    return pathlib.Path(__file__).parent / "data" / name


def test_parse_valid_demo_script():
    scenario = parser.parse_script(load_data("demo_bot.dsl"))
    assert isinstance(scenario, Scenario)
    assert scenario.name == "demo_bot"
    assert scenario.initial_state == "start"
    assert "routing" in scenario.states
    assert scenario.states["order"].default.response.startswith("请提供订单号")


def test_parse_refund_script():
    scenario = parser.parse_script(load_data("refund_bot.dsl"))
    assert scenario.name == "refund_bot"
    assert scenario.initial_state == "start"
    assert "wait_order" in scenario.states
    assert scenario.states["wait_reason"].default.response.startswith("请简要说明")


def test_parse_support_script():
    scenario = parser.parse_script(load_data("support_bot.dsl"))
    assert scenario.name == "support_bot"
    assert scenario.initial_state == "start"
    assert "triage" in scenario.states
    assert "confirm" in scenario.states


def test_missing_default_fails(tmp_path: pathlib.Path):
    bad_script = tmp_path / "bad.dsl"
    bad_script.write_text(
        'scenario x { state start { intent hi -> "hi" -> end; } }',
        encoding="utf-8",
    )
    with pytest.raises(parser.ParseError):
        parser.parse_script(bad_script)


def test_undefined_goto_fails(tmp_path: pathlib.Path):
    bad_script = tmp_path / "bad2.dsl"
    bad_script.write_text(
        'scenario x { state start { default -> "bye" -> goto nowhere; } }',
        encoding="utf-8",
    )
    with pytest.raises(parser.ParseError):
        parser.parse_script(bad_script)


def test_uppercase_identifier_fails(tmp_path: pathlib.Path):
    bad_script = tmp_path / "bad3.dsl"
    bad_script.write_text(
        'scenario Bad { state start { default -> "ok" -> end; } }',
        encoding="utf-8",
    )
    with pytest.raises(parser.ParseError):
        parser.parse_script(bad_script)


def test_multiple_defaults_fail(tmp_path: pathlib.Path):
    bad_script = tmp_path / "bad4.dsl"
    bad_script.write_text(
        'scenario x { state start { default -> "a" -> end; default -> "b" -> end; } }',
        encoding="utf-8",
    )
    with pytest.raises(parser.ParseError):
        parser.parse_script(bad_script)


def test_duplicate_state_names_fail(tmp_path: pathlib.Path):
    bad_script = tmp_path / "bad5.dsl"
    bad_script.write_text(
        'scenario x { state start { default -> "a" -> end; } state start { default -> "b" -> end; } }',
        encoding="utf-8",
    )
    with pytest.raises(parser.ParseError):
        parser.parse_script(bad_script)


def test_initial_refs_missing_state_fail(tmp_path: pathlib.Path):
    bad_script = tmp_path / "bad6.dsl"
    bad_script.write_text(
        'scenario x { initial nowhere; state start { default -> "a" -> end; } }',
        encoding="utf-8",
    )
    with pytest.raises(parser.ParseError):
        parser.parse_script(bad_script)


def test_implicit_initial_is_first_state(tmp_path: pathlib.Path):
    script = tmp_path / "good.dsl"
    script.write_text(
        'scenario x { state first { default -> "a" -> end; } state second { default -> "b" -> end; } }',
        encoding="utf-8",
    )
    scenario = parser.parse_script(script)
    assert scenario.initial_state == "first"


def test_missing_semicolon_fails(tmp_path: pathlib.Path):
    bad_script = tmp_path / "bad7.dsl"
    bad_script.write_text(
        'scenario x { state start { default -> "a" -> end } }',  # missing semicolon
        encoding="utf-8",
    )
    with pytest.raises(parser.ParseError):
        parser.parse_script(bad_script)
