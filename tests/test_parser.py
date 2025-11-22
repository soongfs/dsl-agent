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
    assert scenario.states["order"].default.response.startswith("Please give an order number")


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
