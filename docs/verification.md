# P0 本地验证记录

## v0.2：可迁移交付与尺寸来源校验

2026-10-15，macOS arm64 / Python 3.12.12，当前完整测试为 **77 passed，19.28 秒，无跳过**。17 个警告来自 CadQuery/Pyparsing 的弃用 API，没有隐藏警告。代码检查和六个 Skill 格式校验通过。

新增测试验证：正式尺寸不得静默套用默认值，来源名义值必须一致，测量误差必须有限且非零，孔距不得由设计假设冒充实测，误差范围导致余量不足会拒绝构建。实际圆柱面计量会发现错误孔径，STEP 回读包含真实孔/柱测量值。所有带来源的测试数据均是临时合成测试记录，未描述为真实 PCB 数据。

新增迁移能力：配置从目标解释器生成，默认数据目录不依赖客户端 cwd，六个 Skills 随 wheel 分发并可导出，导出不会覆盖已有目录。示例 MCP 证据现为相对构建路径，不再保存开发者绝对路径。已生成 Python wheel 与可重建源码分发包，跨操作系统 CI 只表示已配置，尚未实际运行。

后续按用户明确约束，支持目标已收敛为 macOS arm64，CI 也仅保留 macOS。新增环境检查脚本与 `doctor --probe-cad`，不再以 Windows/Linux 作为当前验收目标；前述多系统配置说明仅记录当时状态。

`bash scripts/check_environment.sh --probe-cad` 已实际运行通过：Python 为 arm64 / 3.12.12，四个必需依赖已安装，九项真实几何、STEP 回读与文件完整性检查通过。KiCad/PlatformIO 未安装不影响当前 CAD 阶段；此检查未安装软件或启动任何桌面应用。

源码 ZIP 已解压到临时新目录，逐项文件 SHA256 通过；其中没有虚拟环境、宿主缓存、本机客户端配置或临时 artifacts。首次隔离 wheel 安装的 CAD 加载超过旧版 90 秒限制，失败记录保留；当前默认已调整为 300 秒，MCP 配置拒绝非有限或超过 600 秒的时限。

隔离 wheel 安装复测通过：全新虚拟环境安装 wheel 及依赖，未通过 PYTHONPATH 引入源码，从带空格的另一个工作目录生成 MCP 配置、导出六个随包 Skills、发现四个工具、运行真实 CAD 建模并回读校验哈希。九项几何检查全部通过。证据见 `examples/desktop-robot/portable-install-verification.json`；此结果是同一操作系统上的隔离迁移测试，不能据此声称已在另一台电脑或其他 OS 上运行。

当前示例构建 ID 为 `bb7fb002d21d49c2a7c3680a72aec71d`，参见 `examples/desktop-robot/mcp-evidence.json` 与对应 verified 目录。此前构建和以下 v0.1 结果作为历史记录保留。

## v0.1 历史验收记录

执行日期：2026-10-15（Asia/Shanghai）。按用户要求仅在本地完成，不初始化或提交远端仓库。

## 环境与结果

- macOS arm64，Python 3.12.12。
- CadQuery 2.6.1，cadquery-ocp 7.8.1.1.post1，MCP Python SDK 1.30.0。
- `.venv/bin/pytest -q --junitxml=artifacts/junit.xml`：**39 passed，14.64 秒，无跳过**。
- 15 个警告来自 CadQuery 依赖的 Pyparsing 弃用 API，不影响此次检查；未隐藏警告。
- `ruff check .` 与 `ruff format --check .` 通过。
- 六个 Skill 经 skill-creator 的 `quick_validate.py` 校验通过。
- `uv lock --check --offline` 与 `uv sync --locked --extra dev --offline` 通过，依赖锁与项目一致。

## 实际验证范围

31 项参数、目录、失败处理测试覆盖非有限尺寸、超界、壁厚、柱重叠、未知字段、路径穿越、符号链接、超时、并发和失败不伪成功。8 项集成测试覆盖：

1. 实际 STEP 回读后的有效性、单实体、74 × 54 × 11 mm 包围盒，四孔全高度空心及四柱壁存在。
2. 导出 STL 的水密性、三角面绕序、连通性、外包尺寸及与 STEP 体积一致性。
3. 实际 OCC 预览网格、模型源码、版本清单与完整性回读。
4. 在 Node.js 沙箱上下文执行生成的预览脚本，验证初始投影、旋转、缩放、重置和 resize 的有限坐标。
5. 交付目录的独立 `model.py` 重放，不依赖 hardware_studio 导入。
6. 修改底座、孔距、柱高与圆角后，实际 STEP/STL 几何随之改变。
7. 官方 MCP 客户端完成真实 stdio initialize、tools/list、建模、回读与错误输入处理，输入输出 Schema 可发现。
8. 修改交付文件后，SHA256 校验拒绝被篡改的构建。

## 持久交付证据

示例已通过真实 MCP 会话构建，ID：`35852cab8dea41308d9221ef8b538097`。

- 当前完整协议和工具返回：[mcp-evidence.json](../examples/desktop-robot/mcp-evidence.json)，该文件已更新为上述 v0.2 构建。
- 参数、源码、STEP/STL、预览、报告与哈希：[示例输出目录](../examples/desktop-robot/verified/35852cab8dea41308d9221ef8b538097/)。
- 本地机器测试原始结果：`artifacts/junit.xml`，该临时目录默认不进入版本控制。

持久输出目录可以作为独立构建根目录回读：

```bash
uv run --locked hardware-studio --artifact-root examples/desktop-robot/verified inspect 35852cab8dea41308d9221ef8b538097
```

## 已解决问题与未验证项

首轮 Python 3.13 锁定依赖选择不支持该 ABI 的 VTK，现已固定为 Python 3.12。首次原生库加载曾超过 90 秒；完成加载后全套测试及后续 MCP 构建正常，首次失败记录保留于 `artifacts/cad`。没有将超时记录标为成功。

STL 连通性最初调用了需要可选图库的接口，已改为独立面邻接遍历并通过实际网格测试。CAD worker 的字体和绘图缓存定向到构建目录内。

尚未验证 Shapr3D 桌面导入、真实控制板装配、打印工艺、热行为、强度或动力学。浏览器 URL 策略拒绝打开本地 HTML，所以预览只完成网格及 JavaScript 执行验证，未做浏览器画面和真实鼠标操作验收。GitHub Actions 已配置，尚未运行；Linux、其他 CPU 与 Python 版本不能声称通过。也未自动写入 Codex 全局 MCP 或 Skills 配置。

所有示例尺寸是虚构演示值，不能用于声称实际 PCB 兼容性。Electronics、Firmware 与 P2–P4 的服务仍未实现。
