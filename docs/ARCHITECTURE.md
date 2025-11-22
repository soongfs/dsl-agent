# 系统架构（最终版）

本文件为 DSL 多业务场景客服 Agent 的权威设计说明，定义模块职责、接口、行为与 LLM 抽象，严格对应最终 DSL 规范。

## 模块职责

- **parser**：词法/语法解析 DSL 并生成运行时结构，做语义校验（初始状态、每状态唯一 default、`goto` 目标存在）。
- **model (ast/runtime)**：`Scenario`、`State`、`Transition` 等数据类，供解释器与测试使用。
- **interpreter**：基于 `Scenario` 驱动对话，调用意图服务，执行规则、回复和状态迁移，跟踪结束态。
- **intent_service**：意图分类抽象，提供真实 LLM 客户端与桩实现。
- **cli/main**：入口，加载配置和脚本，构建服务，运行 REPL，对接日志和退出命令。
- **config/logging**：处理配置（环境变量 > CLI 参数 > 配置文件），初始化日志（不泄露密钥），向意图服务传递 LLM 设置。

## 数据结构

```python
class Transition:
    response: str          # raw reply template, may contain {user_input}
    next_state: str | None # state id or None to signal end

class State:
    name: str
    intents: dict[str, Transition]      # intent -> transition
    default: Transition                 # required

class Scenario:
    name: str
    states: dict[str, State]            # state_id -> State
    initial_state: str
```

## 接口定义

### Parser

```python
class ParseError(Exception): pass

def parse_script(path: str) -> Scenario
```

- **输入**：DSL 文件路径。
- **输出**：`Scenario` 实例。
- **校验**：以下情况抛 `ParseError`（含消息与行列号）：
  - 语法错误；
  - 无状态；
  - 某状态缺失或重复 `default`；
  - `goto` 指向未定义状态；
  - 初始状态未定义（显式或推断）。
- **语义**：强制小写标识符（见 DSL 规范），无 `initial` 时默认首个 state。

### 意图服务抽象

```python
class IntentService:
    async def identify(self, text: str, state: str, intents: list[str]) -> str | None: ...
```

- **契约**：返回意图标签字符串，未知/无法分类返回 `None`，不因模型不确定性抛异常。
- **归一化**：实现需小写化输出，仅接受提供的 `intents` 内的标签，否则返回 `None`。

实现：

- **StubIntentService**：可配置的确定性映射（如关键词规则），用于测试。
- **LLMIntentService**：封装真实 API（如兼容 OpenAI 的 Qwen 端点）。需 `api_base`、`api_key`、`model`。API 错误时记录日志并返回 `None`，不向解释器抛出。

### Interpreter

```python
class Interpreter:
    def __init__(self, scenario: Scenario, intent_service: IntentService):
        ...

    def process_input(self, user_text: str) -> str
    def reset(self) -> None

    @property
    def current_state(self) -> str

    @property
    def ended(self) -> bool
```

- **行为**：
  1) 若 `ended` 为 `True`，`process_input` 抛 `RuntimeError`。
  2) 调用 `intent_service.identify(user_text, current_state, available_intents)`，结果小写化。
  3) 若结果为 `None`、空字符串或不在当前状态 intents 中，则走 `default` 迁移。
  4) 回复 = 迁移的 response，并用原始 `user_text` 替换 `{user_input}`。
  5) 若 `next_state` 为 `None`（表示 `end`），设置 `ended=True`；否则更新为该状态。
  6) 返回回复字符串。
- **循环**：允许 `goto` 自身（不改变状态）。
- **状态可见性**：`current_state` 属性用于调试/测试。
- **重置**：`reset()` 恢复初始状态并清除 `ended`。

### CLI / Main

- 解析 CLI 参数：`--script PATH`、`--config PATH`、`--use-stub`、`--show-intent`（调试）、`--api-base`、`--api-key`、`--model`。
- 配置优先级：环境变量 > CLI 参数 > 配置文件默认。
- 构建 `IntentService`（桩或 LLM），解析 DSL，实例化 `Interpreter`。
- REPL 流程：打印欢迎；读输入；检测退出命令（`exit`/`quit`）；调用 `process_input`；输出回复；当 `ended` 为 True 结束。
- 日志：记录输入、识别/返回意图（开启 `--show-intent` 或调试时）、状态迁移。密钥绝不写日志。

## 错误处理与不变式

- 解析器保证结构不变式：
  - 至少一个状态；
  - 每状态唯一 default；
  - 所有 `goto` 目标存在。
- 解释器在运行时异常场景走 default；唯一致命错误是结束后调用 `process_input`。
- 意图服务对网络/API 故障做屏蔽，返回 `None`。

## 配置提示

- 环境变量：`DSL_API_BASE`、`DSL_API_KEY`、`DSL_MODEL`、`DSL_USE_STUB`。
- 可选配置文件（INI/JSON），字段与 CLI 名称对应。
- 桩配置可包含按状态的意图映射，便于测试。

## 日志

- 最少字段：时间戳、state_before、user_input、identified_intent（或 `none`）、chosen_transition、state_after、ended_flag。
- API 响应/trace 仅在 debug，密钥打码。

## 扩展提示

- 若需更多模板能力，可扩展解释器替换逻辑；当前仅支持 `{user_input}`。
- 若需埋点，可在解释器外围包装，不改核心接口。
