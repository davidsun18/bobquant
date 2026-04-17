#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多时间框架分析测试脚本
======================

测试 Backtrader 多时间框架分析功能
生成示例数据并演示信号分析
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backtrader_multiframe import MultiFrameAnalyzer, T0MultiFrameStrategy
import backtrader as bt


def generate_sample_data():
    """
    生成示例日线和分钟线数据
    
    返回：
    daily_df, minute_df
    """
    print("生成示例数据...")
    
    # 生成日线数据（60 天）
    dates_daily = pd.date_range(start='2026-01-01', periods=60, freq='D')
    np.random.seed(42)
    
    # 模拟上涨趋势的日线数据
    close_daily = pd.Series(100 + np.cumsum(np.random.randn(60) * 2 + 0.5))
    open_daily = close_daily.shift(1).fillna(close_daily.iloc[0])
    high_daily = np.maximum(open_daily, close_daily) + np.abs(np.random.randn(60))
    low_daily = np.minimum(open_daily, close_daily) - np.abs(np.random.randn(60))
    volume_daily = np.random.randint(1000000, 5000000, 60)
    
    daily_df = pd.DataFrame({
        'datetime': dates_daily,
        'open': open_daily.values,
        'high': high_daily,
        'low': low_daily,
        'close': close_daily.values,
        'volume': volume_daily
    })
    
    # 生成分钟线数据（最近 5 天，每天 240 分钟）
    minute_data = []
    last_close = close_daily.iloc[-1]
    
    for day in range(5):
        date = dates_daily[-5 + day]
        for minute in range(240):  # 4 小时交易时间
            dt = date + timedelta(hours=9, minutes=30 + minute)
            
            # 模拟分钟线波动
            noise = np.random.randn() * 0.3
            trend = 0.01 * minute if day % 2 == 0 else -0.01 * minute
            
            close = last_close + noise + trend
            open_p = last_close
            high = max(open_p, close) + abs(np.random.randn() * 0.2)
            low = min(open_p, close) - abs(np.random.randn() * 0.2)
            volume = np.random.randint(10000, 50000)
            
            minute_data.append({
                'datetime': dt,
                'open': open_p,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
            
            last_close = close
    
    minute_df = pd.DataFrame(minute_data)
    
    print(f"  ✓ 日线数据：{len(daily_df)}条")
    print(f"  ✓ 分钟线数据：{len(minute_df)}条")
    
    return daily_df, minute_df


def test_multiframe_analysis():
    """测试多时间框架分析"""
    print("\n" + "=" * 60)
    print("测试多时间框架信号分析")
    print("=" * 60)
    
    # 生成示例数据
    daily_df, minute_df = generate_sample_data()
    
    # 创建分析器
    analyzer = MultiFrameAnalyzer(daily_df, minute_df)
    
    # 分析信号
    print("\n分析信号...")
    results = analyzer.analyze_signals()
    
    # 输出结果
    print("\n" + "-" * 60)
    print("信号统计结果")
    print("-" * 60)
    print(f"总信号数：{results['total_signals']}")
    print(f"买入信号：{results['buy_signals']}")
    print(f"卖出信号：{results['sell_signals']}")
    
    print("\n按日线趋势分布：")
    trend_map = {1: '上涨', -1: '下跌', 0: '震荡'}
    for trend, signals in results['trend_distribution'].items():
        print(f"  日线{trend_map.get(trend[0], '未知')}: {signals}个信号")
    
    # 显示最近的信号
    signals_df = results['signals_df']
    recent_signals = signals_df[signals_df['signal'] != 0].tail(10)
    
    if len(recent_signals) > 0:
        print("\n最近 10 个信号：")
        print("-" * 60)
        for idx, row in recent_signals.iterrows():
            signal_type = "买入" if row['signal'] == 1 else "卖出"
            print(f"{row['datetime']} | 价格={row['close']:.2f} | "
                  f"日线{trend_map.get(row['daily_trend'], '震荡')} | {signal_type}")
    
    return results


def test_backtrader_integration():
    """测试 Backtrader 集成"""
    print("\n" + "=" * 60)
    print("测试 Backtrader 多时间框架集成")
    print("=" * 60)
    
    # 生成示例数据
    daily_df, minute_df = generate_sample_data()
    
    # 创建 Cerebro 引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(T0MultiFrameStrategy, printlog=False)
    
    # 转换数据格式
    daily_df = daily_df.set_index('datetime')
    minute_df = minute_df.set_index('datetime')
    
    # 创建数据源
    data_daily = bt.feeds.PandasData(
        dataname=daily_df,
        datetime=None,  # 使用索引
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        timeframe=bt.TimeFrame.Days
    )
    
    data_minute = bt.feeds.PandasData(
        dataname=minute_df,
        datetime=None,
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        timeframe=bt.TimeFrame.Minutes
    )
    
    # 添加数据
    cerebro.adddata(data_daily)
    cerebro.adddata(data_minute)
    
    # 设置资金
    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.0003)
    
    # 打印初始状态
    print(f"\n初始资金：¥{cerebro.broker.getvalue():.2f}")
    
    # 运行回测
    print("\n运行回测...")
    results = cerebro.run()
    
    # 打印最终状态
    final_value = cerebro.broker.getvalue()
    print(f"\n最终资金：¥{final_value:.2f}")
    print(f"收益率：{(final_value - 100000) / 100000 * 100:.2f}%")
    
    return results


def show_multiframe_examples():
    """显示多时间框架信号示例"""
    print("\n" + "=" * 60)
    print("多时间框架信号示例")
    print("=" * 60)
    
    examples = [
        {
            "场景": "强买入信号",
            "日线趋势": "上涨 (SMA5>SMA20, RSI>50)",
            "分钟线": "回调到布林带下轨，RSI<40",
            "操作": "买入开仓",
            "胜率": "高（多时间框架共振）"
        },
        {
            "场景": "强卖出信号",
            "日线趋势": "下跌 (SMA5<SMA20, RSI<50)",
            "分钟线": "反弹到布林带上轨，RSI>60",
            "操作": "卖出平仓",
            "胜率": "高（多时间框架共振）"
        },
        {
            "场景": "震荡市超卖",
            "日线趋势": "震荡 (SMA 粘合，RSI 在 40-60)",
            "分钟线": "RSI<20 极端超卖",
            "操作": "轻仓博反弹",
            "胜率": "中（仅分钟线信号）"
        },
        {
            "场景": "震荡市超买",
            "日线趋势": "震荡 (SMA 粘合，RSI 在 40-60)",
            "分钟线": "RSI>80 极端超买",
            "操作": "轻仓博回调",
            "胜率": "中（仅分钟线信号）"
        },
        {
            "场景": "信号冲突",
            "日线趋势": "上涨",
            "分钟线": "卖出信号（超买）",
            "操作": "观望或减仓",
            "胜率": "低（时间框架冲突）"
        }
    ]
    
    for i, ex in enumerate(examples, 1):
        print(f"\n【示例{i}】{ex['场景']}")
        print(f"  日线趋势：{ex['日线趋势']}")
        print(f"  分钟线：{ex['分钟线']}")
        print(f"  操作：{ex['操作']}")
        print(f"  预期胜率：{ex['胜率']}")
    
    print("\n" + "-" * 60)
    print("核心原则：")
    print("1. 日线定方向，分钟线找点位")
    print("2. 多时间框架共振时胜率最高")
    print("3. 时间框架冲突时优先观望")
    print("4. 震荡市降低仓位，只做极端信号")


def provide_improvement_suggestions():
    """提供做 T 策略改进建议"""
    print("\n" + "=" * 60)
    print("对做 T 策略的改进建议")
    print("=" * 60)
    
    suggestions = [
        {
            "方面": "信号优化",
            "建议": [
                "增加更多日线确认指标（如 MACD、成交量）",
                "引入多周期共振（日线 + 60 分钟 + 5 分钟）",
                "添加市场情绪过滤（大盘走势、板块强度）",
                "使用机器学习模型优化信号权重"
            ]
        },
        {
            "方面": "仓位管理",
            "建议": [
                "根据日线趋势强度动态调整做 T 仓位",
                "上涨趋势：做 T 仓位 30-50%",
                "下跌趋势：做 T 仓位 10-20% 或空仓",
                "震荡市：做 T 仓位 20-30%，快进快出"
            ]
        },
        {
            "方面": "止盈止损",
            "建议": [
                "动态止盈：根据 ATR 调整止盈目标",
                "移动止损：盈利后跟踪止损保护利润",
                "时间止损：超过 N 分钟未达目标自动平仓",
                "分批止盈：50% 仓位在 1% 止盈，50% 在 2% 止盈"
            ]
        },
        {
            "方面": "风险控制",
            "建议": [
                "单日最大亏损限制（如总资金 2%）",
                "单只股票最大仓位限制（如 30%）",
                "连续亏损 N 次后暂停交易",
                "避开重大事件日（财报、政策发布）"
            ]
        },
        {
            "方面": "执行优化",
            "建议": [
                "使用限价单而非市价单减少滑点",
                "在流动性好的时段交易（开盘后 30 分钟、收盘前 30 分钟）",
                "监控盘口深度，避免大单冲击",
                "实现自动撤单重报机制"
            ]
        },
        {
            "方面": "回测验证",
            "建议": [
                "使用至少 6 个月历史数据回测",
                "测试不同市场环境（牛市、熊市、震荡）",
                "考虑手续费和滑点的真实成本",
                "对比单时间框架 vs 多时间框架的胜率差异"
            ]
        }
    ]
    
    for sug in suggestions:
        print(f"\n【{sug['方面']}】")
        for item in sug['建议']:
            print(f"  • {item}")
    
    print("\n" + "-" * 60)
    print("实施优先级：")
    print("1. 高优先级：信号优化 + 仓位管理（立即实施）")
    print("2. 中优先级：止盈止损 + 风险控制（1 周内）")
    print("3. 低优先级：执行优化 + 回测验证（持续改进）")
    print("-" * 60)


def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("Backtrader 多时间框架分析测试")
    print("🚀" * 30)
    
    # 测试 1: 信号分析
    test_multiframe_analysis()
    
    # 测试 2: Backtrader 集成
    test_backtrader_integration()
    
    # 测试 3: 信号示例
    show_multiframe_examples()
    
    # 测试 4: 改进建议
    provide_improvement_suggestions()
    
    print("\n" + "✅" * 30)
    print("测试完成！")
    print("✅" * 30)
    
    print("\n📁 创建的文件：")
    print("  1. backtrader_multiframe.py - 多时间框架分析模块")
    print("  2. test_multiframe.py - 测试脚本（本文件）")
    
    print("\n📊 多时间框架信号示例：")
    print("  • 强买入：日线上涨 + 分钟线回调 → 高胜率")
    print("  • 强卖出：日线下跌 + 分钟线反弹 → 高胜率")
    print("  • 震荡市：只做 RSI 极端信号 → 中胜率")
    
    print("\n💡 做 T 策略改进建议：")
    print("  • 动态仓位管理（根据趋势强度）")
    print("  • 移动止损保护利润")
    print("  • 多周期共振提高胜率")
    print("  • 避开重大事件日")


if __name__ == "__main__":
    main()
