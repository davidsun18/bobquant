#!/usr/bin/env python3
"""模拟告警测试 - 触发飞书通知"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from scripts.run_medium_frequency import MediumFrequencyTrader

# 创建交易器
trader = MediumFrequencyTrader(
    config_file='/home/openclaw/.openclaw/workspace/quant_strategies/medium_frequency/config/mf_config.yaml',
    dry_run=True
)

print("=" * 60)
print("🧪 模拟告警测试 - 触发飞书通知")
print("=" * 60)
print(f"通知启用：{trader.notify_enabled}")
print(f"用户 ID: {trader.feishu_user_id}")
print(f"告警阈值：{trader.alert_threshold} 次\n")

# 模拟连续 3 次"有信号无执行"，触发告警
for i in range(1, 5):
    print(f"\n--- 第 {i} 次检查 ---")
    trader.check_alert(
        signals_generated=7,  # 生成 7 个信号
        signals_executed=0     # 执行 0 笔
    )
    print(f"当前连续计数：{trader.consecutive_signal_no_exec}")

print("\n" + "=" * 60)
print("✅ 测试完成！请检查飞书是否收到告警通知")
print("=" * 60)

# 等待几秒让后台发送完成
import time
print("\n等待通知发送中...")
time.sleep(3)
print("完成！")
