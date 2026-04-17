# -*- coding: utf-8 -*-
"""
多因子选股策略测试脚本

测试内容：
1. 对 50 只股票进行因子打分
2. 输出 TOP 10 选股结果
3. 验证因子计算公式
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.multi_factor import (
    FactorCalculator, 
    StockSelector, 
    MultiFactorStrategy,
    test_multi_factor_strategy
)


def run_full_test():
    """运行完整测试"""
    print("\n" + "=" * 70)
    print("BobQuant 多因子选股策略 - 完整测试")
    print("=" * 70 + "\n")
    
    # 测试股票池（50 只 A 股）
    test_stock_pool = [
        # 银行/金融
        'sh.600000', 'sh.600036', 'sh.600016', 'sh.601288', 'sh.601398',
        'sh.601988', 'sh.601166', 'sh.601009', 'sz.000001', 'sz.000002',
        
        # 白酒/消费
        'sh.600519', 'sh.600809', 'sh.600887', 'sz.000858', 'sz.000568',
        'sz.000596', 'sz.000651', 'sz.002415',
        
        # 保险/券商
        'sh.601318', 'sh.601601', 'sh.601628', 'sh.601688', 'sh.600030',
        
        # 能源/石化
        'sh.600028', 'sh.601857', 'sh.601989', 'sh.600256', 'sh.600309',
        
        # 科技/制造
        'sh.600009', 'sh.600048', 'sh.600050', 'sh.600104', 'sh.600276',
        'sh.600346', 'sh.600436', 'sh.600518', 'sh.600547', 'sh.600585',
        'sh.600588', 'sh.600690', 'sh.600900', 'sh.601012', 'sh.601088',
        'sz.000063', 'sz.000100', 'sz.000157', 'sz.000333', 'sz.000538',
        
        # 旅游/其他
        'sh.601888', 'sh.603259', 'sh.601766',
    ]
    
    print(f"测试股票池：{len(test_stock_pool)} 只股票")
    print("包含：银行、白酒、保险、能源、科技等多个行业\n")
    
    # 创建选股器
    calculator = FactorCalculator()
    selector = StockSelector(calculator, top_n=10)
    
    # 因子权重配置
    weights = {
        'value': 0.30,    # 价值因子 30%
        'growth': 0.25,   # 成长因子 25%
        'momentum': 0.25, # 动量因子 25%
        'quality': 0.20,  # 质量因子 20%
    }
    
    print("因子权重配置:")
    for factor, weight in weights.items():
        print(f"  - {factor}: {weight*100:.0f}%")
    print()
    
    # 运行选股
    print("正在计算因子得分...\n")
    ranking = selector.select_stocks(test_stock_pool, weights)
    
    if ranking:
        # 输出结果
        print("=" * 70)
        print("TOP 10 选股结果")
        print("=" * 70)
        header = f"{'排名':<4} {'代码':<10} {'名称':<10} {'总分':<7} {'价值':<7} {'成长':<7} {'动量':<7} {'质量':<7}"
        print(header)
        print("-" * 70)
        
        for i, stock in enumerate(ranking, 1):
            row = (f"{i:<4} {stock['code']:<10} {stock['name']:<10} "
                   f"{stock['total_score']:<7.1f} {stock['value_score']:<7.1f} "
                   f"{stock['growth_score']:<7.1f} {stock['momentum_score']:<7.1f} "
                   f"{stock['quality_score']:<7.1f}")
            print(row)
        
        print("=" * 70)
        
        # 详细分析第一名
        if ranking:
            top_stock = ranking[0]
            print(f"\n🏆 第一名详细分析：{top_stock['code']} {top_stock['name']}")
            print(f"   综合得分：{top_stock['total_score']:.1f}")
            print(f"   价值因子：{top_stock['value_score']:.1f} - {'优秀' if top_stock['value_score']>=70 else '良好' if top_stock['value_score']>=50 else '一般'}")
            print(f"   成长因子：{top_stock['growth_score']:.1f} - {'优秀' if top_stock['growth_score']>=70 else '良好' if top_stock['growth_score']>=50 else '一般'}")
            print(f"   动量因子：{top_stock['momentum_score']:.1f} - {'优秀' if top_stock['momentum_score']>=70 else '良好' if top_stock['momentum_score']>=50 else '一般'}")
            print(f"   质量因子：{top_stock['quality_score']:.1f} - {'优秀' if top_stock['quality_score']>=70 else '良好' if top_stock['quality_score']>=50 else '一般'}")
            
            fundamental = top_stock.get('fundamental', {})
            if fundamental:
                print(f"\n   基本面数据:")
                print(f"   - PE: {fundamental.get('pe', 'N/A')}")
                print(f"   - PB: {fundamental.get('pb', 'N/A')}")
                print(f"   - ROE: {fundamental.get('roe', 'N/A')}%")
                print(f"   - 营收增长：{fundamental.get('revenue_growth', 'N/A')}%")
                print(f"   - 利润增长：{fundamental.get('profit_growth', 'N/A')}%")
                print(f"   - 毛利率：{fundamental.get('gross_margin', 'N/A')}%")
                print(f"   - 净利率：{fundamental.get('net_margin', 'N/A')}%")
                print(f"   - 20 日动量：{top_stock.get('momentum_20', 'N/A')}%")
                print(f"   - 60 日动量：{top_stock.get('momentum_60', 'N/A')}%")
        
        print("\n" + "=" * 70)
        print("因子计算公式")
        print("=" * 70)
        print("""
【价值因子】(权重 30%)
  PE 得分 = (100 - PE) × 100/90, PE 有效范围 [10, 100]
  PB 得分 = (10 - PB) × 100/9, PB 有效范围 [1, 10]
  ROE 得分 = ROE × 5, ROE 有效范围 [0, 20]
  价值得分 = PE 得分×0.4 + PB 得分×0.3 + ROE 得分×0.3

【成长因子】(权重 25%)
  营收增长得分 = 营收增长率 × 2, 有效范围 [0, 50%]
  利润增长得分 = 利润增长率 × 2, 有效范围 [0, 50%]
  成长得分 = 营收得分×0.4 + 利润得分×0.6

【动量因子】(权重 25%)
  20 日动量 = (当前收盘价 - 20 日前收盘价) / 20 日前收盘价 × 100%
  60 日动量 = (当前收盘价 - 60 日前收盘价) / 60 日前收盘价 × 100%
  动量得分 = (20 日动量 +50)×100/100 × 0.6 + (60 日动量 +50)×100/100 × 0.4

【质量因子】(权重 20%)
  毛利率得分 = 毛利率 × 2, 有效范围 [0, 50%]
  净利率得分 = 净利率 × 3.33, 有效范围 [0, 30%]
  质量得分 = 毛利率得分×0.4 + 净利率得分×0.6

【综合得分】
  总分 = 价值×0.30 + 成长×0.25 + 动量×0.25 + 质量×0.20

【选股标准】
  - 总分 ≥ 70: 强烈推荐 (strong buy)
  - 总分 ≥ 55: 推荐 (normal buy)
  - 总分 < 30: 卖出 (sell)
        """)
        
        print("=" * 70)
        print("与现有策略的集成方式")
        print("=" * 70)
        print("""
【方式 1: 作为独立策略使用】

在配置文件中设置:
```python
config = {
    'strategy': 'multi_factor',
    'factor_weights': {
        'value': 0.30,
        'growth': 0.25,
        'momentum': 0.25,
        'quality': 0.20,
    },
    'top_n': 10,
    'stock_pool': ['sh.600000', 'sz.000001', ...],
}
```

在策略引擎中使用:
```python
from strategy.engine import get_strategy
strategy = get_strategy('multi_factor')
signal = strategy.check(code, name, quote, df, pos, config)
```

【方式 2: 作为选股器使用】

每日开盘前运行选股:
```python
from strategy.multi_factor import StockSelector, FactorCalculator

calculator = FactorCalculator()
selector = StockSelector(calculator, top_n=10)
top_stocks = selector.select_stocks(stock_pool)

# 对 TOP 10 股票执行买入逻辑
for stock in top_stocks:
    if stock['total_score'] >= 55:
        buy(stock['code'])
```

【方式 3: 集成到决策引擎】

在 DecisionEngine 中添加多因子信号源:
```python
class DecisionEngine:
    def __init__(self, config):
        self.multi_factor = MultiFactorStrategy(config)
    
    def combine_signals(self, code, name, quote, df, pos, ...):
        # 获取多因子信号
        mf_signal = self.multi_factor.check(code, name, quote, df, pos, config)
        
        # 与其他信号合并
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
- 买入新进入 TOP 10 的股票
- 卖出跌出 TOP 20 的股票
- 保持持仓在 10-15 只股票
        """)
        
    else:
        print("⚠️ 未能获取到有效的选股结果")
        print("可能原因:")
        print("  1. 网络问题导致数据获取失败")
        print("  2. 股票代码格式不正确")
        print("  3. 数据源暂时不可用")
        print("\n建议:")
        print("  - 检查网络连接")
        print("  - 验证股票代码格式 (sh.xxxxxx / sz.xxxxxx)")
        print("  - 尝试使用其他数据源")
    
    print("\n" + "=" * 70)
    print("测试完成!")
    print("=" * 70 + "\n")
    
    return ranking


if __name__ == '__main__':
    results = run_full_test()
    
    # 保存结果到文件
    if results:
        output_file = os.path.join(os.path.dirname(__file__), 'multi_factor_test_result.txt')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("BobQuant 多因子选股策略测试结果\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"测试时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"测试股票数量：50 只\n\n")
            f.write("TOP 10 选股结果:\n")
            f.write("-" * 60 + "\n")
            for i, stock in enumerate(results, 1):
                f.write(f"{i}. {stock['code']} {stock['name']} - 总分:{stock['total_score']:.1f}\n")
                f.write(f"   价值:{stock['value_score']:.1f} 成长:{stock['growth_score']:.1f} ")
                f.write(f"动量:{stock['momentum_score']:.1f} 质量:{stock['quality_score']:.1f}\n")
        print(f"📄 测试结果已保存到：{output_file}")
