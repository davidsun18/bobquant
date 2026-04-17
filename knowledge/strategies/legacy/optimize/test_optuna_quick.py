#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版 Optuna 参数优化测试 - MACD 策略

快速验证优化功能（仅 10 次试验）
"""
import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
sys.path.insert(0, project_dir)
sys.path.insert(0, os.path.join(project_dir, 'bobquant'))

from optuna_optimizer import OptunaOptimizer
from backtest.backtrader_engine import BacktraderEngine
import pandas as pd


def run_quick_test():
    """运行快速测试"""
    
    print("=" * 80)
    print("BobQuant Optuna 参数优化快速测试 - MACD 策略")
    print("=" * 80)
    
    # 设置测试参数（缩短时间范围以加快测试）
    code = '000001.SZ'  # 平安银行
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 过去 6 个月
    
    print(f"\n[测试] 配置参数:")
    print(f"  - 股票代码：{code}")
    print(f"  - 开始日期：{start_date.strftime('%Y-%m-%d')}")
    print(f"  - 结束日期：{end_date.strftime('%Y-%m-%d')}")
    print(f"  - 初始资金：1,000,000")
    print(f"  - 优化试验次数：10（快速测试）")
    
    # 创建优化器
    optimizer = OptunaOptimizer(
        code=code,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        initial_capital=1000000
    )
    
    # 运行优化（10 次试验，快速测试）
    print("\n[测试] 开始优化 MACD 策略参数...")
    best_params = optimizer.optimize_macd(
        n_trials=10,
        timeout=120,  # 2 分钟超时
        prune_bad_trials=False
    )
    
    # 生成可视化图表
    print("\n[测试] 生成可视化图表...")
    optimizer.plot_all(save=True)
    
    # 对比优化前后的性能
    print("\n" + "=" * 80)
    print("参数对比：优化前 vs 优化后")
    print("=" * 80)
    
    # 默认参数（优化前）
    default_params = {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9
    }
    
    print("\n【优化前 - 默认参数】")
    for key, value in default_params.items():
        print(f"  - {key}: {value}")
    
    print("\n【优化后 - 最优参数】")
    for key, value in best_params.items():
        default_value = default_params.get(key, 'N/A')
        change = "↑" if value > default_value else ("↓" if value < default_value else "=")
        print(f"  - {key}: {value} ({change} {default_value})")
    
    # 使用最优参数运行回测
    print("\n[测试] 使用最优参数运行回测验证...")
    engine = BacktraderEngine(config={'initial_capital': 1000000})
    
    results_optimized = engine.run_macd(
        code=code,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        **best_params
    )
    
    # 使用默认参数运行回测
    results_default = engine.run_macd(
        code=code,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        **default_params
    )
    
    # 对比结果
    print("\n" + "=" * 80)
    print("性能对比：优化前 vs 优化后")
    print("=" * 80)
    
    metrics_default = results_default.get('metrics', {})
    metrics_optimized = results_optimized.get('metrics', {})
    
    print("\n【关键指标】")
    print(f"{'指标':<20} {'优化前':<15} {'优化后':<15} {'提升':<10}")
    print("-" * 60)
    
    for metric in ['sharpe_ratio', 'total_return', 'max_drawdown', 'sortino_ratio']:
        val_default = metrics_default.get(metric, 0)
        val_optimized = metrics_optimized.get(metric, 0)
        
        if val_default != 0:
            improvement = ((val_optimized - val_default) / abs(val_default)) * 100
        else:
            improvement = 0
        
        if metric in ['max_drawdown']:
            # 回撤越小越好
            symbol = "↓" if val_optimized < val_default else "↑"
        else:
            # 其他指标越大越好
            symbol = "↑" if val_optimized > val_default else "↓"
        
        print(f"{metric:<20} {val_default:<15.4f} {val_optimized:<15.4f} {symbol} {improvement:+.2f}%")
    
    # 输出优化报告
    report_path = os.path.join(optimizer.results_dir, 'optimization_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("BobQuant Optuna 参数优化报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"股票代码：{code}\n")
        f.write(f"优化时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"时间范围：{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}\n")
        f.write(f"试验次数：10\n\n")
        
        f.write("最优参数:\n")
        for key, value in best_params.items():
            f.write(f"  - {key}: {value}\n")
        
        f.write(f"\n最优夏普比率：{optimizer.best_value:.4f}\n\n")
        
        f.write("性能对比:\n")
        f.write(f"{'指标':<20} {'优化前':<15} {'优化后':<15} {'提升':<10}\n")
        f.write("-" * 60 + "\n")
        
        for metric in ['sharpe_ratio', 'total_return', 'max_drawdown', 'sortino_ratio']:
            val_default = metrics_default.get(metric, 0)
            val_optimized = metrics_optimized.get(metric, 0)
            
            if val_default != 0:
                improvement = ((val_optimized - val_default) / abs(val_default)) * 100
            else:
                improvement = 0
            
            f.write(f"{metric:<20} {val_default:<15.4f} {val_optimized:<15.4f} {improvement:+.2f}%\n")
    
    print(f"\n[测试] ✅ 优化报告已保存：{report_path}")
    print(f"[测试] ✅ 所有结果已保存到：{optimizer.results_dir}")
    
    print("\n" + "=" * 80)
    print("✅ Optuna 参数优化快速测试完成!")
    print("=" * 80)
    
    return {
        'best_params': best_params,
        'default_params': default_params,
        'metrics_default': metrics_default,
        'metrics_optimized': metrics_optimized,
        'results_dir': optimizer.results_dir
    }


if __name__ == '__main__':
    results = run_quick_test()
