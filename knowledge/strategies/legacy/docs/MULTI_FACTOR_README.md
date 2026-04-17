# 多因子选股策略使用指南

## 📋 概述

BobQuant 多因子选股策略是一个综合性的量化选股模型，通过价值、成长、动量、质量四大因子对股票进行全面评估和打分，筛选出最具投资价值的股票。

## 🎯 核心功能

### 1. 四大因子体系

#### 价值因子 (Value Factor) - 权重 30%
评估股票的估值水平，寻找低估股票
- **PE (市盈率)**: 衡量股票价格相对每股收益的水平
- **PB (市净率)**: 衡量股票价格相对每股净资产的水平
- **ROE (净资产收益率)**: 衡量公司盈利能力

**计算公式**:
```
PE 得分 = (100 - PE) × 100/90, PE 有效范围 [10, 100]
PB 得分 = (10 - PB) × 100/9, PB 有效范围 [1, 10]
ROE 得分 = ROE × 5, ROE 有效范围 [0, 20]

价值得分 = PE 得分×0.4 + PB 得分×0.3 + ROE 得分×0.3
```

#### 成长因子 (Growth Factor) - 权重 25%
评估公司的成长潜力
- **营收增长率**: 衡量公司业务扩张速度
- **利润增长率**: 衡量公司盈利增长速度

**计算公式**:
```
营收增长得分 = 营收增长率 × 2, 有效范围 [0, 50%]
利润增长得分 = 利润增长率 × 2, 有效范围 [0, 50%]

成长得分 = 营收得分×0.4 + 利润得分×0.6
```

#### 动量因子 (Momentum Factor) - 权重 25%
评估股票的价格趋势
- **20 日动量**: 短期价格趋势
- **60 日动量**: 中期价格趋势

**计算公式**:
```
20 日动量 = (当前收盘价 - 20 日前收盘价) / 20 日前收盘价 × 100%
60 日动量 = (当前收盘价 - 60 日前收盘价) / 60 日前收盘价 × 100%

动量得分 = (20 日动量 +50)×100/100 × 0.6 + (60 日动量 +50)×100/100 × 0.4
```

#### 质量因子 (Quality Factor) - 权重 20%
评估公司的盈利质量
- **毛利率**: 衡量产品或服务的盈利能力
- **净利率**: 衡量公司整体盈利水平

**计算公式**:
```
毛利率得分 = 毛利率 × 2, 有效范围 [0, 50%]
净利率得分 = 净利率 × 3.33, 有效范围 [0, 30%]

质量得分 = 毛利率得分×0.4 + 净利率得分×0.6
```

### 2. 综合评分系统

```
综合得分 = 价值×0.30 + 成长×0.25 + 动量×0.25 + 质量×0.20
```

**评分标准**:
- **≥ 70 分**: 强烈推荐 (Strong Buy) - 各项指标优秀
- **55-70 分**: 推荐 (Buy) - 综合表现良好
- **30-55 分**: 持有 (Hold) - 表现一般
- **< 30 分**: 卖出 (Sell) - 多项指标较差

## 📦 文件结构

```
bobquant/strategy/
├── multi_factor.py          # 多因子策略核心实现
│   ├── FactorCalculator     # 因子计算器
│   ├── StockSelector        # 选股引擎
│   └── MultiFactorStrategy  # 策略类 (继承 BaseStrategy)
│
├── engine.py                # 策略引擎 (已集成多因子策略)
│
tests/
├── test_multi_factor.py     # 测试脚本

docs/
├── multi_factor_config_example.md  # 配置示例
├── MULTI_FACTOR_README.md          # 本文档
```

## 🚀 快速开始

### 1. 基本使用

```python
from strategy.multi_factor import FactorCalculator, StockSelector

# 创建计算器
calculator = FactorCalculator()

# 创建选股器 (选取前 10 名)
selector = StockSelector(calculator, top_n=10)

# 定义股票池
stock_pool = [
    'sh.600519',  # 贵州茅台
    'sh.600036',  # 招商银行
    'sz.000001',  # 平安银行
    # ... 更多股票
]

# 执行选股
top_stocks = selector.select_stocks(stock_pool)

# 输出结果
for i, stock in enumerate(top_stocks, 1):
    print(f"{i}. {stock['code']} {stock['name']} - 得分:{stock['total_score']:.1f}")
```

### 2. 作为策略使用

```python
from strategy.engine import get_strategy

# 获取多因子策略实例
strategy = get_strategy('multi_factor')

# 配置策略
strategy.config = {
    'top_n': 10,
    'factor_weights': {
        'value': 0.30,
        'growth': 0.25,
        'momentum': 0.25,
        'quality': 0.20,
    }
}

# 检查单只股票
signal = strategy.check(code, name, quote, df, pos, config)

if signal['signal'] == 'buy':
    print(f"买入信号：{signal['reason']}")
    print(f"强度：{signal['strength']}")
    print(f"综合得分：{signal['total_score']}")
```

### 3. 运行测试

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python tests/test_multi_factor.py
```

## ⚙️ 配置选项

### 因子权重配置

```python
config = {
    'factor_weights': {
        'value': 0.30,    # 价值因子权重
        'growth': 0.25,   # 成长因子权重
        'momentum': 0.25, # 动量因子权重
        'quality': 0.20,  # 质量因子权重
    }
}
```

**注意**: 所有权重之和应等于 1.0

### 选股数量配置

```python
config = {
    'top_n': 10,  # 选取前 10 名股票
}
```

### 股票池配置

```python
config = {
    'stock_pool': [
        'sh.600000', 'sh.600036', 'sh.600519',  # 示例股票
        # ... 更多股票
    ],
}
```

### 阈值配置

```python
config = {
    'buy_threshold': 55,          # 买入阈值
    'strong_buy_threshold': 70,   # 强烈推荐阈值
    'sell_threshold': 30,         # 卖出阈值
}
```

## 📊 选股流程

```
1. 准备股票池
   ↓
2. 获取每只股票的基本面数据 (PE/PB/ROE 等)
   ↓
3. 获取历史 K 线数据 (计算动量)
   ↓
4. 计算各因子得分
   - 价值因子得分
   - 成长因子得分
   - 动量因子得分
   - 质量因子得分
   ↓
5. 计算综合得分 (加权求和)
   ↓
6. 排序并筛选前 N 名
   ↓
7. 输出选股结果
```

## 🔄 与现有策略集成

### 方式 1: 独立策略模式

在 `config/settings.py` 中设置:

```python
STRATEGY_CONFIG = {
    'name': 'multi_factor',
    'enabled': True,
    'factor_weights': {
        'value': 0.30,
        'growth': 0.25,
        'momentum': 0.25,
        'quality': 0.20,
    },
    'top_n': 10,
    'stock_pool': [...],
}
```

### 方式 2: 组合策略模式

在 `DecisionEngine` 中整合多个策略信号:

```python
from strategy.engine import DecisionEngine
from strategy.multi_factor import MultiFactorStrategy

# 初始化
engine = DecisionEngine(config)
engine.multi_factor = MultiFactorStrategy(config)

# 综合决策
decision = engine.combine_signals(
    code='sh.600519',
    name='贵州茅台',
    quote=quote,
    df=df,
    pos=pos,
    technical_signals=[macd_signal, bollinger_signal],
)

# decision 包含所有策略的综合判断
```

### 方式 3: 选股器模式

作为独立的选股工具，为其他策略提供股票池:

```python
# 每日开盘前运行选股
top_stocks = selector.select_stocks(stock_pool)
top_codes = [s['code'] for s in top_stocks]

# 将 TOP 10 作为重点观察池
for code in top_codes:
    # 使用其他策略进行详细分析
    signal = macd_strategy.check(code, ...)
    if signal['signal'] == 'buy':
        execute_buy(code)
```

## 📈 实盘应用

### 定期调仓策略

```python
import schedule
from datetime import datetime

def rebalance():
    """每周调仓"""
    print(f"[{datetime.now()}] 执行调仓...")
    
    # 获取最新排名
    ranking = selector.get_stock_ranking(stock_pool)
    
    # 获取当前持仓
    positions = account.get_positions()
    
    # 卖出逻辑：跌出前 20 名
    for pos in positions:
        stock_rank = ranking[ranking['code'] == pos['code']]['rank'].values[0]
        if stock_rank > 20:
            account.sell(pos['code'], pos['volume'])
            print(f"卖出：{pos['code']} (排名:{stock_rank})")
    
    # 买入逻辑：新进入前 10 名且得分>=55
    current_codes = [p['code'] for p in positions]
    for stock in ranking.head(10).to_dict('records'):
        if stock['code'] not in current_codes and stock['total_score'] >= 55:
            account.buy(stock['code'], weight=0.10)
            print(f"买入：{stock['code']} (得分:{stock['total_score']:.1f})")

# 每周一 9:30 调仓
schedule.every().monday.at("09:30").do(rebalance)
```

### 风险控制

```python
# 仓位控制
MAX_POSITION_PER_STOCK = 0.10  # 单只股票最大 10%
MAX_TOTAL_POSITION = 0.95      # 总仓位最大 95%
STOP_LOSS_PERCENT = 0.10       # 止损线 10%

# 分散投资
MIN_STOCKS = 5    # 最少持有 5 只股票
MAX_STOCKS = 15   # 最多持有 15 只股票

# 行业分散
MAX_SECTOR_WEIGHT = 0.30  # 单一行业最大 30%
```

## 🧪 测试与验证

### 单元测试

```bash
# 运行测试
python tests/test_multi_factor.py

# 测试输出包括:
# - 50 只股票的因子得分
# - TOP 10 选股结果
# - 因子计算公式说明
# - 集成方式示例
```

### 回测验证

建议使用历史数据进行回测，验证策略有效性:

```python
from backtest.engine import BacktestEngine

backtest = BacktestEngine(initial_capital=1000000)

results = backtest.run(
    strategy=multi_factor_strategy,
    start_date='2023-01-01',
    end_date='2024-12-31',
    rebalance_frequency='weekly',
)

print(f"年化收益：{results['annual_return']:.2%}")
print(f"最大回撤：{results['max_drawdown']:.2%}")
print(f"夏普比率：{results['sharpe_ratio']:.2f}")
```

## ⚠️ 注意事项

1. **数据质量**: 确保基本面数据准确、及时更新
2. **股票池选择**: 建议覆盖主要行业和不同市值区间
3. **权重调整**: 根据市场环境动态调整因子权重
4. **交易成本**: 考虑调仓频率和交易成本的影响
5. **风险提示**: 量化策略不保证盈利，需结合风险控制
6. **数据源依赖**: 当前使用 baostock 获取基本面数据，需确保数据源稳定

## 📚 参考资料

- Fama, E. F., & French, K. R. (1992). The Cross-Section of Expected Stock Returns
- Carhart, M. M. (1997). On Persistence in Mutual Fund Performance
- AQR Capital Management - Factor Investing Research

## 🤝 技术支持

如有问题或建议，请:
1. 查看 `docs/multi_factor_config_example.md` 获取配置示例
2. 运行 `python tests/test_multi_factor.py` 验证安装
3. 检查日志文件获取详细错误信息

---

**版本**: v1.0  
**最后更新**: 2026-04-11  
**作者**: BobQuant Team
