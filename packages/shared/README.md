# 共享契约

唯一实现位于 `src/hardware_studio/shared/contracts.py`，由同一个 Python 包分发，避免重复 Schema。

工具结果：`status: ok | error`、`data`、`error: {code, message, details}`。
跨语言包待实际消费者出现后再拆分；当前不生成空 SDK。
