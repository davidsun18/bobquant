#!/usr/bin/env python3
"""测试告警功能"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from scripts.run_medium_frequency import MediumFrequencyTrader

# 创建交易器
trader = MediumFrequencyTrader(
    config_file='/home/openclaw/.openclaw/workspace/quant_strategies/medium_frequency/config/mf_config.yaml',
    dry_run=True
)

print("=" * 60)
print("测试告警功能")
print("=" * 60)
print(f"告警阈值：{trader.alert_threshold} 次\n")

# 模拟连续 3 次"有信号无执行"
for i in range(1, 5):
    print(f"\n--- 第 {i} 次检查 ---")
    trader.check_alert(
        signals_generated=7,  # 生成 7 个信号
        signals_executed=0     # 执行 0 笔
    )
    print(f"当前连续计数：{trader.consecutive_signal_no_exec}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

# 测试重置
print(f"\n--- 第 6 次检查（有执行）---")
trader.check_alert(
    signals_generated=7,
    signals_executed=2
)
print(f"当前连续计数：{trader.consecutive_signal_no_exec} (应重置为 0)")
