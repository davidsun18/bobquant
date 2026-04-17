# BobQuant API 参考手册

完整的 API 文档，涵盖所有核心模块、工具和接口。

---

## 📑 目录

1. [核心 API](#核心-api)
2. [策略 API](#策略-api)
3. [数据 API](#数据-api)
4. [工具 API](#工具-api)
5. [配置 API](#配置-api)
6. [回测 API](#回测-api)
7. [风控 API](#风控-api)
8. [Web API](#web-api)

---

## 核心 API

### TradingEngine

主交易引擎，协调所有模块。

```python
from bobquant.core import TradingEngine

engine = TradingEngine(
    mode: str = "simulation",  # "live" | "simulation" | "backtest"
    config_path: str = "config/settings.json5",
    log_level: str = "INFO"
)
```

#### 方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `start()` | - | `bool` | 启动引擎 |
| `stop()` | - | `bool` | 停止引擎 |
| `pause()` | - | `bool` | 暂停交易 |
| `resume()` | - | `bool` | 恢复交易 |
| `get_status()` | - | `dict` | 获取状态 |
| `get_account()` | account_id | `Account` | 获取账户 |
| `get_position()` | symbol | `Position` | 获取持仓 |
| `get_positions()` | - | `List[Position]` | 获取所有持仓 |

#### 示例

```python
engine = TradingEngine(mode="simulation")
engine.start()

# 获取账户信息
account = engine.get_account("account_001")
print(f"总资产：{account.total_assets}")

# 获取持仓
positions = engine.get_positions()
for pos in positions:
    print(f"{pos.symbol}: {pos.volume}股")

engine.stop()
```

---

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
```

#### 方法

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `update()` | data: dict | `None` | 更新账户数据 |
| `get_available()` | symbol: str | `float` | 获取可用资金 |
| `can_buy()` | symbol, qty, price | `bool` | 检查是否可买入 |
| `can_sell()` | symbol, qty | `bool` | 检查是否可卖出 |

---

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
    buy_amount: float
    sell_amount: float
```

---

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

## 策略 API

### Strategy

策略基类，所有策略必须继承此类。

```python
from bobquant.strategy import Strategy

class MyStrategy(Strategy):
    name = "my_strategy"
    version = "1.0"
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        # 初始化
    
    def on_init(self):
        """策略初始化"""
        pass
    
    def on_start(self):
        """策略启动"""
        pass
    
    def on_stop(self):
        """策略停止"""
        pass
    
    def on_bar(self, bar: BarData):
        """K 线数据回调"""
        pass
    
    def on_tick(self, tick: TickData):
        """Tick 数据回调"""
        pass
    
    def on_order(self, order: OrderData):
        """订单状态回调"""
        pass
    
    def on_trade(self, trade: TradeData):
        """成交回调"""
        pass
```

#### 策略方法

| 方法 | 调用时机 | 说明 |
|------|----------|------|
| `on_init()` | 策略初始化时 | 加载数据、设置参数 |
| `on_start()` | 策略启动时 | 订阅行情、初始化状态 |
| `on_stop()` | 策略停止时 | 清理资源、保存状态 |
| `on_bar()` | 收到 K 线时 | 主要策略逻辑 |
| `on_tick()` | 收到 Tick 时 | 高频策略使用 |
| `on_order()` | 订单状态变化 | 订单管理 |
| `on_trade()` | 成交时 | 成交记录 |

#### 交易动作

| 方法 | 参数 | 说明 |
|------|------|------|
| `buy(symbol, quantity, price?)` | 代码、数量、价格 (可选) | 买入 |
| `sell(symbol, quantity, price?)` | 代码、数量、价格 (可选) | 卖出 |
| `cancel_order(order_id)` | 订单 ID | 撤单 |
| `cancel_all(symbol?)` | 代码 (可选) | 撤销所有订单 |

#### 示例

```python
from bobquant.strategy import Strategy
from bobquant.indicator import MA

class MAStrategy(Strategy):
    def on_init(self):
        self.ma5 = MA(5)
        self.ma10 = MA(10)
    
    def on_bar(self, bar):
        self.ma5.update(bar.close)
        self.ma10.update(bar.close)
        
        if self.ma5.value > self.ma10.value and not self.position:
            self.buy(bar.symbol, 100)
        elif self.ma5.value < self.ma10.value and self.position:
            self.sell(bar.symbol, self.position.volume)
```

---

### MultiFactorStrategy

多因子策略。

```python
from bobquant.strategy import MultiFactorStrategy

class MyMFStrategy(MultiFactorStrategy):
    def __init__(self):
        super().__init__(
            factors=["momentum", "value", "quality"],
            weights=[0.4, 0.3, 0.3],
            rebalance_days=5
        )
    
    def calculate_scores(self, universe: List[str]) -> Dict[str, float]:
        """计算股票评分"""
        scores = {}
        for symbol in universe:
            score = self.calculate_factor_score(symbol)
            scores[symbol] = score
        return scores
```

---

### GridTStrategy

网格 T+0 策略。

```python
from bobquant.strategy import GridTStrategy

class MyGridStrategy(GridTStrategy):
    def __init__(self):
        super().__init__(
            grid_size=0.02,  # 网格大小 2%
            max_grid=10,     # 最大网格数
            base_quantity=100 # 基础数量
        )
```

---

## 数据 API

### 数据源接口

```python
from bobquant.data import DataProvider

class MyDataProvider(DataProvider):
    def get_bar_data(self, symbol: str, interval: str, 
                     start: str, end: str) -> pd.DataFrame:
        pass
    
    def get_tick_data(self, symbol: str, date: str) -> pd.DataFrame:
        pass
    
    def get_realtime_data(self, symbols: List[str]) -> Dict[str, TickData]:
        pass
```

### 内置数据源

#### TushareProvider

```python
from bobquant.data import TushareProvider

provider = TushareProvider(token="your_token")

# 获取日线数据
df = provider.get_bar_data(
    symbol="600519.SH",
    interval="1d",
    start="2023-01-01",
    end="2023-12-31"
)

# 获取分钟数据
df = provider.get_bar_data(
    symbol="600519.SH",
    interval="1m",
    start="2023-01-01 09:30:00",
    end="2023-01-01 15:00:00"
)

# 获取实时行情
tick = provider.get_realtime_data(["600519.SH"])
```

#### AkShareProvider

```python
from bobquant.data import AkShareProvider

provider = AkShareProvider()
df = provider.get_bar_data("600519", "1d", "2023-01-01", "2023-12-31")
```

#### YfinanceProvider

```python
from bobquant.data import YfinanceProvider

provider = YfinanceProvider()
df = provider.get_bar_data("AAPL", "1d", "2023-01-01", "2023-12-31")
```

---

### 数据获取函数

```python
from bobquant.data import (
    get_market_data,
    get_realtime_data,
    get_history_data,
    get_financial_data
)

# 获取行情数据
df = get_market_data(
    symbol="600519.SH",
    interval="1d",
    start="2023-01-01",
    end="2023-12-31"
)

# 获取实时行情
tick = get_realtime_data("600519.SH")

# 获取历史数据
df = get_history_data(
    symbol="600519.SH",
    period="5y",
    interval="1d"
)

# 获取财务数据
financials = get_financial_data("600519.SH")
```

---

## 工具 API

### 工具系统

```python
from bobquant.tools import Tool, ToolContext, ToolResult, get_registry

# 获取注册表
registry = get_registry()

# 获取工具
tool = registry.get("place_order")

# 调用工具
context = ToolContext(options={"mode": "simulation"})
result = await tool.call(
    args={"symbol": "600519", "side": "buy", "quantity": 100},
    context=context
)
```

---

### 交易工具

#### PlaceOrderTool

```python
# 下单
from bobquant.tools.trading import place_order

result = await place_order(
    symbol="600519",
    side="buy",
    quantity=100,
    price=1800.0,
    order_type="limit"
)
# 返回：{"order_id": "xxx", "status": "submitted"}
```

#### CancelOrderTool

```python
# 撤单
from bobquant.tools.trading import cancel_order

result = await cancel_order(order_id="123456")
# 返回：{"status": "cancelled"}
```

#### GetPositionTool

```python
# 查询持仓
from bobquant.tools.trading import get_position

position = await get_position(symbol="600519")
# 返回：{"volume": 100, "cost_price": 1800.0, ...}
```

#### GetOrderTool

```python
# 查询订单
from bobquant.tools.trading import get_order

order = await get_order(order_id="123456")
```

#### GetOrdersTool

```python
# 查询订单列表
from bobquant.tools.trading import get_orders

orders = await get_orders(
    symbol="600519",
    status="pending"
)
```

---

### 数据工具

#### GetMarketDataTool

```python
from bobquant.tools.data import get_market_data

df = await get_market_data(
    symbol="600519",
    interval="1d",
    start="2023-01-01",
    end="2023-12-31"
)
```

#### GetRealtimeDataTool

```python
from bobquant.tools.data import get_realtime_data

tick = await get_realtime_data(symbols=["600519", "000858"])
```

#### GetHistoryDataTool

```python
from bobquant.tools.data import get_history_data

df = await get_history_data(
    symbol="600519",
    period="5y",
    interval="1d"
)
```

#### GetFinancialDataTool

```python
from bobquant.tools.data import get_financial_data

financials = await get_financial_data(symbol="600519")
```

---

### 风控工具

#### RiskCheckTool

```python
from bobquant.tools.risk import risk_check

result = await risk_check(
    symbol="600519",
    quantity=1000,
    price=1800.0,
    side="buy"
)
# 返回：{"passed": true, "message": "通过"}
```

#### SetStopLossTool

```python
from bobquant.tools.risk import set_stop_loss

result = await set_stop_loss(
    symbol="600519",
    stop_loss_price=1700.0,
    stop_profit_price=2000.0
)
```

#### GetRiskMetricsTool

```python
from bobquant.tools.risk import get_risk_metrics

metrics = await get_risk_metrics(account_id="account_001")
# 返回：{"var": 0.05, "max_drawdown": 0.1, ...}
```

---

## 配置 API

### ConfigLoader

```python
from bobquant.config import ConfigLoader

# 加载配置
loader = ConfigLoader("config/settings.json5")
config = loader.load(
    strategy="conservative",
    channel="sim_channel",
    account="account_001",
    group="group_a"
)

# 解析 SecretRef
config = config.resolve_secrets()

# 访问配置
print(config.account.initial_capital)
print(config.position.max_position_pct)
```

---

### ConfigValidator

```python
from bobquant.config import ConfigValidator

validator = ConfigValidator(config)

# 验证 Schema
if not validator.validate_schema():
    print(validator.get_errors())

# 验证业务规则
if not validator.validate_business_rules():
    print(validator.get_error_report())

# 验证所有
if not validator.validate_all():
    print(validator.get_error_report())
```

---

### ConfigMigrator

```python
from bobquant.config import ConfigMigrator
from pathlib import Path

migrator = ConfigMigrator()

# 检测版本
version = migrator.detect_version(config)

# 检查是否需要迁移
if migrator.needs_migration(config):
    # 执行迁移
    new_config, records = migrator.migrate(
        config=config,
        backup=True
    )
    
    # 或迁移文件
    new_path, records = migrator.migrate_file(
        source_path=Path("config/settings_v2.2.json5"),
        target_path=Path("config/settings.json5"),
        backup=True
    )
```

---

### BobQuantConfig

```python
from bobquant.config import BobQuantConfig

# 配置结构
class BobQuantConfig:
    system: SystemConfig
    account: AccountConfig
    position: PositionConfig
    risk: RiskConfig
    strategy: StrategyConfig
    data: DataConfig
    notify: NotifyConfig
    
    # 方法
    def resolve() -> BobQuantConfig  # 解析 5 层继承
    def resolve_secrets() -> BobQuantConfig  # 解析 SecretRef
```

---

## 回测 API

### BacktestEngine

```python
from bobquant.backtest import BacktestEngine
from bobquant.strategy import MyStrategy

engine = BacktestEngine(
    strategy=MyStrategy(),
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=1000000,
    commission_rate=0.0005,
    slippage=0.001
)

results = engine.run()
```

#### 结果分析

```python
# 获取回测结果
print(results.summary())
print(results.annual_return)
print(results.sharpe_ratio)
print(results.max_drawdown)
print(results.total_trades)

# 获取交易记录
trades = results.get_trades()

# 获取资金曲线
equity_curve = results.get_equity_curve()

# 生成报告
results.generate_report(output_path="report.html")
```

---

### VectorBT 回测

```python
from bobquant.backtest import VectorBTBacktest

backtest = VectorBTBacktest(
    symbols=["600519.SH", "000858.SZ"],
    start="2023-01-01",
    end="2023-12-31"
)

# 运行回测
portfolio = backtest.run(
    entry_signals=entry_signals,
    exit_signals=exit_signals,
    init_cash=1000000,
    fees=0.0005
)

# 分析结果
print(portfolio.sharpe_ratio())
print(portfolio.max_drawdown())
```

---

## 风控 API

### RiskManager

```python
from bobquant.risk_management import RiskManager

risk_mgr = RiskManager(config=risk_config)

# 仓位检查
can_buy = risk_mgr.check_position_limit(
    symbol="600519",
    quantity=1000,
    price=1800.0
)

# 止损检查
stop_loss_triggered = risk_mgr.check_stop_loss(
    symbol="600519",
    current_price=1700.0
)

# 风险指标
metrics = risk_mgr.get_risk_metrics()
print(f"VaR: {metrics.var_95}")
print(f"最大回撤：{metrics.max_drawdown}")
```

---

### StopLossManager

```python
from bobquant.risk_management import StopLossManager

sl_mgr = StopLossManager()

# 设置止损
sl_mgr.set_stop_loss(
    symbol="600519",
    stop_loss_price=1700.0,
    stop_profit_price=2000.0,
    trailing_stop=True,
    trailing_percent=0.05
)

# 获取止损设置
sl = sl_mgr.get_stop_loss("600519")

# 检查是否触发
triggered = sl_mgr.check_stop_loss(
    symbol="600519",
    current_price=1690.0
)
```

---

## Web API

### Streamlit 页面

```python
# 在 streamlit_app.py 中
import streamlit as st

st.set_page_config(
    page_title="BobQuant",
    page_icon="📊",
    layout="wide"
)

# 侧边栏导航
page = st.sidebar.selectbox(
    "选择页面",
    ["账户概览", "持仓分析", "交易记录", "绩效分析", "设置"]
)

# 页面内容
if page == "账户概览":
    show_overview()
elif page == "持仓分析":
    show_positions()
```

---

### 数据接口

```python
# 获取账户数据
def get_account_data():
    with open("logs/account.json") as f:
        return json.load(f)

# 获取持仓数据
def get_position_data():
    with open("logs/positions.json") as f:
        return json.load(f)

# 获取交易记录
def get_trade_history():
    with open("logs/trades.json") as f:
        return json.load(f)
```

---

## 指标 API

### TA-Lib 指标

```python
from bobquant.indicator import TALib

talib = TALib()

# 移动平均
ma5 = talib.SMA(close, timeperiod=5)
ma10 = talib.SMA(close, timeperiod=10)

# MACD
macd, signal, hist = talib.MACD(
    close,
    fastperiod=12,
    slowperiod=26,
    signalperiod=9
)

# RSI
rsi = talib.RSI(close, timeperiod=14)

# 布林带
upper, middle, lower = talib.BBANDS(
    close,
    timeperiod=20,
    nbdevup=2,
    nbdevdn=2
)
```

---

### 自定义指标

```python
from bobquant.indicator import Indicator

class MyIndicator(Indicator):
    def __init__(self, period=14):
        self.period = period
        self.values = []
    
    def update(self, value: float) -> float:
        self.values.append(value)
        if len(self.values) > self.period:
            self.values.pop(0)
        return self.calculate()
    
    def calculate(self) -> float:
        return sum(self.values) / len(self.values)
```

---

## 事件 API

### EventEngine

```python
from bobquant.event import EventEngine, Event

engine = EventEngine()

# 注册事件处理器
def on_trade_event(event: Event):
    print(f"成交：{event.data}")

engine.register_handler("trade", on_trade_event)

# 发送事件
engine.put_event(Event(
    type="trade",
    data={"symbol": "600519", "volume": 100, "price": 1800.0}
))
```

---

## 通知 API

### FeishuNotifier

```python
from bobquant.notify import FeishuNotifier

notifier = FeishuNotifier(
    webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    secret="xxx"
)

# 发送消息
notifier.send_text("交易通知：买入 600519 100 股")

# 发送卡片
notifier.send_card(
    title="交易通知",
    content={
        "symbol": "600519",
        "side": "buy",
        "quantity": 100,
        "price": 1800.0
    }
)
```

---

## 权限 API

### PermissionEngine

```python
from bobquant.permissions import PermissionEngine

engine = PermissionEngine(config=permission_config)

# 检查权限
allowed = engine.check_permission(
    user_id="user_001",
    action="place_order",
    resource="600519",
    context={"quantity": 1000, "price": 1800.0}
)

if not allowed:
    print("权限不足")
```

---

## 遥测 API

### MetricsCollector

```python
from bobquant.telemetry import MetricsCollector

collector = MetricsCollector()

# 记录指标
collector.record_metric(
    name="order_latency",
    value=50.5,
    tags={"symbol": "600519", "side": "buy"}
)

# 获取指标
metrics = collector.get_metrics(
    name="order_latency",
    start="2023-01-01",
    end="2023-12-31"
)
```

---

## 错误处理

### 异常类型

```python
from bobquant.core import (
    BobQuantError,
    ValidationError,
    PermissionError,
    ExecutionError,
    DataError
)

try:
    # 可能出错的代码
    result = engine.place_order(...)
except ValidationError as e:
    print(f"验证错误：{e}")
except PermissionError as e:
    print(f"权限错误：{e}")
except ExecutionError as e:
    print(f"执行错误：{e}")
except DataError as e:
    print(f"数据错误：{e}")
except BobQuantError as e:
    print(f"通用错误：{e}")
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v3.0 | 2026-04-11 | 工具系统重构、配置系统升级 |
| v2.5 | 2026-04-08 | 网格 T 策略优化 |
| v2.4 | 2026-04-01 | 多因子策略完善 |
| v2.2 | 2026-03-27 | 模拟盘部署 |

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
