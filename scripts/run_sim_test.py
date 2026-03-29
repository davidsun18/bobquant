#!/usr/bin/env python3
"""
中频交易 - 模拟测试启动脚本

功能:
- 创建独立的模拟账户
- 记录所有交易
- 生成每日报告
- 统计收益指标

用法:
python3 scripts/run_sim_test.py [--init] [--run] [--report]
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from medium_frequency import (
    MinuteDataFetcher,
    SignalGenerator,
    ExecutionEngine,
)
from medium_frequency.signal_generator import StrategyType


# ========== 模拟账户配置 ==========
SIM_ACCOUNT_FILE = Path('/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/mf_sim_account.json')
SIM_TRADE_LOG = Path('/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/mf_sim_trades.json')
SIM_REPORT_DIR = Path('/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/mf_reports')


def create_sim_account(initial_capital: float = 200000.0):
    """创建模拟账户"""
    account = {
        'type': 'medium_frequency_sim',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'initial_capital': initial_capital,
        'cash': initial_capital,
        'positions': {},
        'total_value': initial_capital,
        'daily_pnl': 0.0,
        'total_pnl': 0.0,
    }
    
    # 保存账户
    with open(SIM_ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        json.dump(account, f, ensure_ascii=False, indent=2)
    
    # 创建交易日志
    with open(SIM_TRADE_LOG, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=2)
    
    # 创建报告目录
    SIM_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ 模拟账户创建成功")
    print(f"  初始资金：¥{initial_capital:,.2f}")
    print(f"  账户文件：{SIM_ACCOUNT_FILE}")
    
    return account


def load_sim_account():
    """加载模拟账户"""
    if not SIM_ACCOUNT_FILE.exists():
        print("⚠️ 模拟账户不存在，请先初始化")
        return None
    
    with open(SIM_ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_sim_account(account):
    """保存模拟账户"""
    # 更新总资产
    total_position_value = 0
    for code, pos in account['positions'].items():
        current_price = pos.get('current_price', pos.get('avg_price', 0))
        total_position_value += pos['shares'] * current_price
    
    account['total_value'] = account['cash'] + total_position_value
    account['total_pnl'] = account['total_value'] - account['initial_capital']
    
    with open(SIM_ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        json.dump(account, f, ensure_ascii=False, indent=2)


def run_sim_trading(check_once: bool = False):
    """运行模拟交易"""
    print("="*70)
    print("  🧪 中频交易 - 模拟测试")
    print("="*70)
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 加载账户
    account = load_sim_account()
    if not account:
        print("\n❌ 模拟账户不存在，运行：python3 scripts/run_sim_test.py --init")
        return
    
    print(f"\n账户状态:")
    print(f"  现金：¥{account['cash']:,.2f}")
    print(f"  持仓：{len(account['positions'])}只")
    print(f"  总资产：¥{account['total_value']:,.2f}")
    print(f"  总盈亏：¥{account['total_pnl']:,.2f} ({account['total_pnl']/account['initial_capital']*100:.2f}%)")
    
    # 初始化组件
    fetcher = MinuteDataFetcher(cache_duration=60)
    
    signal_config = {
        'grid_size': 0.015,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'breakout_period': 20,
    }
    generator = SignalGenerator(signal_config)
    
    risk_config = {
        'max_position_per_stock': 0.10,
        'max_total_position': 0.60,
        'stop_loss': -0.03,
        'take_profit': 0.08,
        'max_trades_per_day': 5,
        'max_consecutive_losses': 3,
    }
    
    # 使用模拟账户的执行引擎
    engine = ExecutionEngine(
        str(SIM_ACCOUNT_FILE),
        str(SIM_TRADE_LOG),
        risk_config
    )
    
    # 加载股票池
    import yaml
    config_file = '/home/openclaw/.openclaw/workspace/quant_strategies/medium_frequency/config/mf_config.yaml'
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    stock_pool = config['medium_frequency']['stock_pool'][:10]  # 先测试前 10 只
    
    print(f"\n股票池：{len(stock_pool)}只")
    print(f"模式：{'单次检查' if check_once else '循环监控'}")
    print("="*70)
    
    # 交易统计
    signals_generated = 0
    trades_executed = 0
    
    # 遍历股票池
    for stock in stock_pool:
        code = stock['code']
        name = stock['name']
        
        # 获取数据
        df = fetcher.get_minute_kline(code, period=5, limit=50, use_cache=True)
        
        if df is None or len(df) < 30:
            continue
        
        current_price = df['close'].iloc[-1]
        
        # 获取当前持仓
        positions = account.get('positions', {})
        current_pos = positions.get(code, {})
        current_shares = current_pos.get('shares', 0)
        
        # 计算仓位比例
        total_value = account['total_value']
        current_position_ratio = (current_shares * current_price) / total_value if total_value > 0 else 0
        
        # 生成信号
        signals = generator.generate_signals(
            df=df,
            code=code,
            name=name,
            current_price=current_price,
            position=current_position_ratio,
            strategies=[StrategyType.GRID, StrategyType.SWING, StrategyType.MOMENTUM]
        )
        
        if signals:
            signals_generated += len(signals)
            print(f"\n[{code}] {name} ¥{current_price:.2f}")
            print(f"  生成{len(signals)}个信号:")
            
            for signal in signals:
                print(f"    {signal.signal_type.value.upper()} - {signal.strategy.value}")
                
                # 执行交易 (真实执行，更新模拟账户)
                result = engine.execute_signal(signal, account, dry_run=False)
                
                if result['success']:
                    trades_executed += 1
                    print(f"      ✅ {result['action']} {result['shares']}股 @ ¥{result['price']:.2f}")
                    print(f"      金额：¥{result['amount']:,.2f}")
                else:
                    print(f"      ❌ 执行失败：{result['reason']}")
        
        # 更新持仓的当前价格
        if code in positions:
            positions[code]['current_price'] = current_price
    
    # 保存账户
    save_sim_account(account)
    
    # 打印总结
    print("\n" + "="*70)
    print("  本次检查完成")
    print("="*70)
    print(f"  生成信号：{signals_generated}个")
    print(f"  执行交易：{trades_executed}笔")
    print(f"  当前持仓：{len(account['positions'])}只")
    print(f"  可用现金：¥{account['cash']:,.2f}")
    print(f"  总资产：¥{account['total_value']:,.2f}")
    print(f"  总盈亏：¥{account['total_pnl']:,.2f} ({account['total_pnl']/account['initial_capital']*100:.2f}%)")
    print("="*70)
    
    return account


def generate_report():
    """生成交易报告"""
    print("="*70)
    print("  📊 模拟交易报告")
    print("="*70)
    
    # 加载账户
    account = load_sim_account()
    if not account:
        print("❌ 模拟账户不存在")
        return
    
    # 加载交易日志
    if SIM_TRADE_LOG.exists():
        with open(SIM_TRADE_LOG, 'r', encoding='utf-8') as f:
            trades = json.load(f)
    else:
        trades = []
    
    # 基本统计
    print(f"\n【账户概览】")
    print(f"  创建时间：{account.get('created_at', 'N/A')}")
    print(f"  初始资金：¥{account['initial_capital']:,.2f}")
    print(f"  当前总资产：¥{account['total_value']:,.2f}")
    print(f"  总盈亏：¥{account['total_pnl']:,.2f} ({account['total_pnl']/account['initial_capital']*100:.2f}%)")
    
    # 买卖统计
    buys = [t for t in trades if t.get('action') == '买入']
    sells = [t for t in trades if t.get('action') == '卖出']
    
    # 交易统计
    print(f"\n【交易统计】")
    print(f"  总交易次数：{len(trades)}")
    
    if trades:
        
        print(f"  买入次数：{len(buys)}")
        print(f"  卖出次数：{len(sells)}")
        
        # 盈亏统计 (只统计卖出)
        profitable = [t for t in sells if t.get('profit', 0) > 0]
        losing = [t for t in sells if t.get('profit', 0) < 0]
        
        total_profit = sum(t.get('profit', 0) for t in profitable)
        total_loss = sum(t.get('profit', 0) for t in losing)
        
        print(f"  盈利交易：{len(profitable)}笔，¥{total_profit:,.2f}")
        print(f"  亏损交易：{len(losing)}笔，¥{total_loss:,.2f}")
        print(f"  净盈亏：¥{total_profit + total_loss:,.2f}")
        
        if sells:
            win_rate = len(profitable) / len(sells) * 100
            print(f"  胜率：{win_rate:.1f}%")
        
        # 策略统计
        print(f"\n【策略统计】")
        strategies = {}
        for t in trades:
            strategy = t.get('strategy', 'unknown')
            if strategy not in strategies:
                strategies[strategy] = {'count': 0, 'profit': 0}
            strategies[strategy]['count'] += 1
            if t.get('action') == '卖出':
                strategies[strategy]['profit'] += t.get('profit', 0)
        
        for strategy, stats in strategies.items():
            print(f"  {strategy}: {stats['count']}笔，¥{stats['profit']:,.2f}")
        
        # 最近交易
        print(f"\n【最近 10 笔交易】")
        for t in trades[-10:]:
            profit_str = f"¥{t.get('profit', 0):,.2f}" if t.get('action') == '卖出' else "-"
            print(f"  {t['time'][-8:]} {t['action']:4s} {t['name']:<10} {t['shares']:>6}股 "
                  f"@¥{t['price']:>7.2f} 盈亏:{profit_str}")
    
    # 持仓明细
    print(f"\n【当前持仓】")
    if account['positions']:
        for code, pos in account['positions'].items():
            current_price = pos.get('current_price', pos.get('avg_price', 0))
            avg_price = pos.get('avg_price', 0)
            pnl = (current_price - avg_price) * pos['shares']
            pnl_pct = pnl / (avg_price * pos['shares']) * 100 if avg_price > 0 else 0
            
            print(f"  {code} {pos['name']:<10} {pos['shares']:>6}股 "
                  f"成本¥{avg_price:>7.2f} 现¥{current_price:>7.2f} "
                  f"盈亏¥{pnl:>8,.2f} ({pnl_pct:>6.2f}%)")
    else:
        print("  无持仓")
    
    # 保存报告
    report_file = SIM_REPORT_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# 中频交易模拟报告\n\n")
        f.write(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## 账户概览\n")
        f.write(f"- 初始资金：¥{account['initial_capital']:,.2f}\n")
        f.write(f"- 总资产：¥{account['total_value']:,.2f}\n")
        f.write(f"- 总盈亏：¥{account['total_pnl']:,.2f}\n")
        f.write(f"- 收益率：{account['total_pnl']/account['initial_capital']*100:.2f}%\n\n")
        f.write(f"## 交易统计\n")
        f.write(f"- 总交易：{len(trades)}笔\n")
        f.write(f"- 买入：{len(buys) if trades else 0}笔\n")
        f.write(f"- 卖出：{len(sells) if trades else 0}笔\n")
        if sells:
            f.write(f"- 胜率：{win_rate:.1f}%\n")
    
    print(f"\n✅ 报告已保存：{report_file}")
    print("="*70)


def main():
    parser = argparse.ArgumentParser(description='中频交易模拟测试')
    parser.add_argument('--init', action='store_true', help='初始化模拟账户')
    parser.add_argument('--run', action='store_true', help='运行模拟交易')
    parser.add_argument('--once', action='store_true', help='只检查一次 (不循环)')
    parser.add_argument('--report', action='store_true', help='生成交易报告')
    parser.add_argument('--capital', type=float, default=200000.0, help='初始资金')
    
    args = parser.parse_args()
    
    if args.init:
        create_sim_account(args.capital)
    
    elif args.run:
        run_sim_trading(check_once=args.once)
    
    elif args.report:
        generate_report()
    
    else:
        # 默认：运行一次检查
        run_sim_trading(check_once=True)


if __name__ == '__main__':
    main()
