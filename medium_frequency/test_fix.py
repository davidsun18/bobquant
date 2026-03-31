#!/usr/bin/env python3
"""测试风控修复"""

import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from medium_frequency.risk_monitor import RiskMonitor

# 创建监控器
monitor = RiskMonitor({
    'max_trades_per_day': 5,
    'min_trade_interval': 300,  # 5 分钟
})

# 测试 check_trade_frequency
print("=" * 60)
print("测试 check_trade_frequency")
print("=" * 60)

# 第一次检查（应该通过）
paused, reason = monitor.check_trade_frequency('sh.603986')
print(f"\n【测试 1】首次检查")
print(f"  返回：paused={paused}, reason='{reason}'")
print(f"  预期：paused=False (允许交易)")
print(f"  结果：{'✅ PASS' if not paused and '通过' in reason else '❌ FAIL'}")

# 记录一次交易
monitor.record_trade('sh.603986', '买入', 100.0, 100, 0.0)

# 第二次检查（应该被频率限制）
paused, reason = monitor.check_trade_frequency('sh.603986')
print(f"\n【测试 2】交易后立刻检查（间隔<5 分钟）")
print(f"  返回：paused={paused}, reason='{reason}'")
print(f"  预期：paused=True (需要暂停)")
print(f"  结果：{'✅ PASS' if paused and '间隔' in reason else '❌ FAIL'}")

# 测试 should_pause_trading
print("\n" + "=" * 60)
print("测试 should_pause_trading")
print("=" * 60)

# 新股票（应该通过）
paused, reason = monitor.should_pause_trading('sz.002371')
print(f"\n【测试 3】新股票检查")
print(f"  返回：paused={paused}, reason='{reason}'")
print(f"  预期：paused=False (允许交易)")
print(f"  结果：{'✅ PASS' if not paused else '❌ FAIL'}")

# 已交易股票（应该被频率限制）
paused, reason = monitor.should_pause_trading('sh.603986')
print(f"\n【测试 4】已交易股票检查（间隔<5 分钟）")
print(f"  返回：paused={paused}, reason='{reason}'")
print(f"  预期：paused=True (需要暂停)")
print(f"  结果：{'✅ PASS' if paused and '间隔' in reason else '❌ FAIL'}")

print("\n" + "=" * 60)
print("✅ 测试完成")
print("=" * 60)
