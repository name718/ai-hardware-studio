# 建模数据准确性

本项目分别处理输入依据、数值建模和真实制造，不能用一个“通过”替代三种判断。

## 输入数据

`fictional_demo` 表示只用于演示的假设尺寸，不对应真实板卡。缺失误差在报告中为 `null`（未知），不能解读为零误差。

`user_measured` 与 `manufacturer_document` 要求全部 10 项尺寸显式填写，不允许在缺失时套入演示默认值。每项 `dimension_evidence` 包含：

| 字段 | 含义 |
| --- | --- |
| `nominal_mm` | 来源中的名义尺寸，必须与模型输入一致 |
| `uncertainty_mm` | ± 最坏误差范围；实测与厂商尺寸不得填零 |
| `source_kind` | measurement、manufacturer_document 或 design_decision |
| `reference` | 实测记录编号、资料编号或 URL |
| `locator` | 图纸页码/标注位置，或测量方法与特征 |
| `revision` | 资料/测量记录版本 |

孔距必须有与所声明数据类型相符的实测或厂商依据，不能用设计假设冒充实际孔位。设计选择的尺寸可标为 `design_decision`，但不能把设计名义值的零误差当成制造零误差。

来源字符串只是追踪记录。工具不会凭一个 URL 或编号就宣称资料真实；调用 Agent 需要实际读图、核对板卡型号与版本，并保留测量记录。没有资料时只能交付明确标识的演示模型，或等待关键数据。

## 最坏情况余量

工具按各尺寸误差的独立区间计算径向柱壁、底座厚度、柱间距与底座边缘余量，不假设误差互相抵消。名义几何能建出来，但误差范围使最小壁厚或间隙不足时，也会拒绝构建。

这里检查的是单个托架模板的输入区间，不是完整 PCB/螺钉配合的公差链。板孔位置度、实际螺钉、接口空间、打印收缩和材料变形仍需单独验证。

## 实体计量

建模后用 OpenCascade 解析圆柱面量回孔轴、孔径、柱径、柱高；STEP 导出后重新导入并再次计量。报告中的 `measured_features` 与 `step_measured_features` 来自实际实体，不是把输入值复制进“实测”字段。

`1e-5 mm` 是数值比较阈值，只用来判定内核输出与输入是否一致，不是加工能力、测量仪器精度或实物保证。独立回归测试会故意把孔径从 3.2 改成 3.4 mm，确认计量能发现不一致。

## 输出判断

- `status: passed`：本次执行的几何检查通过。
- `dimension_accuracy.input_status: evidence_recorded`：输入证据齐备并通过一致性检查。
- `source_independently_verified: false`：工具没有独立鉴别资料真实性。
- `physical_fit_verified: false`：工具没有替代人工试装。

先调用 `cad_assess_parameters`，通过后再建模和回读。正式制造前需要真实板卡数据与实物验收，不能凭几何报告宣称兼容。
