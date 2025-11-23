# 测试计划（最终版）

本计划是 DSL Agent 的权威测试策略，覆盖解析器校验、解释器+桩行为、黄金用例集成。测试主要用 Python（pytest 风格），依赖 `ARCHITECTURE.md` 的接口与 `DSL_SPEC.md` 的语法。

## 范围与目标

- 校验 DSL 解析正确性与语义验证。
- 使用桩意图服务验证解释器的状态迁移、default、模板替换与结束逻辑。
- 针对示例 DSL 脚本验证端到端对话（golden run）。
- 确保本地/CI 可在无真实 LLM 的情况下运行（默认仅桩）。

## 测试类型

### 1) 解析器单元测试

场景（除标注外均期望抛 `ParseError`）：

- **合法最小脚本**：单状态、含 default，可有 initial；应得到正确 `initial_state` 的 `Scenario`。
- **隐式初始**：无 `initial` 指令，初始为首个 state。
- **缺失 default**：状态无 `default` -> 失败。
- **重复 default**：同一状态多条 `default` -> 失败。
- **未定义 goto**：`goto` 指向不存在的状态 -> 失败。
- **未定义 initial**：`initial` 指向不存在的状态 -> 失败。
- **大写 ID**：含大写字母的标识符按小写规则应失败。
- **语法错误**：缺分号、缺括号、错误字符串等 -> 带行列信息失败。
- **重复状态名**：可选检查；决定拒绝或后者覆盖，需与实现保持一致并测试。

### 2) 解释器 + 桩 测试

准备：加载小型 DSL 脚本，使用可配置映射的 `StubIntentService`。断言：

- **正常意图匹配**：已知意图跳转到预期状态并返回正确回复。
- **未知走 default**：`identify` 返回 `None`/空/不在列表 -> 使用 default 迁移。
- **模板替换**：含 `{user_input}` 的回复用原始输入替换。
- **goto 自身**：状态不变，`ended` 仍为 False。
- **结束迁移**：`end` 将 `ended=True`，回复返回一次。
- **结束后调用**：`ended=True` 时调用 `process_input` 抛 `RuntimeError`。
- **重置**：多次迁移后 `reset()` 恢复初始状态并清除 `ended`。

### 3) 黄金用例（Golden Run）集成

目的：确保脚本对话转录稳定。用桩的意图序列强制确定性。

- **示例脚本**：使用已提供的示例（如 `travel_bot`、`refund_bot`、`support_bot`、`faq_bot`、`appointment_bot`），可按需补充。
- **方法**：预设列表 `(user_input, expected_intent, expected_reply, expected_state_after, ended_flag)`；驱动解释器并逐步断言。
- **输出**：期望转录存为 fixture（golden 文件），比较实际回复/状态，变更需显式更新并评审。
- **负向路径**：包含桩返回未知意图的步骤，确认走 default 分支。

### 4)（可选）LLM 冒烟

不纳入 CI；有密钥时可手工运行。用 `LLMIntentService` 简短提示，验证能返回有效意图。受环境变量保护，避免不稳定。

## 自动化与工具

- **测试运行**：`pytest`（或 `python -m pytest`），测试放在 `tests/`。
- **Fixtures**：辅助加载 `tests/data/*.dsl`；桩意图映射由 fixture 注入。
- **黄金比较**：转录存文本/json fixture；测试生成实际值、比对并在失败时显示 diff。
- **CI 默认**：仅跑桩相关测试；除非设置 `DSL_LLM_SMOKE=1` 且有密钥，否则跳过 LLM 冒烟。

## 退出准则

- 解析器单测覆盖合法与错误路径全部通过。
- 解释器+桩测试覆盖 default、模板、循环、结束/重置语义。
- 示例脚本的黄金用例匹配预期转录。
- 默认无外部网络依赖的测试均通过。
