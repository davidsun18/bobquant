# 多因子选股策略配置示例

## 基础配置

```python
# 在 config/settings.py 或主配置文件中添加

MULTI_FACTOR_CONFIG = {
    # 策略名称
    'strategy': 'multi_factor',
    
    # 选股数量
    'top_n': 10,
    
    # 因子权重（总和应为 1.0）
    'factor_weights': {
        'value': 0.30,    # 价值因子 30% - 适合价值投资者
        'growth': 0.25,   # 成长因子 25%
        'momentum': 0.25, # 动量因子 25%
        'quality': 0.20,  # 质量因子 20%
    },
    
    # 股票池（示例）
    'stock_pool': [
        # 银行
        'sh.600000', 'sh.600036', 'sh.600016', 'sh.601288', 'sh.601398',
        'sh.601988', 'sh.601166', 'sz.000001',
        
        # 白酒
        'sh.600519', 'sh.600809', 'sh.600887', 'sz.000858', 'sz.000568',
        
        # 保险/券商
        'sh.601318', 'sh.601601', 'sh.601628', 'sh.601688',
        
        # 能源
        'sh.600028', 'sh.601857', 'sh.601989',
        
        # 科技
        'sh.600009', 'sh.600048', 'sh.600050', 'sh.600104',
        'sz.000002', 'sz.000651', 'sz.002415',
    ],
    
    # 买入阈值
    'buy_threshold': 55,      # 综合得分 >= 55 考虑买入
    'strong_buy_threshold': 70,  # 综合得分 >= 70 强烈推荐
    
    # 卖出阈值
    'sell_threshold': 30,     # 综合得分 < 30 考虑卖出
    
    # 调仓频率
    'rebalance_days': 7,      # 每 7 天调仓一次
    
    # 风险控制
    'max_position_per_stock': 0.10,  # 单只股票最大仓位 10%
    'max_total_position': 0.95,      # 最大总仓位 95%
}
```

## 不同风格的权重配置

### 价值投资风格
```python
'value_investor': {
    'value': 0.50,    # 价值因子 50% - 重视低估值
    'growth': 0.20,   # 成长因子 20%
    'momentum': 0.10, # 动量因子 10% - 不追高
    'quality': 0.20,  # 质量因子 20%
}
```

### 成长投资风格
```python
'growth_investor': {
    'value': 0.15,    # 价值因子 15% - 不太在意估值
    'growth': 0.45,   # 成长因子 45% - 重视高增长
    'momentum': 0.25, # 动量因子 25%
    'quality': 0.15,  # 质量因子 15%
}
```

### 趋势跟踪风格
```python
'trend_follower': {
    'value': 0.10,    # 价值因子 10%
    'growth': 0.20,   # 成长因子 20%
    'momentum': 0.50, # 动量因子 50% - 重视趋势
    'quality': 0.20,  # 质量因子 20%
}
```

### 质量优先风格
```python
'quality_focused': {
    'value': 0.25,    # 价值因子 25%
    'growth': 0.25,   # 成长因子 25%
    'momentum': 0.15, # 动量因子 15%
    'quality': 0.35,  # 质量因子 35% - 重视盈利质量
}
```

### 均衡配置风格
```python
'balanced': {
    'value': 0.30,    # 价值因子 30%
    'growth': 0.25,   # 成长因子 25%
    'momentum': 0.25, # 动量因子 25%
    'quality': 0.20,  # 质量因子 20%
}
```

## 使用示例

### 示例 1: 作为独立策略运行

```python
from strategy.engine import get_strategy

# 配置策略
config = {
    'strategy': 'multi_factor',
    'factor_weights': MULTI_FACTOR_CONFIG['factor_weights'],
    'top_n': 10,
    'stock_pool': MULTI_FACTOR_CONFIG['stock_pool'],
}

# 获取策略实例
strategy = get_strategy('multi_factor')
strategy.config = config
strategy.weights = config['factor_weights']
strategy.stock_pool = config['stock_pool']

# 对单只股票进行评分
code = 'sh.600519'
name = '贵州茅台'
quote = data_provider.get_quote(code)
df = data_provider.get_history(code, days=60)
pos = account.get_position(code)

signal = strategy.check(code, name, quote, df, pos, config)

if signal['signal'] == 'buy':
    print(f"买入信号：{code} {name}")
    print(f"理由：{signal['reason']}")
    print(f"强度：{signal['strength']}")
    print(f"综合得分：{signal['total_score']}")
```

### 示例 2: 批量选股

```python
from strategy.multi_factor import StockSelector, FactorCalculator

# 创建选股器
calculator = FactorCalculator()
selector = StockSelector(calculator, top_n=10)

# 执行选股
top_stocks = selector.select_stocks(
    stock_pool= MULTI_FACTOR_CONFIG['stock_pool'],
    weights= MULTI_FACTOR_CONFIG['factor_weights']
)

# 输出结果
print("TOP 10 推荐股票:")
for i, stock in enumerate(top_stocks, 1):
    print(f"{i}. {stock['code']} {stock['name']} - 得分:{stock['total_score']:.1f}")

# 执行交易
for stock in top_stocks:
    if stock['total_score'] >= MULTI_FACTOR_CONFIG['strong_buy_threshold']:
        # 买入逻辑
        buy_stock(stock['code'], weight=0.10)
    elif stock['total_score'] >= MULTI_FACTOR_CONFIG['buy_threshold']:
        # 观察或轻仓
        watch_stock(stock['code'])
```

### 示例 3: 集成到决策引擎

```python
from strategy.engine import DecisionEngine
from strategy.multi_factor import MultiFactorStrategy

# 初始化决策引擎
config = {
    'enable_ml': True,
    'enable_sentiment': True,
    'enable_multi_factor': True,
    'multi_factor_weight': 0.3,  # 多因子信号权重
}

engine = DecisionEngine(config)

# 添加多因子策略
if config.get('enable_multi_factor'):
    engine.multi_factor = MultiFactorStrategy(config)

# 综合决策
decision = engine.combine_signals(
    code='sh.600519',
    name='贵州茅台',
    quote=quote,
    df=df,
    pos=pos,
    technical_signals=[macd_signal, bollinger_signal],
    account_value=account.total_value,
    current_position_value=account.position_value
)

if decision['signal'] == 'buy':
    print(f"买入决策：{decision['reason']}")
    print(f"置信度：{decision['confidence']}")
```

### 示例 4: 定期调仓

```python
import schedule
import time

def rebalance_portfolio():
    """定期调仓"""
    print("执行调仓...")
    
    # 获取当前持仓
    current_positions = account.get_all_positions()
    
    # 运行选股
    top_stocks = selector.select_stocks(stock_pool, weights)
    top_codes = [s['code'] for s in top_stocks]
    
    # 卖出跌出 TOP 20 的股票
    all_ranking = selector.get_stock_ranking(stock_pool, weights)
    sell_candidates = []
    for pos in current_positions:
        stock_rank = all_ranking[all_ranking['code'] == pos['code']]['rank'].values[0]
        if stock_rank > 20:
            sell_candidates.append(pos['code'])
    
    for code in sell_candidates:
        sell_stock(code)
        print(f"卖出：{code} (排名跌出前 20)")
    
    # 买入新进入 TOP 10 的股票
    current_codes = [p['code'] for p in current_positions]
    for stock in top_stocks:
        if stock['code'] not in current_codes and stock['total_score'] >= 55:
            buy_stock(stock['code'], weight=0.10)
            print(f"买入：{stock['code']} (得分:{stock['total_score']:.1f})")
    
    print("调仓完成")

# 每周一上午 9:30 调仓
schedule.every().monday.at("09:30").do(rebalance_portfolio)

# 或者每 7 天调仓
schedule.every(7).days.do(rebalance_portfolio)

# 运行调度器
while True:
    schedule.run_pending()
    time.sleep(60)
```

## 回测配置

```python
# 在回测系统中使用多因子策略

from backtest.engine import BacktestEngine
from strategy.multi_factor import MultiFactorStrategy

# 初始化回测引擎
backtest = BacktestEngine(
    initial_capital=1000000,  # 初始资金 100 万
    commission_rate=0.0003,   # 手续费万分之三
    slippage=0.001,           # 滑点 0.1%
)

# 设置策略
strategy = MultiFactorStrategy(config={
    'factor_weights': {'value': 0.3, 'growth': 0.25, 'momentum': 0.25, 'quality': 0.2},
    'top_n': 10,
    'stock_pool': stock_pool,
})

# 运行回测
results = backtest.run(
    strategy=strategy,
    start_date='2023-01-01',
    end_date='2024-12-31',
    rebalance_frequency='weekly',  # 每周调仓
)

# 输出回测结果
print(f"总收益率：{results['total_return']:.2%}")
print(f"年化收益：{results['annual_return']:.2%}")
print(f"最大回撤：{results['max_drawdown']:.2%}")
print(f"夏普比率：{results['sharpe_ratio']:.2f}")
```

## 注意事项

1. **数据质量**: 确保基本面数据准确及时更新
2. **股票池选择**: 建议覆盖主要行业和市值区间
3. **权重调整**: 根据市场环境动态调整因子权重
4. **风险控制**: 设置单只股票和总仓位上限
5. **交易成本**: 考虑调仓频率和交易成本
6. **回测验证**: 实盘前充分回测验证策略有效性
