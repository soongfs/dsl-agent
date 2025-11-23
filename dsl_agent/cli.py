from __future__ import annotations

import argparse
import configparser
import logging
import os
import pathlib
from typing import Any, Dict, Optional

from . import interpreter
from . import parser as dsl_parser
from .intent_service import IntentService, LLMIntentService, StubIntentService


def _str_to_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_config(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    config = configparser.ConfigParser()
    config.read(path)
    data: Dict[str, Any] = {}
    if "llm" in config:
        data.update(config["llm"])
    if "settings" in config:
        data.update(config["settings"])
    # intent_descriptions sections: [intent_descriptions.<scenario>]
    descriptions: Dict[str, Dict[str, str]] = {}
    prefix = "intent_descriptions."
    for section in config.sections():
        if section.startswith(prefix):
            scenario_name = section[len(prefix) :]
            descriptions[scenario_name] = dict(config[section])
    if descriptions:
        data["intent_descriptions"] = descriptions
    return data


def _resolve_settings(args: argparse.Namespace, cfg: Dict[str, Any]) -> Dict[str, Any]:
    # config -> CLI -> env (env has highest priority)
    settings: Dict[str, Any] = {
        "api_base": cfg.get("api_base"),
        "api_key": cfg.get("api_key"),
        "model": cfg.get("model"),
        "use_stub": cfg.get("use_stub"),
        "show_intent": cfg.get("show_intent"),
        "intent_descriptions": cfg.get("intent_descriptions", {}),
    }

    if args.api_base:
        settings["api_base"] = args.api_base
    if args.api_key:
        settings["api_key"] = args.api_key
    if args.model:
        settings["model"] = args.model
    if args.use_stub is not None:
        settings["use_stub"] = args.use_stub
    if args.show_intent is not None:
        settings["show_intent"] = args.show_intent

    # environment overrides everything
    settings["api_base"] = os.getenv("DSL_API_BASE", settings.get("api_base"))
    settings["api_key"] = os.getenv("DSL_API_KEY", settings.get("api_key"))
    settings["model"] = os.getenv("DSL_MODEL", settings.get("model"))
    env_use_stub = os.getenv("DSL_USE_STUB")
    if env_use_stub is not None:
        settings["use_stub"] = _str_to_bool(env_use_stub, True)
    env_show_intent = os.getenv("DSL_SHOW_INTENT")
    if env_show_intent is not None:
        settings["show_intent"] = _str_to_bool(env_show_intent, False)

    settings["use_stub"] = _str_to_bool(str(settings.get("use_stub")) if settings.get("use_stub") is not None else None, True)
    settings["show_intent"] = _str_to_bool(str(settings.get("show_intent")) if settings.get("show_intent") is not None else None, False)

    return settings


def _build_intent_service(settings: Dict[str, Any], scenario_name: str) -> IntentService:
    if settings["use_stub"]:
        return StubIntentService()
    api_base = settings.get("api_base") or ""
    api_key = settings.get("api_key") or ""
    model = settings.get("model") or ""
    if not (api_base and api_key and model):
        logging.warning("LLM settings incomplete; falling back to stub intent service")
        return StubIntentService()
    desc_all = settings.get("intent_descriptions") or {}
    intent_descriptions = desc_all.get(scenario_name, {})
    return LLMIntentService(
        api_base=api_base,
        api_key=api_key,
        model=model,
        intent_descriptions=intent_descriptions,
    )


def run_cli() -> None:
    parser = argparse.ArgumentParser(description="DSL Agent CLI")
    parser.add_argument("script", help="Path to DSL script file")
    parser.add_argument("--config", help="Optional config file (ini)")
    parser.add_argument("--use-stub", dest="use_stub", action="store_true", help="Force stub intent service")
    parser.add_argument("--no-stub", dest="use_stub", action="store_false", help="Disable stub (use LLM)")
    parser.add_argument("--show-intent", dest="show_intent", action="store_true", help="Show identified intent in logs")
    parser.add_argument("--api-base", help="LLM API base URL")
    parser.add_argument("--api-key", help="LLM API key")
    parser.add_argument("--model", help="LLM model name")
    parser.set_defaults(use_stub=None, show_intent=None)
    args = parser.parse_args()

    config_data = _load_config(args.config)
    settings = _resolve_settings(args, config_data)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    dsl_scenario = dsl_parser.parse_script(args.script)
    intent_service = _build_intent_service(settings, scenario_name=dsl_scenario.name)
    bot = interpreter.Interpreter(dsl_scenario, intent_service)

    print(f"[{dsl_scenario.name}] ready. Type 'exit' to quit.")
    while True:
        try:
            user_text = input("> ")
        except EOFError:
            print()
            break
        if user_text.strip().lower() in {"exit", "quit"}:
            break
        reply = bot.process_input(user_text)
        print(reply)
        if settings["show_intent"]:
            logging.info("current_state=%s ended=%s", bot.current_state, bot.ended)
        if bot.ended:
            break

    print("Conversation ended.")


if __name__ == "__main__":
    run_cli()
