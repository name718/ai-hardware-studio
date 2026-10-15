# AI Hardware Studio

由 AI Agent 驱动的数字软硬件研发平台。**人负责物理世界，Agent 负责数字研发。**

当前实现 P0：Agent 按 Skill 将自然语言需求转换为结构化参数，通过标准 stdio MCP 调用真实 CadQuery / OpenCascade，生成四安装柱、四通孔的主控板托架。自然语言理解由连接的 Agent 完成；本仓库不包含独立大模型服务或通用自然语言 CAD 编译器。

## 本地运行

当前仅支持 **macOS arm64**，需要 [uv](https://docs.astral.sh/uv/) 与原生 Python 3.12。使用 3.12 是为兼容当前锁定的 CAD / VTK 二进制依赖。首次安装需要网络和约 1 GB 磁盘空间；建模、预览不需要网络。

```bash
uv sync --locked --extra dev
bash scripts/check_environment.sh
uv run --locked hardware-studio build examples/desktop-robot/bracket.parameters.json
uv run --locked python scripts/mcp_demo.py
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
```

进一步验证真实 CAD 内核、STEP/STL 导出与回读：`bash scripts/check_environment.sh --probe-cad`。该完整检查生成明确标记为虚构尺寸的测试模型，不安装软件、不启动桌面应用。

构建返回 JSON，只有 `status == "ok"` 才可消费输出。`artifacts/cad/<build_id>/` 保存：

| 文件 | 用途 |
| --- | --- |
| `parameters.json` | mm 参数与尺寸来源 |
| `model.py` | 可独立重放的 CadQuery 源码 |
| `bracket.step` / `bracket.stl` | 可编辑实体与打印网格 |
| `preview.html` / `preview.svg` | 无 CDN 的离线可旋转三维预览、静态预览 |
| `report.json` | 内核有效性、尺寸、体积、通孔、柱壁和 STEP 回读结果 |
| `manifest.json` | 完成标记、依赖版本、源码及交付文件 SHA256 |
| `IMPORT_SHAPR3D.md` | Shapr3D 导入与人工检查说明 |

用浏览器直接打开 `preview.html`，拖动旋转、滚轮缩放。在本次构建使用的根目录下用 `hardware-studio --artifact-root <目录> inspect <build_id>` 重新核验哈希。在交付目录运行 `python model.py` 可独立重新生成 STEP/STL。

默认数据根目录由目标电脑操作系统确定，可用 `HARDWARE_STUDIO_ARTIFACT_ROOT` 覆盖；示例脚本显式输出到项目 `artifacts/cad`。项目不需要 Docker，也不会启动桌面应用。

**示例 74 × 54 × 11 mm、孔距 50 × 30 mm、孔径 3.2 mm 均为虚构演示值，不对应真实 PCB。** 没有测量板孔和接口空间前，不可据此宣称能安装某个型号。

## Agent 与 MCP

按 [安装指南](docs/installation.md) 配置 MCP 客户端，加载 [参数化 CAD Skill](skills/parametric-cad-design/SKILL.md)。用户输入“生成一个用于桌面机器人主控板的安装托架，带四个安装柱和螺丝孔”后，Agent 读取 Schema，调用 `cad_assess_parameters` 校验来源和误差，再调用 `cad_build_bracket`，最后用 `cad_get_build` 核验输出。

工具声明输入和输出 Schema；业务失败通过结构化 `status/error` 返回，客户端必须检查 `status`。SDK 参数验证失败使用 MCP `isError`。服务仅执行固定建模子进程，不接受用户代码或路径。默认每次构建限时 300 秒，同时最多两个构建；MCP 可配置 1–600 秒时限，只监听 stdio，不暴露网络端口。

## 尺寸依据与数值准确性

正式数据必须显式填写每个尺寸，并附 `dimension_evidence`：名义值、误差范围、实测/厂商/设计依据、资料定位和版本。来源记录与输入矛盾、缺少依据、误差范围造成余量不足时，构建会被拒绝。演示数据仍允许，但误差缺失明确显示未知，不能声称真实适配。

`cad_assess_parameters` 先做来源与误差校验，建模后再从实际 B-Rep 和导出的 STEP 中量回四个孔的轴线、孔径、柱径与高度进行比较。记录来源并不代表工具已核实原始资料；数值比较容差也不代表物理制造精度。详细规则见 [尺寸准确性说明](docs/dimension-accuracy.md)。

## 在其他电脑使用

在目标电脑重新安装依赖，运行 `hardware-studio mcp-config` 生成该电脑的配置，运行 `hardware-studio export-skills <新目录>` 导出六个随包交付的 Skills。无需复制开发者路径或 `.venv`。提供包含锁文件的完整源码 ZIP，以及可安装 wheel；详见 [迁移安装说明](docs/installation.md)。

## 工程范围

- 已实现：CAD MCP、CLI、六个角色工作流 Skill、七种工程角色说明、真实几何与 MCP 集成测试、锁定依赖及 CI 配置。
- 尚未实现：Electronics / Firmware / Mechanics / Manufacturing / Hardware Test MCP、自动编排与持久化任务调度、统一 UI。
- 尚未验证：Shapr3D 桌面导入、实物制造与装配、物理强度、热与动力学行为；跨平台结果见 [验证记录](docs/verification.md)。

参见 [架构](docs/architecture.md)、[阶段路线](docs/roadmap.md)、[安全边界](docs/safety.md)、[测试与验收](docs/verification.md)。本次按用户要求仅交付本地工程，没有远端提交。
