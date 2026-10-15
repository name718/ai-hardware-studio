# 安装与调用

## 环境

当前只支持 **macOS arm64（Apple Silicon）与 Python 3.12**，其他系统不作为本阶段目标。终端和项目 Python 应原生运行，避免通过 Rosetta 使用 x86_64 解释器。Python 3.13 的锁定 VTK 组合不受本项目支持。

项目不依赖开发者电脑或 Docker。另一台 macOS arm64 电脑仍需重新安装原生依赖；不要复制开发电脑的 `.venv`。CI 已收敛为 macOS，环境检查会拒绝不受支持的系统与解释器架构。

```bash
uv sync --locked --extra dev
uv run --locked hardware-studio doctor
uv run --locked hardware-studio schema
uv run --locked hardware-studio build examples/desktop-robot/bracket.parameters.json
```

不使用 uv 时可在 Python 3.12 虚拟环境中 `pip install -e '.[dev]'`，但这不会使用 uv.lock 的完整锁定版本。

## 环境检查脚本

源码包自带的检查脚本可以在任意工作目录运行，不会自动安装软件或启动桌面应用：

```bash
bash scripts/check_environment.sh
```

它检查 macOS arm64、uv、项目 `.venv`、Python 3.12、解释器架构及 CadQuery/OpenCascade/MCP/Pydantic 包。缺少环境时输出 `[FAIL]` 和准备命令；成功退出码为 0，失败为 1。KiCad 和 PlatformIO 只是可选工具发现，缺少它们不阻断当前 CAD 阶段。

安装依赖后，可以进一步执行真实 CAD 环境检查：

```bash
bash scripts/check_environment.sh --probe-cad
```

完整检查实际构建虚构演示托架，导出 STEP/STL、回读 STEP、核验文件哈希，并将报告保存到该项目的 `artifacts/cad/<build_id>`。默认基础检查只读取环境信息，不创建 CAD 产物。首次原生库加载可能较慢。

只安装 wheel 时，可用等价入口：

```bash
hardware-studio doctor
hardware-studio doctor --probe-cad
```

完整检查的通过只证明本地 CAD 运行环境可用，不代表已经连接 Agent 客户端，也不代表真实 PCB 适配。

## MCP 客户端

在目标电脑安装后，运行以下命令生成适合该电脑的配置，然后把输出的 `mcpServers` 条目加入支持 stdio 的客户端：

```bash
uv run --locked hardware-studio mcp-config
```

该命令只输出 JSON，不修改客户端配置。它使用目标电脑当前环境的 Python 和自动选择的数据目录，不写死 macOS 的 `.venv/bin`、Windows 的 `Scripts` 或开发者目录。不要把生成的 `mcp.local.json` 从一台电脑原样复制到另一台电脑；每台电脑重新生成。

`mcp/cad/client.example.json` 是通用结构示例；其中 `python` 必须由调用环境解析为已安装本包的 Python 3.12，例中的相对输出目录由客户端 cwd 决定。实际使用优先运行配置生成命令。

服务器入口为 `python -m hardware_studio.cad.server`，也提供 `cad-mcp` 命令。`HARDWARE_STUDIO_ARTIFACT_ROOT` 可显式指定根目录；其次使用 `HARDWARE_STUDIO_DATA_ROOT/cad`；未指定时根据目标操作系统选择用户数据目录，避免依赖客户端 cwd。需要自定义目录时运行 `hardware-studio --artifact-root <目标目录> mcp-config`。

启动后标准输出专供 JSON-RPC，SDK 日志发到 stderr。尚未自动注册任何全局客户端；测试使用官方 SDK 建立真实会话。

实际可用工具：

| 工具 | 输入 | 输出 |
| --- | --- | --- |
| `cad_get_bracket_schema` | 无 | 参数 JSON Schema 与演示默认值 |
| `cad_assess_parameters` | `parameters` 对象 | 来源、误差、最坏情况余量与参数校验 |
| `cad_build_bracket` | `parameters` 对象 | 构建 ID、文件位置、报告、版本及哈希 |
| `cad_get_build` | `build_id` 字符串 | 重核验文件后的构建结果 |

每个输出的 `status` 必须为 `ok`；若为 `error`，检查 `error.code/message/details`。无效 MCP 输入可能直接获得 `isError: true`。当前没有通用 CAD 代码执行或任意文件读取工具。

运行真实调用示例：

```bash
uv run --locked python scripts/mcp_demo.py
```

脚本执行 initialize、tools/list、参数 Schema 读取、建模、构建回读，保存真实握手和工具返回到 `artifacts/mcp-evidence.json`。

## 本地 Skills

六个 Skill 随 wheel 一起发布；没有源码目录也能导出：

```bash
hardware-studio export-skills ./hardware-studio-skills
```

源码环境也可以运行 `uv run --locked hardware-studio export-skills ./hardware-studio-skills`。目标目录必须不存在，避免覆盖已有技能。将导出的六个目录按目标 Agent 的安装机制注册。Skill 本身不引用开发者目录，也不依赖相对仓库文档链接；它们仍需要目标 Agent 连接对应 MCP。

## 可迁移交付包

`dist/ai_hardware_studio-0.2.0-py3-none-any.whl` 包含 Python 实现、预览模板和六个 Skills，可安装到目标电脑的 Python 3.12 环境。wheel 的 Python 部分可跨平台，CadQuery/OpenCascade 等原生依赖由目标电脑的包管理器按平台安装；wheel 本身不等于离线全依赖包。

完整源码 ZIP `dist/ai-hardware-studio-0.2.0-portable.zip` 包含锁文件、测试、示例、文档与文件哈希清单，适合复制到另一台电脑后从项目根目录运行 `uv sync --locked --extra dev`。不包含 `.venv`、宿主缓存、客户端本机配置或临时 artifacts。离线部署需要另行准备对应 OS/CPU 的依赖包，不能把某台电脑的二进制虚拟环境当作通用安装包。

从源码重新打包：

```bash
uv build --out-dir dist
uv run --locked python scripts/package_portable.py
```

## 排错

- `DEPENDENCY_MISSING`：用 Python 3.12 重新执行锁定安装，在目标电脑重新生成 MCP 配置。
- `INVALID_PARAMETERS`：根据 Schema 修正尺寸；不能用无限大尺寸、任意代码、未知字段绕过限制。
- `BUILD_TIMEOUT`：查看构建目录。先检查内核能否正常导入，勿重复无限重试。
- `BUILD_FAILED`：读取对应 `worker.log`，修复模板或参数后创建新构建。
- `ARTIFACT_INVALID`：文件被删除、修改或路径不安全；保留原始记录并重新构建，不能手工篡改清单使其通过。
- `BUSY`：等待当前构建完成再调用。

成功目录用 UUID 区分；失败目录也保留，便于审计。磁盘清理由本地操作者决定，P0 不提供 MCP 删除工具或磁盘配额。

新安装的原生库首次导入可能明显慢于后续构建。默认构建时限为 300 秒；MCP 环境变量 `HARDWARE_STUDIO_CAD_TIMEOUT_SECONDS` 可设置 1–600 秒，不允许无限等待。超过时限仍返回失败，不应把首次超时记录删除或改成通过。
