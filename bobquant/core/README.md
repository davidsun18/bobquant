# BobQuant 核心模块

核心交易引擎、账户管理、订单执行器。

---

## 📁 模块结构

```
core/
├── __init__.py          # 模块导出
├── account.py           # 账户管理
├── executor.py          # 订单执行器
├── fundamental_filter.py # 基本面过滤器
├── market_risk.py       # 市场风险
├── risk_filters.py      # 风控过滤器
├── trade_id.py          # 交易 ID 生成
└── trading_rules.py     # 交易规则
```

---

## 🚀 快速开始

### 1. 创建交易引擎

```python
from bobquant.core import TradingEngine

engine = TradingEngine(
    mode="simulation",  # "live" | "simulation" | "backtest"
    config_path="config/settings.json5"
)

engine.start()
```

### 2. 管理账户

```python
from bobquant.core import Account

account = Account(
    account_id="account_001",
    initial_capital=1000000
)

# 更新账户
account.update({
    "total_assets": 1050000,
    "available_cash": 500000,
    "market_value": 550000
})

print(f"总资产：{account.total_assets}")
print(f"可用资金：{account.available_cash}")
```

### 3. 执行订单

```python
from bobquant.core import OrderExecutor

executor = OrderExecutor(mode="simulation")

# 下单
order = executor.place_order(
    symbol="600519",
    side="buy",
    quantity=100,
    price=1800.0
)

# 撤单
executor.cancel_order(order.order_id)

# 查询订单
order = executor.get_order(order.order_id)
```

---

## 📖 API 参考

### TradingEngine

主交易引擎类。

```python
class TradingEngine:
    def __init__(self, mode="simulation", config_path="config/settings.json5")
    def start() -> bool
    def stop() -> bool
    def pause() -> bool
    def resume() -> bool
    def get_status() -> dict
    def get_account(account_id: str) -> Account
    def get_position(symbol: str) -> Position
    def get_positions() -> List[Position]
```

### Account

账户管理类。

```python
class Account:
    account_id: str
    initial_capital: float
    current_capital: float
    available_cash: float
    frozen_cash: float
    market_value: float
    total_assets: float
    profit: float
    profit_rate: float
    
    def update(data: dict) -> None
    def get_available(symbol: str) -> float
    def can_buy(symbol: str, qty: int, price: float) -> bool
    def can_sell(symbol: str, qty: int) -> bool
```

### OrderExecutor

订单执行器类。

```python
class OrderExecutor:
    def __init__(self, mode="simulation")
    
    def place_order(
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_type: str = "limit"
    ) -> Order
    
    def cancel_order(order_id: str) -> bool
    def get_order(order_id: str) -> Order
    def get_orders(symbol: str = None, status: str = None) -> List[Order]
```

### Position

持仓管理类。

```python
class Position:
    symbol: str
    volume: int
    available_volume: int
    frozen_volume: int
    cost_price: float
    current_price: float
    market_value: float
    profit: float
    profit_rate: float
    
    def update_price(price: float) -> None
    def add_volume(volume: int, price: float) -> None
    def reduce_volume(volume: int, price: float) -> float  # 返回盈亏
```

### Order

订单管理类。

```python
class Order:
    order_id: str
    symbol: str
    side: str  # "buy" | "sell"
    status: str  # "pending" | "filled" | "cancelled" | "rejected"
    order_type: str  # "limit" | "market"
    price: float
    quantity: int
    filled_quantity: int
    filled_amount: float
    create_time: datetime
    update_time: datetime
```

---

## 💡 使用示例

### 示例 1: 完整交易流程

```python
from bobquant.core import TradingEngine, Account, OrderExecutor

# 创建引擎
engine = TradingEngine(mode="simulation")
engine.start()

# 获取账户
account = engine.get_account("account_001")
print(f"初始资金：{account.initial_capital}")

# 执行器
executor = engine.executor

# 买入
order = executor.place_order(
    symbol="600519",
    side="buy",
    quantity=100,
    price=1800.0
)
print(f"订单 ID: {order.order_id}")

# 等待成交
import time
time.sleep(1)

# 查询订单
order = executor.get_order(order.order_id)
print(f"状态：{order.status}")
print(f"成交：{order.filled_quantity}/{order.quantity}")

# 查询持仓
position = engine.get_position("600519")
if position:
    print(f"持仓：{position.volume}股")
    print(f"成本：{position.cost_price}")
    print(f"盈亏：{position.profit}")

# 卖出
if position and position.volume > 0:
    sell_order = executor.place_order(
        symbol="600519",
        side="sell",
        quantity=position.volume,
        price=position.current_price
    )

engine.stop()
```

### 示例 2: 批量下单

```python
from bobquant.core import OrderExecutor

executor = OrderExecutor(mode="simulation")

# 批量买入
orders = []
for symbol in ["600519", "000858", "002415"]:
    order = executor.place_order(
        symbol=symbol,
        side="buy",
        quantity=100,
        price=get_current_price(symbol)
    )
    orders.append(order)

# 等待所有订单
for order in orders:
    print(f"{order.symbol}: {order.status}")
```

### 示例 3: 风控检查

```python
from bobquant.core import RiskFilters

risk_filters = RiskFilters()

# 检查是否可以下单
can_trade = risk_filters.check(
    symbol="600519",
    quantity=1000,
    price=1800.0,
    side="buy",
    account=account
)

if can_trade:
    executor.place_order(...)
else:
    print("风控检查失败")
    print(risk_filters.get_error_message())
```

---

## 🔧 配置说明

### 账户配置

```json5
{
  "account": {
    "initial_capital": 1000000,  // 初始资金
    "commission_rate": 0.0005,   // 手续费率
    "stamp_duty": 0.001,         // 印花税 (卖出收取)
    "transfer_fee": 0.00002      // 过户费
  }
}
```

### 风控配置

```json5
{
  "risk": {
    "max_position_pct": 0.10,     // 单票最大仓位 10%
    "max_total_position": 0.80,   // 总仓位上限 80%
    "max_positions": 10,          // 最多持有股票数
    "max_drawdown": 0.10,         // 最大回撤 10%
    "daily_loss_limit": 0.03,     // 单日亏损限制 3%
    "var_limit": 0.05             // VaR 限制 5%
  }
}
```

### 执行配置

```json5
{
  "execution": {
    "default_order_type": "limit",  // 默认订单类型
    "price_slippage": 0.001,        // 价格滑点 0.1%
    "timeout_seconds": 60,          // 订单超时 60 秒
    "retry_times": 3                // 重试次数
  }
}
```

---

## 📊 交易规则

### A 股交易规则

- **交易时间**: 9:30-11:30, 13:00-15:00
- **T+1**: 当日买入，次日可卖
- **涨跌幅**: 主板±10%, 科创板/创业板±20%
- **最小单位**: 100 股 (1 手)
- **手续费**: 万分之五 (最低 5 元)
- **印花税**: 千分之一 (卖出收取)

### 交易时段

```python
from bobquant.core.trading_rules import is_trading_time, get_next_trading_time

# 检查是否在交易时间
if is_trading_time():
    print("交易时间")
else:
    print(f"下次交易时间：{get_next_trading_time()}")
```

---

## 🐛 故障排查

### 问题 1: 下单失败

```python
# 检查可用资金
print(f"可用资金：{account.available_cash}")

# 检查仓位限制
print(f"当前仓位：{account.market_value / account.total_assets:.2%}")

# 检查风控
result = risk_check(symbol, quantity, price)
print(f"风控结果：{result}")
```

### 问题 2: 订单未成交

```python
# 检查订单状态
order = executor.get_order(order_id)
print(f"状态：{order.status}")

# 检查价格
print(f"委托价：{order.price}")
print(f"市场价：{get_current_price(symbol)}")

# 撤单重下
if order.status == "pending":
    executor.cancel_order(order_id)
    executor.place_order(symbol, side, quantity, new_price)
```

---

## 📚 相关文档

- [策略模块](../strategy/README.md)
- [风控模块](../risk_management/README.md)
- [工具模块](../tools/README.md)

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
