# BobQuant 回测模块

回测引擎、VectorBT 集成、Backtrader 集成。

---

## 📁 模块结构

```
backtest/
├── __init__.py              # 模块导出
├── vectorbt_backtest.py     # VectorBT 回测
├── backtrader_integration.py # Backtrader 集成
├── MULTIFRAME_GUIDE.md      # 多因子回测指南
└── VECTORBT_INTEGRATION.md  # VectorBT 集成文档
```

---

## 🚀 快速开始

### 1. 简单回测

```python
from bobquant.backtest import BacktestEngine
from bobquant.strategy import MAStrategy

engine = BacktestEngine(
    strategy=MAStrategy(),
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=1000000
)

results = engine.run()
print(results.summary())
```

### 2. VectorBT 回测

```python
from bobquant.backtest import VectorBTBacktest

backtest = VectorBTBacktest(
    symbols=["600519.SH"],
    start="2023-01-01",
    end="2023-12-31"
)

portfolio = backtest.run(
    entry_signals=entry_signals,
    exit_signals=exit_signals
)

print(f"夏普比率：{portfolio.sharpe_ratio()}")
```

---

## 📖 回测引擎

### BacktestEngine

```python
class BacktestEngine:
    def __init__(
        self,
        strategy: Strategy,
        start_date: str,
        end_date: str,
        initial_capital: float = 1000000,
        commission_rate: float = 0.0005,
        slippage: float = 0.001
    )
    
    def run() -> BacktestResults
```

### BacktestResults

```python
class BacktestResults:
    total_return: float      # 总收益
    annual_return: float     # 年化收益
    sharpe_ratio: float      # 夏普比率
    max_drawdown: float      # 最大回撤
    total_trades: int        # 交易次数
    win_rate: float          # 胜率
    
    def summary() -> dict
    def generate_report(output_path: str)
```

---

## 💡 使用示例

### 示例 1: 参数优化回测

```python
from bobquant.backtest import BacktestEngine
from bobquant.strategy import MAStrategy

best_sharpe = 0
best_params = {}

for fast in [5, 10, 15]:
    for slow in [20, 30, 40]:
        engine = BacktestEngine(
            strategy=MAStrategy(fast_period=fast, slow_period=slow),
            start_date="2023-01-01",
            end_date="2023-12-31"
        )
        
        results = engine.run()
        
        if results.sharpe_ratio > best_sharpe:
            best_sharpe = results.sharpe_ratio
            best_params = {"fast": fast, "slow": slow}

print(f"最优参数：{best_params}")
print(f"最优夏普：{best_sharpe:.2f}")
```

### 示例 2: 多股票回测

```python
from bobquant.backtest import PortfolioBacktest

backtest = PortfolioBacktest(
    strategy=MyStrategy(),
    universe=["600519.SH", "000858.SZ", "002415.SZ"],
    start_date="2023-01-01",
    end_date="2023-12-31"
)

results = backtest.run()
print(results.summary())
```

---

## 📚 相关文档

- [多因子回测指南](./MULTIFRAME_GUIDE.md)
- [VectorBT 集成](./VECTORBT_INTEGRATION.md)

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
