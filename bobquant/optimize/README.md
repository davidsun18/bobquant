# BobQuant 优化模块

Optuna 参数优化、超参数搜索。

---

## 📁 模块结构

```
optimize/
├── __init__.py              # 模块导出
├── optuna_optimizer.py      # Optuna 优化器
└── OPTUNA_INTEGRATION_SUMMARY.md # 集成文档
```

---

## 🚀 快速开始

### 1. 参数优化

```python
from bobquant.optimize import OptunaOptimizer
from bobquant.strategy import MAStrategy

optimizer = OptunaOptimizer(
    strategy_class=MAStrategy,
    start_date="2023-01-01",
    end_date="2023-12-31"
)

# 定义参数空间
param_space = {
    "ma_fast_period": (5, 20),
    "ma_slow_period": (10, 60)
}

# 运行优化
best_params, best_score = optimizer.optimize(
    param_space=param_space,
    n_trials=100,
    objective="sharpe_ratio"
)

print(f"最优参数：{best_params}")
print(f"最优夏普比率：{best_score:.2f}")
```

---

## 📖 优化目标

支持以下优化目标：

- `sharpe_ratio`: 夏普比率 (默认)
- `total_return`: 总收益
- `annual_return`: 年化收益
- `max_drawdown`: 最大回撤 (最小化)
- `sortino_ratio`: 索提诺比率
- `calmar_ratio`: 卡玛比率

---

## 💡 使用示例

### 示例 1: 优化均线策略

```python
from bobquant.optimize import OptunaOptimizer

optimizer = OptunaOptimizer(
    strategy_class=MAStrategy,
    start_date="2020-01-01",
    end_date="2022-12-31"
)

param_space = {
    "fast_period": (3, 10),
    "slow_period": (15, 30)
}

best_params, best_score = optimizer.optimize(
    param_space=param_space,
    n_trials=50,
    objective="sharpe_ratio"
)
```

### 示例 2: 优化多因子策略

```python
from bobquant.optimize import OptunaOptimizer

optimizer = OptunaOptimizer(
    strategy_class=MultiFactorStrategy,
    start_date="2020-01-01",
    end_date="2022-12-31"
)

param_space = {
    "momentum_period": (10, 30),
    "rebalance_days": (3, 10),
    "max_positions": (5, 20)
}

best_params, best_score = optimizer.optimize(
    param_space=param_space,
    n_trials=100,
    objective="total_return"
)
```

### 示例 3: 自定义目标函数

```python
from bobquant.optimize import OptunaOptimizer

def custom_objective(results):
    # 自定义目标：收益 / 回撤
    if results.max_drawdown == 0:
        return 0
    return results.total_return / abs(results.max_drawdown)

optimizer = OptunaOptimizer(
    strategy_class=MyStrategy,
    start_date="2020-01-01",
    end_date="2022-12-31"
)

best_params, best_score = optimizer.optimize(
    param_space=param_space,
    n_trials=100,
    objective=custom_objective  # 使用自定义目标
)
```

---

## 🔧 配置说明

### 优化器配置

```python
optimizer = OptunaOptimizer(
    strategy_class=MyStrategy,
    start_date="2020-01-01",
    end_date="2022-12-31",
    initial_capital=1000000,
    commission_rate=0.0005,
    direction="maximize",  # "maximize" | "minimize"
    n_trials=100,
    timeout=3600  # 1 小时超时
)
```

### 参数空间

```python
param_space = {
    # 整数范围
    "period": (5, 20),
    
    # 浮点数范围
    "threshold": (0.01, 0.10),
    
    # 分类选择
    "method": ["sma", "ema", "wma"],
    
    # 布尔值
    "use_stop_loss": [True, False]
}
```

---

## 📚 相关文档

- [Optuna 集成文档](./OPTUNA_INTEGRATION_SUMMARY.md)

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
