# -*- coding: utf-8 -*-
"""
多因子选股策略 - 演示测试脚本

使用模拟数据演示多因子选股策略的功能
"""
import sys
import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.multi_factor import FactorCalculator, StockSelector


def generate_mock_history(days=60):
    """生成模拟历史 K 线数据"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # 生成随机价格走势
    base_price = random.uniform(10, 100)
    prices = [base_price]
    for i in range(1, days):
        change = random.uniform(-0.05, 0.05)
        prices.append(prices[-1] * (1 + change))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * random.uniform(1.01, 1.03) for p in prices],
        'low': [p * random.uniform(0.97, 0.99) for p in prices],
        'close': prices,
        'volume': [random.uniform(1e6, 1e8) for _ in range(days)]
    })
    df.set_index('date', inplace=True)
    return df


def generate_mock_fundamental():
    """生成模拟基本面数据"""
    return {
        'pe': random.uniform(5, 50),
        'pb': random.uniform(0.5, 5),
        'roe': random.uniform(-5, 25),
        'revenue_growth': random.uniform(-20, 50),
        'profit_growth': random.uniform(-30, 60),
        'gross_margin': random.uniform(10, 60),
        'net_margin': random.uniform(5, 30),
    }


class MockFactorCalculator(FactorCalculator):
    """使用模拟数据的因子计算器"""
    
    def get_fundamental_data(self, code: str) -> dict:
        return generate_mock_fundamental()
    
    def get_history(self, code: str, days: int = 60):
        return generate_mock_history(days)


def run_demo():
    """运行演示"""
    print("\n" + "=" * 80)
    print("BobQuant 多因子选股策略 - 演示 (使用模拟数据)")
    print("=" * 80 + "\n")
    
    # 测试股票池（50 只股票）
    stock_pool = [
        'sh.600000', 'sh.600036', 'sh.600016', 'sh.601288', 'sh.601398',
        'sh.601988', 'sh.601166', 'sh.601009', 'sz.000001', 'sz.000002',
        'sh.600519', 'sh.600809', 'sh.600887', 'sz.000858', 'sz.000568',
        'sz.000596', 'sz.000651', 'sz.002415', 'sh.601318', 'sh.601601',
        'sh.601628', 'sh.601688', 'sh.600030', 'sh.600028', 'sh.601857',
        'sh.601989', 'sh.600256', 'sh.600309', 'sh.600009', 'sh.600048',
        'sh.600050', 'sh.600104', 'sh.600276', 'sh.600346', 'sh.600436',
        'sh.600518', 'sh.600547', 'sh.600585', 'sh.600588', 'sh.600690',
        'sh.600900', 'sh.601012', 'sh.601088', 'sz.000063', 'sz.000100',
        'sz.000157', 'sz.000333', 'sz.000538', 'sh.601888', 'sh.603259',
    ]
    
    print(f"📊 测试股票池：{len(stock_pool)} 只股票")
    print("   行业分布：银行、白酒、保险、证券、能源、科技、制造等\n")
    
    # 创建计算器（使用模拟数据）
    calculator = MockFactorCalculator()
    selector = StockSelector(calculator, top_n=10)
    
    # 因子权重
    weights = {
        'value': 0.30,
        'growth': 0.25,
        'momentum': 0.25,
        'quality': 0.20,
    }
    
    print("⚖️  因子权重配置:")
    print(f"   - 价值因子 (Value):   {weights['value']*100:.0f}%  (PE/PB/ROE)")
    print(f"   - 成长因子 (Growth):  {weights['growth']*100:.0f}%  (营收增长/利润增长)")
    print(f"   - 动量因子 (Momentum): {weights['momentum']*100:.0f}%  (20 日/60 日动量)")
    print(f"   - 质量因子 (Quality): {weights['quality']*100:.0f}%  (毛利率/净利率)\n")
    
    print("🔄 正在计算因子得分...\n")
    
    # 执行选股
    ranking = selector.select_stocks(stock_pool, weights)
    
    if ranking:
        # 输出 TOP 10
        print("=" * 80)
        print("🏆 TOP 10 选股结果")
        print("=" * 80)
        
        header = f"{'排名':<4} {'代码':<10} {'总分':<7} {'价值':<7} {'成长':<7} {'动量':<7} {'质量':<7}  评级"
        print(header)
        print("-" * 80)
        
        for i, stock in enumerate(ranking, 1):
            # 根据得分给出评级
            if stock['total_score'] >= 70:
                rating = "★★★ 强烈推荐"
            elif stock['total_score'] >= 55:
                rating = "★★☆ 推荐"
            elif stock['total_score'] >= 40:
                rating = "★☆☆ 持有"
            else:
                rating = "☆☆☆ 卖出"
            
            row = (f"{i:<4} {stock['code']:<10} {stock['total_score']:<7.1f} "
                   f"{stock['value_score']:<7.1f} {stock['growth_score']:<7.1f} "
                   f"{stock['momentum_score']:<7.1f} {stock['quality_score']:<7.1f}  {rating}")
            print(row)
        
        print("=" * 80)
        
        # 详细分析第一名
        top = ranking[0]
        print(f"\n📈 冠军股票详细分析：{top['code']}")
        print(f"   综合得分：{top['total_score']:.1f} / 100")
        print()
        
        # 雷达图数据
        print("   因子得分雷达:")
        factors = [
            ('价值因子', top['value_score']),
            ('成长因子', top['growth_score']),
            ('动量因子', top['momentum_score']),
            ('质量因子', top['quality_score']),
        ]
        
        for name, score in factors:
            bar_len = int(score / 5)
            bar = '█' * bar_len + '░' * (20 - bar_len)
            level = '优秀' if score >= 70 else '良好' if score >= 50 else '一般'
            print(f"   {name}: {bar} {score:.1f} ({level})")
        
        print()
        print("   基本面数据:")
        fundamental = top.get('fundamental', {})
        if fundamental:
            print(f"   - 市盈率 (PE):   {fundamental.get('pe', 'N/A'):.2f}")
            print(f"   - 市净率 (PB):   {fundamental.get('pb', 'N/A'):.2f}")
            print(f"   - 净资产收益 (ROE): {fundamental.get('roe', 'N/A'):.2f}%")
            print(f"   - 营收增长率：   {fundamental.get('revenue_growth', 'N/A'):.2f}%")
            print(f"   - 利润增长率：   {fundamental.get('profit_growth', 'N/A'):.2f}%")
            print(f"   - 毛利率：       {fundamental.get('gross_margin', 'N/A'):.2f}%")
            print(f"   - 净利率：       {fundamental.get('net_margin', 'N/A'):.2f}%")
            print(f"   - 20 日动量：     {top.get('momentum_20', 'N/A'):.2f}%")
            print(f"   - 60 日动量：     {top.get('momentum_60', 'N/A'):.2f}%")
        
        # 因子计算公式
        print("\n" + "=" * 80)
        print("📐 因子计算公式")
        print("=" * 80)
        
        print("""
【1. 价值因子】(权重 30%)
    评估股票估值水平，寻找低估股票
    
    PE 得分 = (100 - PE) × 100/90,  PE 有效范围 [10, 100]
    PB 得分 = (10 - PB) × 100/9,    PB 有效范围 [1, 10]
    ROE 得分 = ROE × 5,             ROE 有效范围 [0, 20]
    
    价值得分 = PE 得分×0.4 + PB 得分×0.3 + ROE 得分×0.3
    说明：PE/PB 越低越好，ROE 越高越好

【2. 成长因子】(权重 25%)
    评估公司成长潜力
    
    营收增长得分 = 营收增长率 × 2,    有效范围 [0, 50%]
    利润增长得分 = 利润增长率 × 2,    有效范围 [0, 50%]
    
    成长得分 = 营收得分×0.4 + 利润得分×0.6
    说明：利润增长权重更高，因为更反映真实盈利能力

【3. 动量因子】(权重 25%)
    评估价格趋势强度
    
    20 日动量 = (当前价 - 20 日前价) / 20 日前价 × 100%
    60 日动量 = (当前价 - 60 日前价) / 60 日前价 × 100%
    
    动量得分 = (20 日动量 +50)×100/100 × 0.6 + (60 日动量 +50)×100/100 × 0.4
    说明：动量>-50% 得分为正，短期动量权重更高

【4. 质量因子】(权重 20%)
    评估盈利质量
    
    毛利率得分 = 毛利率 × 2,       有效范围 [0, 50%]
    净利率得分 = 净利率 × 3.33,     有效范围 [0, 30%]
    
    质量得分 = 毛利率得分×0.4 + 净利率得分×0.6
    说明：净利率权重更高，反映整体盈利能力

【5. 综合得分】
    总分 = 价值×0.30 + 成长×0.25 + 动量×0.25 + 质量×0.20
    
【6. 投资建议】
    总分 ≥ 70:  ★★★ 强烈推荐 (Strong Buy)
    总分 ≥ 55:  ★★☆ 推荐 (Buy)
    总分 ≥ 40:  ★☆☆ 持有 (Hold)
    总分 < 30:  ☆☆☆ 卖出 (Sell)
        """)
        
        # 集成方式
        print("=" * 80)
        print("🔌 与现有策略的集成方式")
        print("=" * 80)
        
        print("""
【方式 1: 作为独立策略】

在 strategy/engine.py 中已注册，可直接使用:

```python
from strategy.engine import get_strategy

strategy = get_strategy('multi_factor', config={
    'factor_weights': {'value': 0.3, 'growth': 0.25, 'momentum': 0.25, 'quality': 0.2},
    'top_n': 10,
    'stock_pool': ['sh.600000', 'sz.000001', ...],
})

signal = strategy.check(code, name, quote, df, pos, config)
```

【方式 2: 作为选股器】

每日开盘前运行选股，生成推荐股票池:

```python
from strategy.multi_factor import StockSelector, FactorCalculator

calculator = FactorCalculator()
selector = StockSelector(calculator, top_n=10)

top_stocks = selector.select_stocks(stock_pool)

# 对 TOP 10 执行买入逻辑
for stock in top_stocks:
    if stock['total_score'] >= 70:
        buy(stock['code'], weight=0.10)
```

【方式 3: 集成到决策引擎】

在 DecisionEngine 中作为信号源之一:

```python
class DecisionEngine:
    def __init__(self, config):
        self.multi_factor = MultiFactorStrategy(config)
    
    def combine_signals(self, code, name, quote, df, pos, ...):
        # 获取多因子信号
        mf_signal = self.multi_factor.check(code, name, quote, df, pos, config)
        
        # 与其他信号 (MACD/布林带/ML) 合并
        if mf_signal['signal'] == 'buy' and mf_signal['total_score'] >= 70:
            signals.append({
                'source': 'multi_factor',
                'signal': 'buy',
                'strength': 'strong',
                'reason': mf_signal['reason'],
            })
```

【方式 4: 定期调仓】

每周/每月运行选股策略，调整持仓:

```python
# 每周一 9:30 调仓
def rebalance():
    top_stocks = selector.select_stocks(stock_pool)
    
    # 卖出跌出前 20 的股票
    # 买入新进入前 10 的股票
    
schedule.every().monday.at("09:30").do(rebalance)
```
        """)
        
        # 保存结果
        output_file = os.path.join(os.path.dirname(__file__), 'multi_factor_demo_result.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("BobQuant 多因子选股策略 - 演示结果\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"演示时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试股票数量：{len(stock_pool)} 只\n\n")
            f.write("TOP 10 选股结果:\n")
            f.write("-" * 60 + "\n")
            for i, stock in enumerate(ranking, 1):
                f.write(f"{i}. {stock['code']} - 总分:{stock['total_score']:.1f}\n")
                f.write(f"   价值:{stock['value_score']:.1f} 成长:{stock['growth_score']:.1f} ")
                f.write(f"动量:{stock['momentum_score']:.1f} 质量:{stock['quality_score']:.1f}\n")
        
        print(f"\n💾 演示结果已保存到：{output_file}")
        
    else:
        print("❌ 未能生成选股结果")
    
    print("\n" + "=" * 80)
    print("✅ 演示完成!")
    print("=" * 80 + "\n")
    
    return ranking


if __name__ == '__main__':
    results = run_demo()
