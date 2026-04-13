# -*- coding: utf-8 -*-
"""
PyFolio 集成测试脚本

测试对模拟盘数据进行 PyFolio 绩效分析
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# 添加 bobquant 到路径
import sys
sys.path.insert(0, '/home/openclaw/.openclaw/workspace/quant_strategies')

from bobquant.analysis.pyfolio_analysis import PyFolioAnalyzer, generate_report, format_report


def load_sim_trading_data():
    """加载模拟盘交易数据"""
    trade_file = Path('/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json')
    
    if not trade_file.exists():
        print(f"❌ 交易记录文件不存在：{trade_file}")
        return None
    
    with open(trade_file, 'r', encoding='utf-8') as f:
        trades = json.load(f)
    
    print(f"✅ 加载了 {len(trades)} 条交易记录")
    return trades


def convert_to_analysis_format(trades):
    """
    将模拟盘交易数据转换为分析格式
    
    Args:
        trades: 原始交易记录列表
        
    Returns:
        trades_df: 标准化的交易 DataFrame
    """
    df = pd.DataFrame(trades)
    
    # 转换时间格式
    df['date'] = pd.to_datetime(df['time']).dt.date
    df['datetime'] = pd.to_datetime(df['time'])
    
    # 标准化代码格式
    df['code'] = df['code'].apply(lambda x: x.replace('.', '') if isinstance(x, str) else x)
    
    # 计算盈亏（pnl）
    # 如果有 profit 字段，直接使用
    if 'profit' in df.columns:
        df['pnl'] = df['profit'].fillna(0)
    else:
        df['pnl'] = 0
    
    # 计算方向（1=买入，-1=卖出）
    def get_direction(action):
        if isinstance(action, str):
            if '买入' in action or '加仓' in action:
                return 1
            elif '卖出' in action or '减仓' in action:
                return -1
        return 0
    
    df['direction'] = df['action'].apply(get_direction)
    
    # 标准化列名
    standardized_df = pd.DataFrame({
        'date': df['date'],
        'datetime': df['datetime'],
        'code': df['code'],
        'pnl': df['pnl'],
        'amount': df.get('amount', 0),
        'shares': df.get('shares', 0),
        'price': df.get('price', 0),
        'direction': df['direction'],
        'action': df['action']
    })
    
    print(f"✅ 数据转换完成：{len(standardized_df)} 条记录")
    print(f"   时间范围：{standardized_df['date'].min()} 至 {standardized_df['date'].max()}")
    print(f"   标的数量：{standardized_df['code'].nunique()}")
    
    return standardized_df


def run_pyfolio_analysis():
    """运行 PyFolio 分析"""
    print("=" * 70)
    print("🚀 PyFolio 绩效分析测试")
    print("=" * 70)
    
    # 加载数据
    trades = load_sim_trading_data()
    if trades is None:
        return
    
    # 转换数据格式
    trades_df = convert_to_analysis_format(trades)
    
    # 创建分析器
    initial_capital = 500000.0  # 假设初始资金 50 万
    analyzer = PyFolioAnalyzer(initial_capital=initial_capital)
    
    print("\n" + "=" * 70)
    print("📊 开始绩效分析...")
    print("=" * 70 + "\n")
    
    # 生成报告
    report = analyzer.generate_report(trades_df)
    
    # 打印文本报告
    print(format_report(report))
    
    # 输出关键指标
    print("\n" + "=" * 70)
    print("📈 关键绩效指标摘要")
    print("=" * 70)
    
    metrics = report.get('metrics', {})
    if 'error' not in metrics:
        print(f"""
总收益率：     {metrics.get('total_return', 0)*100:+.2f}%
年化收益：     {metrics.get('annual_return', 0)*100:+.2f}%
Sharpe 比率：   {metrics.get('sharpe', 0):.3f}
Sortino 比率：  {metrics.get('sortino', 0):.3f}
Calmar 比率：   {metrics.get('calmar', 0):.3f}
最大回撤：     {metrics.get('max_drawdown', 0)*100:.2f}%
胜率：         {metrics.get('win_rate', 0)*100:.1f}%
""")
    
    # HTML 报告
    if report.get('html_report'):
        print(f"✅ HTML 报告已生成：{report['html_report']}")
    else:
        print("⚠️ HTML 报告未生成（可能数据不足或 pyfolio 不可用）")
    
    return report


def create_sample_report():
    """创建示例报告（使用模拟数据）"""
    print("\n" + "=" * 70)
    print("📝 创建示例报告（模拟数据）")
    print("=" * 70)
    
    # 生成模拟交易数据（60 天，足够生成 HTML 报告）
    np.random.seed(42)
    n_days = 60
    dates = pd.date_range('2024-01-01', periods=n_days, freq='D')
    
    # 模拟每日盈亏（略微盈利）
    daily_pnl = np.random.randn(n_days) * 3000 + 500
    
    # 创建交易记录
    trades = []
    for i, (date, pnl) in enumerate(zip(dates, daily_pnl)):
        # 每天生成 1-3 笔交易
        n_trades = np.random.randint(1, 4)
        for j in range(n_trades):
            trades.append({
                'date': date,
                'datetime': date,
                'code': f'00000{i % 10}.SZ',
                'pnl': pnl / n_trades,
                'amount': 10000,
                'shares': 100,
                'price': 20.0 + np.random.randn(),
                'direction': 1 if pnl > 0 else -1,
                'action': 'buy' if pnl > 0 else 'sell'
            })
    
    trades_df = pd.DataFrame(trades)
    
    # 运行分析
    analyzer = PyFolioAnalyzer(initial_capital=500000.0)
    report = analyzer.generate_report(trades_df)
    
    # 打印报告
    print("\n" + format_report(report))
    
    return report


if __name__ == '__main__':
    # 运行真实数据分析
    report = run_pyfolio_analysis()
    
    # 创建示例报告
    try:
        sample_report = create_sample_report()
    except Exception as e:
        print(f"\n⚠️ 示例报告生成失败：{e}")
        print("   这可能是由于 pyfolio 与 numpy 2.0 的兼容性问题")
    
    print("\n" + "=" * 70)
    print("✅ PyFolio 集成测试完成!")
    print("=" * 70)
