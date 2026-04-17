#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtrader 回测引擎测试脚本

测试内容：
1. MACD 策略回测
2. 参数优化
3. 多策略对比
4. 与 VectorBT 性能对比
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(script_dir))

from loguru import logger
import json

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{message}</level>")
logger.add("backtest_test.log", rotation="10 MB", level="DEBUG")


def test_macd_backtest():
    """测试 MACD 策略回测"""
    print("\n" + "=" * 70)
    print("测试 1: MACD 策略回测")
    print("=" * 70)
    
    from backtest.backtrader_engine import BacktraderEngine
    
    config = {
        'initial_capital': 1000000,
        'commission_rate': 0.0005,
        'stamp_duty_rate': 0.001,
        'slippage': 0.002
    }
    
    engine = BacktraderEngine(config)
    
    # 回测过去 1 年
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    results = engine.run_macd(
        code='000001.SZ',
        start_date=start_date,
        end_date=end_date,
        fast_period=12,
        slow_period=26,
        signal_period=9
    )
    
    # 导出报告
    report_path = f'backtest/reports/backtrader_macd_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    engine.export_report(results, report_path)
    
    print(f"\n✅ MACD 回测测试完成！报告已保存：{report_path}")
    
    return results


def test_parameter_optimization():
    """测试参数优化"""
    print("\n" + "=" * 70)
    print("测试 2: MACD 参数优化")
    print("=" * 70)
    
    from backtest.backtrader_engine import BacktraderEngine
    
    config = {
        'initial_capital': 1000000,
        'commission_rate': 0.0005,
        'stamp_duty_rate': 0.001,
        'slippage': 0.002
    }
    
    engine = BacktraderEngine(config)
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    # 缩小参数范围以加快测试
    opt_results = engine.optimize_macd(
        code='000001.SZ',
        start_date=start_date,
        end_date=end_date,
        fast_range=(10, 16),
        slow_range=(20, 30),
        signal_range=(7, 11)
    )
    
    if 'best_params' in opt_results:
        print(f"\n✅ 参数优化完成！")
        print(f"最优参数：{opt_results['best_params']}")
        print(f"最优夏普比率：{opt_results['best_sharpe']:.2f}")
    
    return opt_results


def test_multi_strategy_comparison():
    """测试多策略对比"""
    print("\n" + "=" * 70)
    print("测试 3: 多策略对比")
    print("=" * 70)
    
    from backtest.backtrader_engine import BacktraderEngine
    
    config = {
        'initial_capital': 1000000,
        'commission_rate': 0.0005,
        'stamp_duty_rate': 0.001,
        'slippage': 0.002
    }
    
    engine = BacktraderEngine(config)
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    comparison = engine.compare_strategies(
        code='000001.SZ',
        start_date=start_date,
        end_date=end_date,
        strategies=['macd', 'dual_ma']  # 只测试两个策略以加快测试
    )
    
    print(f"\n✅ 多策略对比完成！")
    
    return comparison


def test_engine_comparison():
    """测试 Backtrader vs VectorBT 引擎对比"""
    print("\n" + "=" * 70)
    print("测试 4: Backtrader vs VectorBT 引擎对比")
    print("=" * 70)
    
    from backtest.backtrader_engine import compare_engines
    
    config = {
        'initial_capital': 1000000,
        'commission_rate': 0.0005,
        'stamp_duty_rate': 0.001,
        'slippage': 0.002
    }
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')  # 缩短时间以加快测试
    
    comparison = compare_engines(
        config=config,
        code='000001.SZ',
        start_date=start_date,
        end_date=end_date,
        strategy='macd'
    )
    
    print(f"\n✅ 引擎对比完成！")
    
    return comparison


def test_minute_data():
    """测试分钟线回测"""
    print("\n" + "=" * 70)
    print("测试 5: 分钟线回测")
    print("=" * 70)
    
    from backtest.backtrader_engine import BacktraderEngine
    
    config = {
        'initial_capital': 1000000,
        'commission_rate': 0.0005,
        'stamp_duty_rate': 0.001,
        'slippage': 0.002
    }
    
    engine = BacktraderEngine(config)
    
    # 测试最近 5 天的分钟线
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    
    try:
        results = engine.run_macd(
            code='000001.SZ',
            start_date=start_date,
            end_date=end_date,
            timeframe='minute'  # 使用分钟线
        )
        
        print(f"\n✅ 分钟线回测完成！")
        return results
    except Exception as e:
        print(f"⚠️  分钟线回测失败（可能是数据源限制）: {e}")
        return {'error': str(e)}


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("BobQuant Backtrader 回测引擎 - 完整测试套件")
    print("=" * 70)
    print(f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    all_results = {
        'test_time': datetime.now().isoformat(),
        'tests': {}
    }
    
    # 测试 1: MACD 回测
    try:
        all_results['tests']['macd_backtest'] = test_macd_backtest()
    except Exception as e:
        print(f"❌ MACD 回测测试失败：{e}")
        all_results['tests']['macd_backtest'] = {'error': str(e)}
    
    # 测试 2: 参数优化
    try:
        all_results['tests']['parameter_optimization'] = test_parameter_optimization()
    except Exception as e:
        print(f"❌ 参数优化测试失败：{e}")
        all_results['tests']['parameter_optimization'] = {'error': str(e)}
    
    # 测试 3: 多策略对比
    try:
        all_results['tests']['multi_strategy'] = test_multi_strategy_comparison()
    except Exception as e:
        print(f"❌ 多策略对比测试失败：{e}")
        all_results['tests']['multi_strategy'] = {'error': str(e)}
    
    # 测试 4: 引擎对比
    try:
        all_results['tests']['engine_comparison'] = test_engine_comparison()
    except Exception as e:
        print(f"❌ 引擎对比测试失败：{e}")
        all_results['tests']['engine_comparison'] = {'error': str(e)}
    
    # 测试 5: 分钟线回测
    try:
        all_results['tests']['minute_data'] = test_minute_data()
    except Exception as e:
        print(f"❌ 分钟线回测测试失败：{e}")
        all_results['tests']['minute_data'] = {'error': str(e)}
    
    # 保存测试结果
    test_report_path = f'backtest/reports/backtrader_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    os.makedirs(os.path.dirname(test_report_path), exist_ok=True)
    
    # 序列化结果（移除 DataFrame 等不可序列化对象）
    def serialize(obj):
        if isinstance(obj, dict):
            return {k: serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [serialize(v) for v in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)
    
    serializable_results = serialize(all_results)
    
    with open(test_report_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_results, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 70)
    print("✅ 所有测试完成！")
    print("=" * 70)
    print(f"测试报告：{test_report_path}")
    print("=" * 70)
    
    return all_results


if __name__ == '__main__':
    results = main()
