#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant 回测运行脚本 v2.0

用法：
  python3 run_backtest.py [策略名] [开始日期] [结束日期]

示例：
  python3 run_backtest.py macd 2024-01-01 2024-12-31
  python3 run_backtest.py dual_macd 2025-09-01 2025-11-30
  python3 run_backtest.py bollinger 2024-01-01 2025-12-31
"""
import sys
import os

# 添加项目根目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

from backtest.engine import run_backtest


def load_stock_pool(pool_file='config/stock_pool_v2.yaml'):
    """加载股票池"""
    import yaml
    with open(pool_file, 'r', encoding='utf-8') as f:
        pool = yaml.safe_load(f)
    return pool


def load_simple_config():
    """加载简单配置"""
    return {
        'initial_capital': 1000000,
        'commission_rate': 0.0005,
        'stamp_duty_rate': 0.001,
        'use_dual_macd': True,
        'use_dynamic_bollinger': True,
        'enable_risk_filters': True,
        'enable_market_risk': True,
        'min_turnover': 50000000,
        'rsi_buy_max': 35,
        'rsi_sell_min': 70,
        'volume_confirm': True,
        'volume_ratio_buy': 1.5,
        'stop_loss_pct': -0.08,
        'trailing_activation': 0.05,
        'trailing_dip': 0.02,
    }


def main():
    # 解析参数
    strategy = sys.argv[1] if len(sys.argv) > 1 else 'dual_macd'
    start_date = sys.argv[2] if len(sys.argv) > 2 else '2024-01-01'
    end_date = sys.argv[3] if len(sys.argv) > 3 else '2024-12-31'
    
    print("=" * 60)
    print("🚀 BobQuant 回测系统 v2.0")
    print("=" * 60)
    print(f"策略：    {strategy}")
    print(f"时间段：  {start_date} → {end_date}")
    print("=" * 60)
    
    # 加载配置
    config = load_simple_config()
    
    # 加载股票池
    stock_pool = load_stock_pool()
    print(f"股票池：  {len(stock_pool)} 只股票")
    
    # 运行回测
    results = run_backtest(config, stock_pool, start_date, end_date, strategy)
    
    # 导出报告
    report_path = f"backtest/reports/backtest_{strategy}_{start_date}_{end_date}.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    from backtest.engine import BacktestEngine
    engine = BacktestEngine(config)
    engine.export_report(results, report_path)
    
    print(f"\n✅ 回测完成！")
    print(f"📄 报告：{report_path}")
    
    return results


if __name__ == '__main__':
    main()
