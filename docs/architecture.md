# 工程架构

## 三层职责

```mermaid
flowchart LR
  U[自然语言需求] --> A[Chief Engineer Agent]
  A --> S[角色 Skills]
  S --> M[stdio CAD MCP]
  M --> V[参数与目录边界校验]
  V --> W[固定 CAD 子进程]
  W --> O[CadQuery / OpenCascade]
  O --> B[参数 / 源码 / STEP / STL / 预览 / 报告]
  B --> C[SHA256 清单与完成标记]
  C --> A
```

Agent 决定参数与工程步骤，Skill 定义角色流程与验收，MCP 提供可验证执行结果。初期由一个 Agent 切换角色；没有引入多模型调度服务。Agent 调用的真实工具来自 MCP `tools/list`，不可仅依据角色文档猜测工具存在。MCP 通过标准 Python 模块入口启动，路径在目标电脑生成；项目不依赖 Docker 或开发者本机应用。

## P0 实现

`src/hardware_studio/cad/parameters.py` 用严格 Pydantic 模型限制尺寸、有限值、壁厚、孔柱关系和边界余量，拒绝未知字段。`model.py` 是可信参数模板。MCP 不执行上传的 Python，后续扩展其他零件应增加经过测试的模板与独立 Schema。

`CadService` 在服务端预先确定的根目录下生成 UUID 构建目录，固定执行 `sys.executable -m hardware_studio.cad.worker`，不使用 shell。子进程限时，服务实例并发上限为二；失败保留 `failure.json` 或工作日志。worker 几何检查与导出全部成功后原子发布 `manifest.json`。读取构建时验证 ID、目录、符号链接、文件白名单、大小和哈希。

报告基于真实 B-Rep：单实体有效性、外包尺寸、解析体积对比、四个孔的探针交集体积、柱壁点检测，以及 STEP 回读。STL 水密性、连通性、绕序与体积对比通过集成测试独立完成。HTML 内嵌真实 OCC 三角化网格，以 Canvas 投影提供旋转缩放，不依赖外部 CDN；它是预览，不是独立几何判定器。

v0.2 增加逐项尺寸证据与最坏情况余量计算，非演示输入禁止静默使用默认尺寸。新增真实圆柱面计量模块，直接提取孔/柱的解析轴线、直径和高度，导出 STEP 后再次计量。报告将输入误差、内核数值容差、来源真实性与实物验证状态分别记录，防止把几何有效误当成物理尺寸可靠。

wheel 随包包含六个可独立导出的 Skill；完整源码 ZIP 保留测试与锁文件。MCP 实时响应使用目标电脑的实际文件路径，持久示例证据使用相对构建 ID 的逻辑路径，移动交付目录后用 `cad_get_build` 重新获取当前路径。

## 模块归属

| 目录 | 归属 |
| --- | --- |
| `agents/` | 总工程师及六专业角色的职责、交接 |
| `skills/` | 六个可加载工作流；只有 CAD 有已实现 MCP |
| `mcp/cad/` | CAD 服务协议与客户端示例 |
| `mcp/{其他五服务}/` | 明确标记未实现的服务边界 |
| `src/hardware_studio/` | 可打包的真实 Python 实现 |
| `packages/shared/` | 指向唯一共享 Schema 实现的说明 |
| `examples/desktop-robot/` | 虚构托架参数及本地执行证据 |
| `tests/` | 参数、路径边界、失败处理、实际 CAD 和 MCP 客户端测试 |

## 后续接口设计原则

P1 引入外部命令时只允许固定可执行文件、参数列表和受限项目目录，设置时限并保存 stdout/stderr、退出码与版本。硬件能力默认只读，写操作另设确认边界。P3 才引入跨阶段依赖图、数据库状态机和重试策略，不能把当前文件清单描述为完整的编排平台。

本地文件访问保护以合作式本机 Agent 为威胁边界，不构成操作系统级沙箱；持有同一目录写权限的恶意本机用户仍可篡改文件或同时替换路径。部署多用户服务前需增加 OS 隔离、配额、身份验证与更严格的无竞争文件访问。

实现参考：[CadQuery 导入导出](https://cadquery.readthedocs.io/en/latest/importexport.html)、[官方 MCP Python SDK](https://py.sdk.modelcontextprotocol.io/v1/)。
