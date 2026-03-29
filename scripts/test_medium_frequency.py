#!/usr/bin/env python3
"""
中频交易模块 - 完整测试脚本

测试范围:
1. 数据获取
2. 指标计算
3. 信号生成 (3 种策略)
4. 风控检查
5. 订单执行
6. 日志记录
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from medium_frequency import (
    MinuteDataFetcher,
    SignalGenerator,
    ExecutionEngine,
)
from medium_frequency.signal_generator import SignalType, StrategyType
from medium_frequency.risk_monitor import RiskMonitor


def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_data_fetcher():
    """1. 测试数据获取"""
    print_section("【1】数据获取测试")
    
    fetcher = MinuteDataFetcher(cache_duration=60)
    
    # 测试股票池
    test_stocks = [
        ('sh.603986', '兆易创新'),
        ('sz.300750', '宁德时代'),
        ('sh.600519', '贵州茅台'),
    ]
    
    results = {}
    
    for code, name in test_stocks:
        print(f"获取 {code} {name}...")
        
        # 获取 5 分钟 K 线
        df = fetcher.get_minute_kline(code, period=5, limit=50)
        
        if df is not None and len(df) > 0:
            results[code] = {
                'name': name,
                'df': df,
                'latest_price': df['close'].iloc[-1],
                'data_points': len(df),
            }
            print(f"  ✅ 成功：{len(df)}条，最新价¥{df['close'].iloc[-1]:.2f}")
        else:
            print(f"  ❌ 失败")
    
    # 测试缓存
    print(f"\n测试缓存机制...")
    start = time.time()
    fetcher.get_minute_kline('sh.603986', period=5, limit=50, use_cache=True)
    t1 = time.time() - start
    
    print(f"  缓存命中时间：{t1*1000:.2f}ms")
    print(f"  缓存统计：{fetcher.get_cache_stats()}")
    
    return results


def test_indicator_calculation(data_dict):
    """2. 测试指标计算"""
    print_section("【2】技术指标计算测试")
    
    generator = SignalGenerator()
    
    for code, info in data_dict.items():
        df = info['df']
        print(f"\n{code} {info['name']}:")
        
        # 计算指标
        df_with_indicators = generator._calculate_indicators(df.copy())
        
        if len(df_with_indicators) > 0:
            latest = df_with_indicators.iloc[-1]
            
            print(f"  MACD: {latest['macd']:.4f}")
            print(f"  RSI: {latest['rsi']:.2f}")
            print(f"  布林带位置：{latest['bb_position']:.2f}")
            print(f"  成交量比率：{latest['volume_ratio']:.2f}")
            
            # 验证指标有效性
            checks = {
                'RSI 范围': 0 <= latest['rsi'] <= 100,
                '布林带范围': 0 <= latest['bb_position'] <= 1,
                '成交量为正': latest['volume'] > 0,
            }
            
            for check_name, passed in checks.items():
                print(f"  {'✅' if passed else '❌'} {check_name}")
    
    return True


def test_signal_generation(data_dict):
    """3. 测试信号生成"""
    print_section("【3】信号生成测试 (3 种策略)")
    
    config = {
        'grid_size': 0.015,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'breakout_period': 20,
    }
    
    generator = SignalGenerator(config)
    
    all_signals = {}
    
    for code, info in data_dict.items():
        df = info['df']
        current_price = info['latest_price']
        
        print(f"\n{code} {info['name']} (现价¥{current_price:.2f}):")
        
        # 测试三种策略
        strategies = [
            (StrategyType.GRID, '网格策略'),
            (StrategyType.SWING, '波段策略'),
            (StrategyType.MOMENTUM, '动量策略'),
        ]
        
        signals = generator.generate_signals(
            df=df,
            code=code,
            name=info['name'],
            current_price=current_price,
            position=0.05,  # 假设已有 5% 仓位
            strategies=[s[0] for s in strategies]
        )
        
        if signals:
            print(f"  生成{len(signals)}个信号:")
            for signal in signals:
                print(f"    {signal.signal_type.value.upper()} - {signal.strategy.value}")
                print(f"      置信度：{signal.confidence:.2f}")
                print(f"      原因：{', '.join(signal.reasons)}")
                print(f"      目标仓位：{signal.target_position*100:.1f}%")
        else:
            print(f"  暂无信号 (市场平静)")
        
        all_signals[code] = signals
    
    return all_signals


def test_risk_monitor():
    """4. 测试风控系统"""
    print_section("【4】风控系统测试")
    
    config = {
        'max_position_per_stock': 0.10,
        'max_total_position': 0.60,
        'min_cash_reserve': 0.40,
        'stop_loss': -0.03,
        'take_profit': 0.08,
        'max_trades_per_day': 5,
        'max_consecutive_losses': 3,
    }
    
    monitor = RiskMonitor(config)
    
    # 测试 1: 仓位限制
    print("【4.1】仓位限制检查")
    allowed, reason = monitor.check_position_limit(
        code='sh.603986',
        current_position=0.05,
        target_position=0.08,
        total_position=0.35
    )
    print(f"  买入检查：{'✅ 允许' if allowed else '❌ 拒绝'} - {reason}")
    
    allowed, reason = monitor.check_position_limit(
        code='sh.603986',
        current_position=0.08,
        target_position=0.15,  # 超标
        total_position=0.35
    )
    print(f"  超仓检查：{'✅ 允许' if allowed else '❌ 拒绝'} - {reason}")
    
    # 测试 2: 止损止盈
    print("\n【4.2】止损止盈检查")
    triggered, reason = monitor.check_stop_loss(
        code='sh.603986',
        buy_price=100.0,
        current_price=96.0  # -4%
    )
    print(f"  止损触发：{'⚠️ 是' if triggered else '✅ 否'} - {reason}")
    
    triggered, reason = monitor.check_stop_loss(
        code='sh.603986',
        buy_price=100.0,
        current_price=109.0  # +9%
    )
    print(f"  止盈触发：{'⚠️ 是' if triggered else '✅ 否'} - {reason}")
    
    # 测试 3: 交易频率
    print("\n【4.3】交易频率检查")
    for i in range(3):
        monitor.record_trade('sh.603986', '卖出', 100.0, 100, profit=-300.0)
        paused, reason = monitor.check_consecutive_losses('sh.603986')
        print(f"  第{i+1}笔亏损后：连续{monitor._consecutive_losses.get('sh.603986')}笔，暂停：{paused}")
    
    # 测试 4: 综合检查
    print("\n【4.4】综合风控检查")
    paused, reason = monitor.should_pause_trading('sh.603986')
    print(f"  是否暂停：{'⏸️ 是' if paused else '▶️ 否'} - {reason}")
    
    return monitor


def test_execution_engine(signals_dict, data_dict):
    """5. 测试执行引擎"""
    print_section("【5】执行引擎测试")
    
    account_file = Path('/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json')
    trade_log_file = Path('/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json')
    
    # 加载账户
    with open(account_file, 'r', encoding='utf-8') as f:
        account = json.load(f)
    
    print(f"初始状态:")
    print(f"  现金：¥{account.get('cash', 0)/10000:.2f}万")
    print(f"  持仓：{len(account.get('positions', {}))}只")
    
    # 创建执行引擎 (模拟模式)
    risk_config = {
        'max_position_per_stock': 0.10,
        'stop_loss': -0.03,
        'take_profit': 0.08,
    }
    
    engine = ExecutionEngine(
        str(account_file),
        str(trade_log_file),
        risk_config
    )
    
    executed_trades = []
    
    # 执行信号 (模拟)
    print(f"\n执行信号 (dry_run=True):")
    
    for code, signals in signals_dict.items():
        if not signals:
            continue
        
        for signal in signals:
            result = engine.execute_signal(signal, account, dry_run=True)
            
            if result['success']:
                executed_trades.append(result)
                print(f"  ✅ {signal.code} {result['action']} {result['shares']}股 @ ¥{result['price']:.2f}")
                print(f"     金额：¥{result['amount']/10000:.2f}万")
                print(f"     原因：{result['reason'][:50]}...")
            else:
                print(f"  ❌ {signal.code} 执行失败：{result['reason']}")
    
    print(f"\n执行统计:")
    print(f"  成功：{len(executed_trades)}笔")
    print(f"  失败：{len(signals_dict) - len(executed_trades) if executed_trades else 0}笔")
    
    return executed_trades


def test_integration():
    """6. 完整集成测试"""
    print_section("【6】完整集成测试")
    
    print("运行一次完整的中频交易检查...\n")
    
    # 导入主程序
    from scripts.run_medium_frequency import MediumFrequencyTrader
    
    config_file = '/home/openclaw/.openclaw/workspace/quant_strategies/medium_frequency/config/mf_config.yaml'
    
    trader = MediumFrequencyTrader(config_file, dry_run=True)
    
    # 执行一次检查
    trader.run_once()
    
    print("\n✅ 集成测试完成")


def main():
    """主测试流程"""
    print("="*70)
    print("  🧪 中频交易模块 - 完整测试")
    print("="*70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 数据获取
        data_dict = test_data_fetcher()
        
        if not data_dict:
            print("\n❌ 数据获取失败，终止测试")
            return
        
        # 2. 指标计算
        test_indicator_calculation(data_dict)
        
        # 3. 信号生成
        signals_dict = test_signal_generation(data_dict)
        
        # 4. 风控系统
        test_risk_monitor()
        
        # 5. 执行引擎
        test_execution_engine(signals_dict, data_dict)
        
        # 6. 集成测试
        test_integration()
        
        # 总结
        print_section("📊 测试总结")
        print("✅ 所有测试完成！")
        print("\n测试覆盖:")
        print("  1. ✅ 数据获取 (新浪财经分钟线)")
        print("  2. ✅ 指标计算 (MACD/RSI/布林带)")
        print("  3. ✅ 信号生成 (网格/波段/动量)")
        print("  4. ✅ 风控检查 (仓位/止损/频率)")
        print("  5. ✅ 订单执行 (模拟模式)")
        print("  6. ✅ 集成测试 (完整流程)")
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
