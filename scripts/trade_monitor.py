#!/usr/bin/env python3
"""
交易日志异常检测工具

功能:
- 检测连续亏损
- 检测异常交易频率
- 检测仓位超标
- 生成风险报告

用法:
python3 scripts/trade_monitor.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

TRADE_LOG_FILE = Path('/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json')
ACCOUNT_FILE = Path('/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json')


def load_trade_log():
    """加载交易记录"""
    if TRADE_LOG_FILE.exists():
        with open(TRADE_LOG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def load_account():
    """加载账户数据"""
    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_consecutive_losses(trades, threshold=3):
    """
    检测连续亏损
    
    Args:
        trades: 交易记录列表
        threshold: 连续亏损阈值
    
    Returns:
        (bool, list) - 是否触发警报，连续亏损的交易列表
    """
    losses = []
    consecutive = []
    
    for trade in trades:
        if trade.get('action', '').startswith('❌') or trade.get('profit', 0) < 0:
            losses.append(trade)
            consecutive.append(trade)
        else:
            if len(consecutive) >= threshold:
                break
            consecutive = []
    
    triggered = len(consecutive) >= threshold
    return triggered, consecutive


def check_abnormal_frequency(trades, days=7, max_trades=20):
    """
    检测异常交易频率
    
    Args:
        trades: 交易记录列表
        days: 检查天数
        max_trades: 最大交易次数
    
    Returns:
        (bool, int) - 是否触发警报，实际交易次数
    """
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    
    recent_trades = [
        t for t in trades 
        if datetime.strptime(t['time'], '%Y-%m-%d %H:%M:%S') > cutoff
    ]
    
    triggered = len(recent_trades) > max_trades
    return triggered, len(recent_trades)


def check_position_limits(account):
    """
    检查仓位限制
    
    Args:
        account: 账户数据
    
    Returns:
        list - 违规列表
    """
    violations = []
    
    positions = account.get('positions', {})
    cash = account.get('cash', 0)
    
    # 计算总资产
    total_value = cash
    for code, pos in positions.items():
        current_price = pos.get('current_price', pos.get('avg_price', 0))
        total_value += pos['shares'] * current_price
    
    # 检查总仓位
    position_value = total_value - cash
    position_ratio = position_value / total_value if total_value > 0 else 0
    
    if position_ratio > 0.80:
        violations.append(f"总仓位超标：{position_ratio*100:.1f}% (>80%)")
    
    # 检查单只股票仓位
    for code, pos in positions.items():
        current_price = pos.get('current_price', pos.get('avg_price', 0))
        stock_value = pos['shares'] * current_price
        stock_ratio = stock_value / total_value if total_value > 0 else 0
        
        if stock_ratio > 0.15:
            violations.append(f"{pos['name']} 仓位超标：{stock_ratio*100:.1f}% (>15%)")
    
    # 检查现金储备
    cash_ratio = cash / total_value if total_value > 0 else 0
    if cash_ratio < 0.20:
        violations.append(f"现金储备不足：{cash_ratio*100:.1f}% (<20%)")
    
    return violations


def check_stop_loss_efficiency(trades):
    """
    检查止损执行效率
    
    Args:
        trades: 交易记录列表
    
    Returns:
        dict - 止损统计
    """
    stop_loss_trades = [
        t for t in trades 
        if t.get('reason', '').startswith('止损') or t.get('action', '') == '❌ 止损'
    ]
    
    total_trades = len([t for t in trades if t.get('action', '').startswith('❌')])
    
    return {
        'total_losses': total_trades,
        'stop_loss_executed': len(stop_loss_trades),
        'efficiency': len(stop_loss_trades) / total_trades if total_trades > 0 else 0
    }


def generate_report():
    """生成监控报告"""
    print("="*70)
    print("🔍 交易日志异常检测报告")
    print("="*70)
    print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 加载数据
    trades = load_trade_log()
    account = load_account()
    
    alerts = []
    warnings = []
    
    # 1. 连续亏损检测
    print("【1】连续亏损检测")
    triggered, consecutive = check_consecutive_losses(trades)
    if triggered:
        alerts.append(f"⚠️ 连续亏损警报：连续{len(consecutive)}笔亏损交易")
        print(f"  ⚠️ 触发警报！连续{len(consecutive)}笔亏损")
        for t in consecutive[-3:]:
            print(f"    - {t['name']}: {t.get('profit', 0):.2f} ({t['time']})")
    else:
        print(f"  ✅ 正常 (最近连续亏损：{len(consecutive)}笔)")
    print()
    
    # 2. 交易频率检测
    print("【2】交易频率检测")
    triggered, count = check_abnormal_frequency(trades, days=7, max_trades=20)
    if triggered:
        alerts.append(f"⚠️ 交易频率异常：7 天内{count}笔交易 (>20)")
        print(f"  ⚠️ 触发警报！7 天内{count}笔交易")
    else:
        print(f"  ✅ 正常 (7 天内{count}笔交易)")
    print()
    
    # 3. 仓位限制检测
    print("【3】仓位限制检测")
    violations = check_position_limits(account)
    if violations:
        for v in violations:
            alerts.append(f"⚠️ {v}")
            print(f"  ⚠️ {v}")
    else:
        print(f"  ✅ 所有仓位指标正常")
    print()
    
    # 4. 止损效率检测
    print("【4】止损执行效率")
    stats = check_stop_loss_efficiency(trades)
    print(f"  总亏损交易：{stats['total_losses']}笔")
    print(f"  止损执行：{stats['stop_loss_executed']}笔")
    print(f"  执行效率：{stats['efficiency']*100:.1f}%")
    if stats['efficiency'] < 0.8 and stats['total_losses'] > 0:
        warnings.append("⚠️ 止损执行效率偏低 (<80%)")
        print(f"  ⚠️ 止损执行效率偏低")
    else:
        print(f"  ✅ 止损执行正常")
    print()
    
    # 汇总
    print("="*70)
    print("📊 检测汇总")
    print("="*70)
    
    if alerts:
        print(f"\n❌ 警报 ({len(alerts)}):")
        for a in alerts:
            print(f"  {a}")
    
    if warnings:
        print(f"\n⚠️ 警告 ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")
    
    if not alerts and not warnings:
        print(f"\n✅ 所有检测通过！系统运行正常！")
    
    print()
    print("="*70)
    
    return len(alerts) == 0 and len(warnings) == 0


if __name__ == '__main__':
    success = generate_report()
    sys.exit(0 if success else 1)
