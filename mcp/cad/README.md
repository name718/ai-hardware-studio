# CAD MCP · 已实现

实现入口：`src/hardware_studio/cad/server.py`，启动：`uv run --locked cad-mcp`。

使用官方 MCP Python SDK，stdio 传输；无 HTTP 监听。输入输出 JSON Schema 由 Pydantic / FastMCP 自动生成。

工具：`cad_get_bracket_schema`、`cad_assess_parameters(parameters)`、`cad_build_bracket(parameters)`、`cad_get_build(build_id)`。
配置环境变量 `HARDWARE_STUDIO_ARTIFACT_ROOT`；详细调用与错误码见 `docs/installation.md`。

每项业务结果必须检查 `status`，不能只检查 MCP `isError`。

在目标电脑运行 `hardware-studio mcp-config` 生成本机配置。标准入口为 `python -m hardware_studio.cad.server`，不依赖 Docker 或开发者目录。
