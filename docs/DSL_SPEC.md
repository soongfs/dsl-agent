# DSL 规格说明（最终版）

本文档是本项目客服 DSL 的权威规范，整合需求与审查结论，供解析器、解释器与脚本作者使用。

## 语言规则

- **大小写**：关键字仅小写（`scenario`、`state`、`intent`、`default`、`goto`、`end`、`initial`）。标识符（场景/状态/意图名）必须为小写字母数字加下划线（`[a-z][a-z0-9_]*`）。解释器会对 LLM 输出做小写化匹配，因此脚本 ID 必须小写。
- **初始状态**：推荐使用顶层指令 `initial <state_id>;` 显式声明；若省略，则默认第一个声明的 `state` 为初始状态。解析器会校验初始状态存在。
- **default 规则**：每个 `state` **必须且仅能** 有一个 `default` 规则。缺失将被解析器拒绝。当无意图匹配或意图未知/为空时使用 default。
- **`{user_input}` 模板**：回复字符串支持字面量 `{user_input}` 替换为本轮原始用户输入。仅支持这一变量，不提供转义——除非希望被替换，否则避免写出该字面量。
- **保留字**：`scenario`、`state`、`intent`、`default`、`goto`、`end`、`initial` 为保留字，不能作为标识符。

## 语法（EBNF）

```ebnf
Script       ::= "scenario" ScenarioID "{" InitialOpt StateList "}"
InitialOpt   ::= "initial" StateID ";" | /* empty -> first state is initial */
StateList    ::= StateDef { StateDef }
StateDef     ::= "state" StateID "{" RuleList "}"
RuleList     ::= Rule { Rule }
Rule         ::= IntentRule | DefaultRule
IntentRule   ::= "intent" IntentID "->" String "->" NextAction ";"
DefaultRule  ::= "default" "->" String "->" NextAction ";"
NextAction   ::= "goto" StateID | "end"

ScenarioID   ::= ID
StateID      ::= ID
IntentID     ::= ID
ID           ::= /[a-z][a-z0-9_]*/
String       ::= '"' ( '\' '"' | . )* '"'   // supports \" escape
```

### 语义

- 进入某 `state` 时，解释器调用 LLM/桩获取意图标签，转为小写后在该状态的 `intent` 规则中匹配。
- 若命中 intent 规则，输出其回复并执行 `NextAction`：
  - `goto X`：跳转到状态 `X`，允许跳回自身。
  - `end`：回复后结束对话。
- 若未命中任何 intent，则使用 `default` 规则的回复与动作。
- 回复可含 `{user_input}`，由本轮原始用户输入替换。
- 脚本至少包含一个 state。所有 `goto` 目标必须是已声明状态（解析器校验）。

## 使用指南

### 最小脚本模板

```plaintext
scenario demo_bot {
    initial start;

    state start {
        intent greeting -> "Hello! What can I do for you?" -> goto routing;
        default -> "Sorry, I missed that. How can I help?" -> goto start;
    }

    state routing {
        intent ask_order -> "Sure, please provide your order number." -> goto order;
        intent ask_flight -> "I can help with flights. Where are you flying to?" -> goto flight;
        default -> "I can help with orders or flights. Which one?" -> goto routing;
    }

    state order {
        intent provide_order -> "Got it: {user_input}. Checking status..." -> end;
        default -> "Please give an order number (e.g., 2024-001)." -> goto order;
    }

    state flight {
        intent provide_destination -> "Destination noted: {user_input}. What date?" -> goto flight_date;
        default -> "Tell me your destination city." -> goto flight;
    }

    state flight_date {
        intent provide_date -> "Date {user_input} received. Booking now..." -> end;
        default -> "Please give a date like 2024-12-01." -> goto flight_date;
    }
}
```

### 编写要点

- 标识符保持小写以配合解析与意图归一化。
- 每个状态确保有且仅有一个 `default` 规则，提供兜底。
- 建议显式写出 `initial`，否则默认首个 state 为初始。
- `{user_input}` 仅用于简单回显，无其他模板功能。
- 及早用解析器校验；缺失 default、未知 `goto`、语法错误都会快速失败。
