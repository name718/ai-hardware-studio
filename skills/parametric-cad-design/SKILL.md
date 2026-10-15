---
name: parametric-cad-design
description: 为 AI Hardware Studio 生成或调整四柱主控板托架，调用真实 CAD MCP，交付可重放 STEP、STL 与几何检查证据。其他机械形状需要先扩展可信模板。
---

# 参数化 CAD

适用于“生成桌面机器人主控板安装托架，带四个安装柱和螺丝孔”等请求。

当前模板只支持以中心为基准的对称矩形四孔阵列。偏移、不对称或其他孔位模式需要先扩展模板；不能把真实孔坐标强行简化为两个孔距。

## 输入与输出

输入：底座长宽厚、孔距、柱高、柱径、孔径、最小壁厚和尺寸来源；单位 mm。
输出：通过校验的参数、CadQuery 源码、STEP/STL、离线三维预览、检查报告与版本哈希。

## 工作流程与工具

1. 使用 MCP `tools/list` 确认存在 `cad_get_bracket_schema`、`cad_assess_parameters`、`cad_build_bracket`、`cad_get_build`。未连接时，在目标电脑安装 AI Hardware Studio 的 wheel 或源码，运行 `hardware-studio mcp-config` 生成当前环境配置并加入支持 stdio 的客户端。不要复制别人的解释器绝对路径；不需要 Docker。
2. 调用 `cad_get_bracket_schema` 获取真实参数 Schema。自然语言解析由当前 Agent 负责，不声称工具支持任意文本或任意 CAD 形状。
3. 提取用户尺寸。未提供板孔数据时，只能用 `fictional_demo`，明确演示值不对应真实 PCB，误差未知。正式输入使用 `user_measured` 或 `manufacturer_document`，所有尺寸显式填写，每项 `dimension_evidence` 必须包含 `nominal_mm`、`uncertainty_mm`、`source_kind`、`reference`、`locator`、`revision`。设计选取值用 `design_decision`；板孔距必须有对应的实测或厂商来源。不得猜资料页码、精度或公差。
4. 调用 `cad_assess_parameters` 校验来源与数值一致性、误差范围和最坏情况余量。缺证据或不满足余量必须修正，不能仅修改来源标签绕过。记录来源不代表已独立核实原始资料真实性。
5. 以 `{"parameters": {...}}` 调用 `cad_build_bracket`。不要发送 Python 源码、命令或输出路径；修改尺寸通过参数完成。新几何结构需要扩展可信模板并重新测试。
6. 检查返回 `status == ok`、报告 `status == passed`、所有 `checks` 为真，查看 `measured_features` 和 `step_measured_features` 中实际量回的孔径、孔轴、柱径和高度。再用 `cad_get_build` 核验完整性。
7. 交付 STEP/STL、预览、参数、源码、报告、清单和导入说明，报告来源与未验证项。CAD 数值比较容差不等于加工精度；实物还受制造、装配、间隙和材料影响。

## 错误与验收

MCP `isError` 或业务 `status: error` 都视为失败。参数错误根据 Schema 修正；内核错误读取构建日志，只针对明确原因修复。超时、依赖缺失或文件篡改时不得编造成功或无限重试。

验收以真实 CAD 内核报告、STEP 回读、输入来源校验和 MCP 回读为据。在有源码测试环境时运行完整测试；没有执行的检查标为未验证。几何通过不等于强度、打印适配或实物装配通过；没有运行 Shapr3D 桌面导入时必须标记未验证。
