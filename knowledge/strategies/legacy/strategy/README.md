# BobQuant 策略模块

策略引擎、多因子策略、网格 T、高频策略、再平衡策略。

---

## 📁 模块结构

```
strategy/
├── __init__.py              # 模块导出
├── engine.py                # 策略引擎
├── multi_factor.py          # 多因子策略
├── grid_t_v2_5_patch.py     # 网格 T 策略
├── high_frequency.py        # 高频策略
├── rebalance.py             # 再平衡策略
├── ml_strategy.py           # ML 策略
└── sentiment_controller.py  # 情绪控制器
```

---

## 🚀 快速开始

### 1. 创建策略

```python
from bobquant.strategy import Strategy
from bobquant.indicator import MA

class MyStrategy(Strategy):
    def on_init(self):
        self.ma = MA(20)
    
    def on_bar(self, bar):
        self.ma.update(bar.close)
        
        if bar.close > self.ma.value:
            self.buy(bar.symbol, 100)
        else:
            self.sell(bar.symbol, self.get_position(bar.symbol))
```

### 2. 运行策略

```python
from bobquant.core import TradingEngine

engine = TradingEngine(
    strategy=MyStrategy(),
    mode="simulation"
)

engine.start()
```

### 3. 回测策略

```python
from bobquant.backtest import BacktestEngine

engine = BacktestEngine(
    strategy=MyStrategy(),
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=1000000
)

results = engine.run()
print(results.summary())
```

---

## 📖 策略类型

### 1. 基础策略 (Strategy)

所有策略的基类。

```python
from bobquant.strategy import Strategy

class MyStrategy(Strategy):
    """自定义策略"""
    
    name = "my_strategy"
    version = "1.0"
    
    def __init__(self, config=None):
        super().__init__(config)
        # 初始化参数
    
    def on_init(self):
        """策略初始化"""
        pass
    
    def on_start(self):
        """策略启动"""
        pass
    
    def on_stop(self):
        """策略停止"""
        pass
    
    def on_bar(self, bar):
        """K 线回调"""
        pass
    
    def on_tick(self, tick):
        """Tick 回调"""
        pass
    
    def on_order(self, order):
        """订单回调"""
        pass
    
    def on_trade(self, trade):
        """成交回调"""
        pass
```

### 2. 多因子策略 (MultiFactorStrategy)

基于多因子选股的策略。

```python
from bobquant.strategy import MultiFactorStrategy

class MFStrategy(MultiFactorStrategy):
    def __init__(self):
        super().__init__(
            factors=["momentum", "value", "quality"],
            weights=[0.4, 0.3, 0.3],
            rebalance_days=5
        )
    
    def calculate_factor_score(self, symbol: str) -> float:
        """计算股票得分"""
        momentum = self.get_momentum(symbol)
        value = self.get_value(symbol)
        quality = self.get_quality(symbol)
        
        return (
            momentum * 0.4 +
            value * 0.3 +
            quality * 0.3
        )
```

### 3. 网格 T 策略 (GridTStrategy)

网格 T+0 交易策略。

```python
from bobquant.strategy import GridTStrategy

class MyGridStrategy(GridTStrategy):
    def __init__(self):
        super().__init__(
            grid_size=0.02,      # 2% 网格
            max_grid=10,         # 10 层网格
            base_quantity=100    # 每格 100 股
        )
```

### 4. 高频策略 (HighFrequencyStrategy)

高频交易策略。

```python
from bobquant.strategy import HighFrequencyStrategy

class HFStrategy(HighFrequencyStrategy):
    def __init__(self):
        super().__init__(
            tick_interval=0.1,   # 100ms 间隔
            order_threshold=0.005  # 0.5% 阈值
        )
    
    def on_tick(self, tick):
        """Tick 级别策略逻辑"""
        pass
```

### 5. 再平衡策略 (RebalanceStrategy)

定期调仓再平衡策略。

```python
from bobquant.strategy import RebalanceStrategy

class RebalanceStrategy(RebalanceStrategy):
    def __init__(self):
        super().__init__(
            target_weights={"600519": 0.3, "000858": 0.3, "002415": 0.4},
            rebalance_days=10,
            threshold=0.05  # 偏离 5% 触发再平衡
        )
```

---

## 💡 使用示例

### 示例 1: 均线策略

```python
from bobquant.strategy import Strategy
from bobquant.indicator import MA

class MAStrategy(Strategy):
    def on_init(self):
        self.ma5 = MA(5)
        self.ma20 = MA(20)
    
    def on_bar(self, bar):
        self.ma5.update(bar.close)
        self.ma20.update(bar.close)
        
        # 金叉买入
        if self.ma5.value > self.ma20.value and not self.get_position(bar.symbol):
            self.buy(bar.symbol, 100)
        
        # 死叉卖出
        elif self.ma5.value < self.ma20.value and self.get_position(bar.symbol):
            self.sell(bar.symbol, self.get_position(bar.symbol))
```

### 示例 2: RSI 策略

```python
from bobquant.strategy import Strategy
from bobquant.indicator import RSI

class RSIStrategy(Strategy):
    def on_init(self):
        self.rsi = RSI(14)
    
    def on_bar(self, bar):
        self.rsi.update(bar.close)
        
        # 超卖买入
        if self.rsi.value < 30:
            self.buy(bar.symbol, 100)
        
        # 超买卖出
        elif self.rsi.value > 70:
            self.sell(bar.symbol, self.get_position(bar.symbol))
```

### 示例 3: 多因子策略

```python
from bobquant.strategy import MultiFactorStrategy

class MyMFStrategy(MultiFactorStrategy):
    def calculate_factor_score(self, symbol: str) -> float:
        # 动量因子
        momentum = self.get_momentum(symbol, period=20)
        
        # 价值因子
        pe = self.get_pe_ratio(symbol)
        value = 1 / pe if pe > 0 else 0
        
        # 质量因子
        roe = self.get_roe(symbol)
        
        # 综合得分
        score = momentum * 0.4 + value * 0.3 + roe * 0.3
        
        return score
```

### 示例 4: 网格策略

```python
from bobquant.strategy import GridTStrategy

class MyGridStrategy(GridTStrategy):
    def on_bar(self, bar):
        # 自动执行网格交易
        self.execute_grid(bar.symbol, bar.close)
```

---

## 🔧 策略配置

### 策略参数

```json5
{
  "strategy": {
    "name": "multi_factor",
    "version": "1.0",
    
    // 多因子参数
    "factors": ["momentum", "value", "quality"],
    "weights": [0.4, 0.3, 0.3],
    "rebalance_days": 5,
    
    // 股票池
    "universe": ["600519.SH", "000858.SZ", "002415.SZ"],
    "universe_size": 30,
    
    // 仓位管理
    "max_position_pct": 0.10,
    "max_total_position": 0.80
  }
}
```

### 因子配置

```json5
{
  "factors": {
    "momentum": {
      "period": 20,
      "weight": 0.4
    },
    "value": {
      "metrics": ["pe", "pb", "ps"],
      "weight": 0.3
    },
    "quality": {
      "metrics": ["roe", "roa", "gross_margin"],
      "weight": 0.3
    }
  }
}
```

---

## 📊 策略评估

### 绩效指标

```python
results = engine.run()

print(f"总收益：{results.total_return:.2%}")
print(f"年化收益：{results.annual_return:.2%}")
print(f"夏普比率：{results.sharpe_ratio:.2f}")
print(f"最大回撤：{results.max_drawdown:.2%}")
print(f"交易次数：{results.total_trades}")
print(f"胜率：{results.win_rate:.2%}")
print(f"盈亏比：{results.profit_loss_ratio:.2f}")
```

### 风险分析

```python
# 风险指标
print(f"VaR(95%): {results.var_95:.2%}")
print(f"波动率：{results.volatility:.2%}")
print(f"Beta: {results.beta:.2f}")
print(f"Alpha: {results.alpha:.2%}")

# 月度收益
for month, return_pct in results.monthly_returns.items():
    print(f"{month}: {return_pct:.2%}")
```

---

## 🐛 故障排查

### 问题 1: 策略不产生信号

```python
# 添加调试日志
def on_bar(self, bar):
    self.logger.debug(f"on_bar: {bar.symbol} {bar.close}")
    self.logger.debug(f"指标值：{self.indicator.value}")
    self.logger.debug(f"持仓：{self.get_position(bar.symbol)}")
```

### 问题 2: 回测结果异常

```python
# 检查手续费
engine = BacktestEngine(
    commission_rate=0.0005,
    slippage=0.001
)

# 检查未来函数
# 确保不使用未来数据
```

---

## 📚 相关文档

- [核心模块](../core/README.md)
- [指标模块](../indicator/README.md)
- [回测模块](../backtest/README.md)
- [示例集合](../docs/EXAMPLES.md)

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
