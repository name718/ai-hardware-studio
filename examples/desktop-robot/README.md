# 桌面机器人 P0：四柱主控板托架

自然语言验收请求：“生成一个用于桌面机器人主控板的安装托架，带四个安装柱和螺丝孔。”

Agent 可按 `skills/parametric-cad-design/SKILL.md` 提取参数并调用 CAD MCP。本示例使用 `bracket.parameters.json`，全部尺寸均为虚构演示值，不对应真实 PCB。

当前 v0.2 的真实 MCP 运行证据见 `mcp-evidence.json`，交付位于 `verified/bb7fb002d21d49c2a7c3680a72aec71d/`。证据只保存相对构建路径，复制项目后仍可关联输出。旧版 `35852cab8dea41308d9221ef8b538097` 目录作为历史构建保留。

在浏览器直接打开 `preview.html` 查看离线三维网格；用 STEP 导入 CAD 编辑，STL 用于后续工艺检查。新版报告还包含实际孔/柱计量和逐项输入误差状态；演示尺寸误差为未知，Shapr3D 和实物装配尚未验证。

重新生成：

```bash
uv run --locked hardware-studio build examples/desktop-robot/bracket.parameters.json
uv run --locked python scripts/mcp_demo.py
```

返回的每次构建 ID 不同；源码、参数和依赖版本均保存在对应目录。检查通过不代表制造认证。
