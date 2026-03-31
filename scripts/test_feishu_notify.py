#!/usr/bin/env python3
"""测试飞书通知功能"""

import sys
import subprocess
from datetime import datetime

sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from scripts.run_medium_frequency import MediumFrequencyTrader

# 创建交易器
trader = MediumFrequencyTrader(
    config_file='/home/openclaw/.openclaw/workspace/quant_strategies/medium_frequency/config/mf_config.yaml',
    dry_run=True
)

print("=" * 60)
print("测试飞书通知功能")
print("=" * 60)
print(f"通知启用：{trader.notify_enabled}")
print(f"用户 ID: {trader.feishu_user_id}\n")

# 测试 1：告警通知
print("--- 测试 1: 告警通知 ---")
trader.send_feishu_alert(
    title="中频策略风控告警（测试）",
    content="""**连续 3 次** 检查发现：生成信号 > 0 但 执行交易 = 0

**告警阈值：** 3 次

**可能原因:**
  1. 风控策略过于严格
  2. 资金不足
  3. 执行引擎 Bug

**建议检查:**
  - 查看日志中的'执行失败'原因
  - 检查风控配置""",
    urgent=False
)

print("\n等待 2 秒...\n")
import time
time.sleep(2)

# 测试 2：交易通知（买入）
print("--- 测试 2: 交易通知（买入）---")
trader.send_feishu_alert(
    title="✅ 中频交易执行（测试）",
    content="""**买入 兆易创新**

- 数量：100 股
- 价格：¥238.16
- 金额：¥2.38 万
- 模式：[模拟]
- 原因：Grid 信号 (RSI 超卖，MACD 金叉)""",
    urgent=False
)

print("\n等待 2 秒...\n")
time.sleep(2)

# 测试 3：交易通知（卖出）
print("--- 测试 3: 交易通知（卖出）---")
trader.send_feishu_alert(
    title="💰 中频交易执行（测试）",
    content="""**卖出 北方华创**

- 数量：100 股
- 价格：¥448.29
- 金额：¥4.48 万
- 模式：[模拟]
- 原因：止盈 L1 (盈 +5.2% 卖 33%)""",
    urgent=False
)

print("\n" + "=" * 60)
print("✅ 测试完成！请检查飞书消息")
print("=" * 60)
