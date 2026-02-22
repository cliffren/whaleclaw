---
triggers: ["运行代码", "执行代码", "Python", "计算", "run code", "execute", "沙箱"]
max_tokens: 600
---
# 代码沙箱

## 触发条件
用户请求运行代码、执行计算、测试脚本。

## 指令
使用 code_sandbox 工具执行 Python 代码。代码在安全沙箱中运行，有超时和内存限制。

## 工具
- code_sandbox

## 示例
用户: 计算 1 到 100 的和
Agent: [code_sandbox: print(sum(range(1, 101)))]
