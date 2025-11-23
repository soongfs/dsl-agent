from __future__ import annotations

import argparse
import configparser
import logging
import os
import pathlib
import select
import sys
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

    # welcome message per scenario: [welcome.<scenario>]
    welcomes: Dict[str, str] = {}
    welcome_prefix = "welcome."
    for section in config.sections():
        if section.startswith(welcome_prefix):
            scenario_name = section[len(welcome_prefix) :]
            # take first key/value as the message; or empty section -> skip
            if config[section]:
                # pick the first item
                first_key = next(iter(config[section]))
                welcomes[scenario_name] = config[section][first_key]
    if welcomes:
        data["welcome_messages"] = welcomes
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
        "welcome_messages": cfg.get("welcome_messages", {}),
        "log_file": cfg.get("log_file"),
        "idle_timeout": cfg.get("idle_timeout"),
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
    if args.log_file:
        settings["log_file"] = args.log_file
    if args.idle_timeout is not None:
        settings["idle_timeout"] = args.idle_timeout

    # environment overrides everything
    settings["api_base"] = os.getenv("DSL_API_BASE", settings.get("api_base"))
    settings["api_key"] = os.getenv("DSL_API_KEY", settings.get("api_key"))
    settings["model"] = os.getenv("DSL_MODEL", settings.get("model"))
    env_use_stub = os.getenv("DSL_USE_STUB")
    if env_use_stub is not None:
        settings["use_stub"] = _str_to_bool(env_use_stub, False)
    env_show_intent = os.getenv("DSL_SHOW_INTENT")
    if env_show_intent is not None:
        settings["show_intent"] = _str_to_bool(env_show_intent, False)
    env_idle = os.getenv("DSL_IDLE_TIMEOUT")
    if env_idle is not None:
        try:
            settings["idle_timeout"] = float(env_idle)
        except ValueError:
            logging.warning("Invalid DSL_IDLE_TIMEOUT value: %s", env_idle)

    settings["use_stub"] = _str_to_bool(str(settings.get("use_stub")) if settings.get("use_stub") is not None else None, False)
    settings["show_intent"] = _str_to_bool(str(settings.get("show_intent")) if settings.get("show_intent") is not None else None, False)
    # idle timeout: None or float seconds; <=0 disables
    try:
        if settings.get("idle_timeout") is not None:
            settings["idle_timeout"] = float(settings["idle_timeout"])
    except ValueError:
        logging.warning("Invalid idle_timeout config; disabling.")
        settings["idle_timeout"] = None

    return settings


def _build_intent_service(settings: Dict[str, Any], scenario_name: str) -> IntentService:
    if settings["use_stub"]:
        logging.info("Using stub intent service (use_stub=True)")
        return StubIntentService()
    api_base = settings.get("api_base") or ""
    api_key = settings.get("api_key") or ""
    model = settings.get("model") or ""
    if not (api_base and api_key and model):
        logging.warning("LLM settings incomplete; falling back to stub intent service")
        return StubIntentService()
    logging.info("Using LLM intent service model=%s api_base=%s", model, api_base)
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
    parser.add_argument("--log-file", dest="log_file", help="Write logs to file (console will show warnings only)")
    parser.add_argument(
        "--idle-timeout",
        type=float,
        help="Seconds to wait for user input before auto-triggering default (<=0 disables)",
    )
    parser.set_defaults(use_stub=None, show_intent=None)
    args = parser.parse_args()

    config_data = _load_config(args.config)
    settings = _resolve_settings(args, config_data)

    dsl_scenario = dsl_parser.parse_script(args.script)

    # 默认日志目录：项目当前工作目录下 logs/<scenario>.log
    if not settings.get("log_file"):
        default_log_dir = pathlib.Path.cwd() / "logs"
        default_log_dir.mkdir(parents=True, exist_ok=True)
        settings["log_file"] = str(default_log_dir / f"{dsl_scenario.name}.log")
    else:
        log_path = pathlib.Path(settings["log_file"])
        log_path.parent.mkdir(parents=True, exist_ok=True)

    log_handlers = []
    log_handlers.append(logging.FileHandler(settings["log_file"], encoding="utf-8"))
    console_handler = logging.StreamHandler()
    # 控制台仅显示警告以上，避免干扰对话输出
    console_handler.setLevel(logging.WARNING)
    log_handlers.append(console_handler)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=log_handlers,
    )

    intent_service = _build_intent_service(settings, scenario_name=dsl_scenario.name)
    bot = interpreter.Interpreter(dsl_scenario, intent_service)

    if settings.get("log_file"):
        print(f"[{dsl_scenario.name}] ready. Logs -> {settings['log_file']}. Type 'exit' to quit.")
    else:
        print(f"[{dsl_scenario.name}] ready. Type 'exit' to quit.")

    welcome = settings.get("welcome_messages", {}).get(dsl_scenario.name)
    if welcome:
        print(welcome)
    else:
        print(f"欢迎使用 {dsl_scenario.name}，请输入问题（输入 exit/quit 退出）。")
    idle_timeout = settings.get("idle_timeout")

    def read_input_with_timeout(prompt: str) -> Optional[str]:
        """Read a line with optional timeout. Return None on EOF."""
        if idle_timeout is None or idle_timeout <= 0:
            try:
                return input(prompt)
            except EOFError:
                return None
        # use select to wait for stdin
        print(prompt, end="", flush=True)
        rlist, _, _ = select.select([sys.stdin], [], [], idle_timeout)
        if not rlist:
            return ""  # timeout -> empty string to trigger default
        line = sys.stdin.readline()
        if not line:
            return None
        return line.rstrip("\n")

    while True:
        try:
            user_text = read_input_with_timeout("> ")
        except KeyboardInterrupt:
            print()
            break
        if user_text is None:
            print()
            break
        if user_text.strip().lower() in {"exit", "quit"}:
            break
        if user_text == "" and idle_timeout and idle_timeout > 0:
            # timeout path, log for debugging
            logging.info("Idle timeout %.2fs reached, triggering default flow", idle_timeout)
        reply = bot.process_input(user_text)
        print(reply)
        if settings["show_intent"]:
            logging.info("current_state=%s ended=%s", bot.current_state, bot.ended)
        if bot.ended:
            break

    print("Conversation ended.")


if __name__ == "__main__":
    run_cli()
