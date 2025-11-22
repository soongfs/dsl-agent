# DSL Agent

基于自定义 DSL 的多业务场景客服 Agent。解析 DSL 脚本并结合意图识别（默认桩服务，可接入 LLM）驱动对话。

## 快速开始

```bash
# 安装开发依赖（pytest 可选）
pip install -e .[dev]

# 运行示例脚本（使用桩意图服务）
python3 main.py tests/data/demo_bot.dsl --use-stub
```

退出命令：在 REPL 输入 `exit` 或 `quit`。

## 配置

优先级：环境变量 > CLI 参数 > 配置文件（示例见 `config.example.ini`）。

- 环境变量：`DSL_API_BASE`、`DSL_API_KEY`、`DSL_MODEL`、`DSL_USE_STUB`、`DSL_SHOW_INTENT`
- CLI 参数：`--script PATH`（位置参数）、`--config PATH`、`--use-stub/--no-stub`、`--show-intent`、`--api-base`、`--api-key`、`--model`
- 配置文件（可选 INI）示例：参考 `config.example.ini`

## 测试

```bash
python3 -m pytest
```

默认只依赖桩意图服务，无需外网。黄金用例与解析边界测试见 `tests/`。更多规范与设计细节参考 `docs/`。
