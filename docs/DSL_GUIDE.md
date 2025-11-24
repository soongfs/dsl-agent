# DSL 脚本编写指南

本指南说明如何编写本项目的 DSL 脚本，包括语法规则、使用方式和完整示例。

## 1. 脚本语法说明

- **整体结构**：以 `scenario <name> { ... }` 包裹，至少包含一个 `state`。
- **标识符**：场景/状态/意图名必须小写字母开头，可含数字和下划线（正则 `[a-z][a-z0-9_]*`）。关键字全部小写。
- **初始状态**：可选 `initial <state>;`，若省略则默认第一个声明的状态。
- **规则格式**：
  - 意图规则：`intent <intent_id> -> "<reply>" -> goto <state>;` 或 `... -> end;`
  - 默认规则：`default -> "<reply>" -> goto <state>;` 或 `... -> end;`
  - 每个状态**必须且仅能**有一个 `default`。
- **回复模板**：回复字符串内的 `{user_input}` 会被当前用户原始输入替换；仅支持此占位符。
- **保留字**：`scenario`/`state`/`intent`/`default`/`goto`/`end`/`initial` 不可作为标识符。
- **语法参考 (EBNF)**：

  ```plaintext
  Script       ::= "scenario" ScenarioID "{" InitialOpt StateList "}"
  InitialOpt   ::= "initial" StateID ";" | /* empty */
  StateList    ::= StateDef { StateDef }
  StateDef     ::= "state" StateID "{" RuleList "}"
  RuleList     ::= Rule { Rule }
  Rule         ::= IntentRule | DefaultRule
  IntentRule   ::= "intent" IntentID "->" String "->" NextAction ";"
  DefaultRule  ::= "default" "->" String "->" NextAction ";"
  NextAction   ::= "goto" StateID | "end"
  ```

## 2. 脚本用法说明

1) 编写脚本文件（`.dsl`），确保所有状态都有 `default`，所有 `goto` 目标已定义。
2) 可选在场景顶层声明 `initial` 指向起始状态，否则默认第一个状态。
3) 在回复中使用 `{user_input}` 可回显用户输入，其它占位符目前不支持。
4) 运行脚本（命令行）：

   ```bash
   python main.py path/to/your.dsl --config config.example.ini
   ```

   - 如无真实 LLM 配置，可加 `--use-stub` 使用桩意图；
   - 退出命令：在对话中输入 `exit` 或 `quit`。
5) 调试建议：先用简化脚本校验解析通过，再逐步增加状态和意图；运行时查看日志（默认 `logs/<scenario>.log`）确认意图与状态跳转。

## 3. 脚本范例

以下示例展示一个包含多状态的“出行/订单”场景，涵盖初始声明、意图分流、默认兜底和占位符：

```plaintext
scenario travel_bot {
    initial start;

    state start {
        intent greeting -> "您好，我能为您做什么？" -> goto routing;
        intent ask_order -> "好的，请提供您的订单号。" -> goto order;
        intent ask_flight -> "我可以帮您处理机票，请问目的地是哪里？" -> goto flight;
        default -> "我可以帮您查订单或预订机票，请问需要哪一项？" -> goto routing;
    }

    state routing {
        intent ask_order -> "好的，请提供您的订单号。" -> goto order;
        intent ask_flight -> "我可以帮您处理机票，请问目的地是哪里？" -> goto flight;
        default -> "我可以帮您查订单或预订机票，请问需要哪一项？" -> goto routing;
    }

    state order {
        intent provide_order -> "已收到订单号：{user_input}，正在为您查询..." -> end;
        default -> "请提供订单号（例如：2024-001）。" -> goto order;
    }

    state flight {
        intent provide_destination -> "目的地已记录：{user_input}。请问出行日期？" -> goto flight_date;
        default -> "请告诉我目的地城市。" -> goto flight;
    }

    state flight_date {
        intent provide_date -> "已收到日期 {user_input}，正在为您查询航班..." -> end;
        default -> "请提供日期，例如 2024-12-01。" -> goto flight_date;
    }
}
```

要增加新场景，只需复制此骨架并修改状态名、意图名与回复文案，确保仍满足：标识符小写、每状态唯一 `default`、所有跳转可达。
