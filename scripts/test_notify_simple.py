#!/usr/bin/env python3
"""简单测试飞书通知"""

import subprocess

# 测试消息
message = "⚠️ **中频策略告警测试**\n\n这是测试消息\n\n---\n📊 中频量化策略"

# 使用 openclaw message 发送
cmd = f"openclaw message send --target 'user:ou_973651ccbc692b7cd90a7d561f6885b3' --message '{message}'"

print(f"执行命令：{cmd}")
result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

print(f"返回码：{result.returncode}")
print(f"STDOUT: {result.stdout}")
print(f"STDERR: {result.stderr}")
