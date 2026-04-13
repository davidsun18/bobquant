# BobQuant 代码示例集

常用代码示例和模板。

---

## 📋 目录

1. [策略示例](#策略示例)
2. [指标示例](#指标示例)
3. [回测示例](#回测示例)
4. [数据示例](#数据示例)
5. [工具示例](#工具示例)
6. [风控示例](#风控示例)
7. [Web 示例](#web-示例)
8. [实用脚本](#实用脚本)

---

## 策略示例

### 1. 均线交叉策略

```python
"""
简单均线交叉策略
- 金叉 (短均线上穿长均线): 买入
- 死叉 (短均线下穿长均线): 卖出
"""

from bobquant.strategy import Strategy
from bobquant.indicator import MA

class MAStrategy(Strategy):
    def __init__(self, fast_period=5, slow_period=20):
        super().__init__()
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def on_init(self):
        self.ma_fast = MA(self.fast_period)
        self.ma_slow = MA(self.slow_period)
        self.position = 0
    
    def on_bar(self, bar):
        # 更新均线
        self.ma_fast.update(bar.close)
        self.ma_slow.update(bar.close)
        
        # 检查金叉
        if (self.ma_fast.value > self.ma_slow.value and 
            self.ma_fast.prev_value <= self.ma_slow.prev_value and
            self.position == 0):
            self.buy(bar.symbol, 100)
            self.position = 100
            self.logger.info(f"金叉买入 {bar.symbol}")
        
        # 检查死叉
        elif (self.ma_fast.value < self.ma_slow.value and 
              self.ma_fast.prev_value >= self.ma_slow.prev_value and
              self.position > 0):
            self.sell(bar.symbol, self.position)
            self.position = 0
            self.logger.info(f"死叉卖出 {bar.symbol}")


# 运行策略
if __name__ == "__main__":
    from bobquant.core import TradingEngine
    
    engine = TradingEngine(
        strategy=MAStrategy(fast_period=5, slow_period=20),
        mode="simulation"
    )
    engine.start()
```

### 2. RSI 超买超卖策略

```python
"""
RSI 超买超卖策略
- RSI < 30: 超卖，买入
- RSI > 70: 超买，卖出
"""

from bobquant.strategy import Strategy
from bobquant.indicator import RSI

class RSIStrategy(Strategy):
    def __init__(self, rsi_period=14, oversold=30, overbought=70):
        super().__init__()
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def on_init(self):
        self.rsi = RSI(self.rsi_period)
    
    def on_bar(self, bar):
        self.rsi.update(bar.close)
        
        # 超卖买入
        if self.rsi.value < self.oversold and not self.get_position(bar.symbol):
            self.buy(bar.symbol, 100)
            self.logger.info(f"RSI 超卖买入 {bar.symbol}, RSI={self.rsi.value:.1f}")
        
        # 超买卖出
        elif self.rsi.value > self.overbought and self.get_position(bar.symbol):
            self.sell(bar.symbol, self.get_position(bar.symbol))
            self.logger.info(f"RSI 超买卖出 {bar.symbol}, RSI={self.rsi.value:.1f}")
```

### 3. MACD 策略

```python
"""
MACD 策略
- DIF 上穿 DEA: 买入
- DIF 下穿 DEA: 卖出
"""

from bobquant.strategy import Strategy
from bobquant.indicator import MACD

class MACDStrategy(Strategy):
    def __init__(self, fast=12, slow=26, signal=9):
        super().__init__()
        self.fast = fast
        self.slow = slow
        self.signal = signal
    
    def on_init(self):
        self.macd = MACD(self.fast, self.slow, self.signal)
    
    def on_bar(self, bar):
        self.macd.update(bar.close)
        
        dif_cross = self.macd.dif - self.macd.dea
        dif_cross_prev = self.macd.prev_dif - self.macd.prev_dea
        
        # 金叉
        if dif_cross > 0 and dif_cross_prev <= 0:
            if not self.get_position(bar.symbol):
                self.buy(bar.symbol, 100)
                self.logger.info(f"MACD 金叉买入 {bar.symbol}")
        
        # 死叉
        elif dif_cross < 0 and dif_cross_prev >= 0:
            if self.get_position(bar.symbol):
                self.sell(bar.symbol, self.get_position(bar.symbol))
                self.logger.info(f"MACD 死叉卖出 {bar.symbol}")
```

### 4. 布林带策略

```python
"""
布林带策略
- 价格触及下轨：买入
- 价格触及上轨：卖出
"""

from bobquant.strategy import Strategy
from bobquant.indicator import BollingerBands

class BollingerStrategy(Strategy):
    def __init__(self, period=20, std_dev=2):
        super().__init__()
        self.period = period
        self.std_dev = std_dev
    
    def on_init(self):
        self.bb = BollingerBands(self.period, self.std_dev)
    
    def on_bar(self, bar):
        self.bb.update(bar.close)
        
        # 触及下轨买入
        if bar.close <= self.bb.lower and not self.get_position(bar.symbol):
            self.buy(bar.symbol, 100)
            self.logger.info(f"触及下轨买入 {bar.symbol}")
        
        # 触及上轨卖出
        elif bar.close >= self.bb.upper and self.get_position(bar.symbol):
            self.sell(bar.symbol, self.get_position(bar.symbol))
            self.logger.info(f"触及上轨卖出 {bar.symbol}")
```

### 5. 多因子策略

```python
"""
多因子选股策略
- 动量因子：过去 20 日收益率
- 价值因子：市盈率倒数
- 质量因子：ROE
"""

from bobquant.strategy import MultiFactorStrategy
from bobquant.data import get_financial_data

class MultiFactorStrategy(MultiFactorStrategy):
    def __init__(self, factors=None, weights=None, rebalance_days=5):
        super().__init__(
            factors=factors or ["momentum", "value", "quality"],
            weights=weights or [0.4, 0.3, 0.3],
            rebalance_days=rebalance_days
        )
    
    def calculate_factor_score(self, symbol: str) -> float:
        """计算单只股票的综合得分"""
        scores = {}
        
        # 动量因子 (过去 20 日收益率)
        momentum = self.get_momentum(symbol, period=20)
        scores["momentum"] = self.normalize(momentum)
        
        # 价值因子 (EP 收益率)
        pe = self.get_pe_ratio(symbol)
        scores["value"] = self.normalize(1 / pe if pe > 0 else 0)
        
        # 质量因子 (ROE)
        roe = self.get_roe(symbol)
        scores["quality"] = self.normalize(roe)
        
        # 加权得分
        total_score = sum(
            scores[factor] * weight 
            for factor, weight in zip(self.factors, self.weights)
        )
        
        return total_score
    
    def normalize(self, value: float, min_val=0, max_val=1) -> float:
        """归一化到 0-1"""
        return max(0, min(1, (value - min_val) / (max_val - min_val + 1e-6)))
    
    def get_momentum(self, symbol: str, period: int = 20) -> float:
        """计算动量"""
        data = self.get_history_data(symbol, period=period)
        if len(data) < period:
            return 0
        return data['close'].pct_change(period).iloc[-1]
    
    def get_pe_ratio(self, symbol: str) -> float:
        """获取市盈率"""
        financials = get_financial_data(symbol)
        return financials.get('pe_ratio', 999)
    
    def get_roe(self, symbol: str) -> float:
        """获取 ROE"""
        financials = get_financial_data(symbol)
        return financials.get('roe', 0)
```

### 6. 网格 T+0 策略

```python
"""
网格 T+0 策略
- 价格每下跌 grid_size%，买入一格
- 价格每上涨 grid_size%，卖出一格
"""

from bobquant.strategy import Strategy

class GridTStrategy(Strategy):
    def __init__(self, grid_size=0.02, max_grid=10, base_quantity=100):
        super().__init__()
        self.grid_size = grid_size  # 网格大小 (2%)
        self.max_grid = max_grid    # 最大网格数
        self.base_quantity = base_quantity  # 每格数量
        self.grids = {}  # 每只股票的网格状态
    
    def on_init(self):
        self.universe = ["600519.SH", "000858.SZ"]
        for symbol in self.universe:
            self.grids[symbol] = {
                "base_price": None,
                "grid_level": 0,
                "position": 0
            }
    
    def on_bar(self, bar):
        grid = self.grids[bar.symbol]
        
        # 初始化基准价
        if grid["base_price"] is None:
            grid["base_price"] = bar.close
            return
        
        # 计算网格位置
        price_change = (bar.close - grid["base_price"]) / grid["base_price"]
        target_grid = int(price_change / self.grid_size)
        
        # 限制网格范围
        target_grid = max(-self.max_grid, min(self.max_grid, target_grid))
        
        # 调整仓位
        grid_diff = target_grid - grid["grid_level"]
        
        if grid_diff > 0:
            # 价格上涨，卖出
            quantity = min(grid_diff * self.base_quantity, grid["position"])
            if quantity > 0:
                self.sell(bar.symbol, quantity)
                grid["position"] -= quantity
                self.logger.info(f"网格卖出 {bar.symbol} {quantity}股")
        
        elif grid_diff < 0:
            # 价格下跌，买入
            quantity = abs(grid_diff) * self.base_quantity
            if self.account.available_cash > bar.close * quantity:
                self.buy(bar.symbol, quantity)
                grid["position"] += quantity
                self.logger.info(f"网格买入 {bar.symbol} {quantity}股")
        
        grid["grid_level"] = target_grid
```

### 7. 均值回归策略

```python
"""
均值回归策略
- 价格偏离均线超过阈值：反向交易
"""

from bobquant.strategy import Strategy
from bobquant.indicator import MA, ATR

class MeanReversionStrategy(Strategy):
    def __init__(self, ma_period=20, threshold=2):
        super().__init__()
        self.ma_period = ma_period
        self.threshold = threshold  # 阈值 (倍数 ATR)
    
    def on_init(self):
        self.ma = MA(self.ma_period)
        self.atr = ATR(14)
    
    def on_bar(self, bar):
        self.ma.update(bar.close)
        self.atr.update(bar.high, bar.low, bar.close)
        
        # 计算偏离
        deviation = bar.close - self.ma.value
        normalized_dev = deviation / (self.atr.value + 1e-6)
        
        # 价格低于均线 -2ATR: 买入
        if normalized_dev < -self.threshold and not self.get_position(bar.symbol):
            self.buy(bar.symbol, 100)
            self.logger.info(f"均值回归买入 {bar.symbol}, 偏离={normalized_dev:.2f}")
        
        # 价格高于均线 +2ATR: 卖出
        elif normalized_dev > self.threshold and self.get_position(bar.symbol):
            self.sell(bar.symbol, self.get_position(bar.symbol))
            self.logger.info(f"均值回归卖出 {bar.symbol}, 偏离={normalized_dev:.2f}")
        
        # 回归均线：平仓
        elif abs(normalized_dev) < 0.5 and self.get_position(bar.symbol):
            self.sell(bar.symbol, self.get_position(bar.symbol))
            self.logger.info(f"回归平仓 {bar.symbol}")
```

---

## 指标示例

### 1. 自定义指标

```python
"""
自定义指标示例
"""

from bobquant.indicator import Indicator

class MyCustomIndicator(Indicator):
    """自定义指标：价格动量"""
    
    def __init__(self, period=10):
        self.period = period
        self.prices = []
    
    def update(self, price: float) -> float:
        """更新并返回指标值"""
        self.prices.append(price)
        
        # 保持固定长度
        if len(self.prices) > self.period:
            self.prices.pop(0)
        
        # 计算动量
        if len(self.prices) >= self.period:
            momentum = (self.prices[-1] - self.prices[0]) / self.prices[0]
            return momentum
        
        return 0
    
    def reset(self):
        """重置指标"""
        self.prices = []


# 使用示例
if __name__ == "__main__":
    indicator = MyCustomIndicator(period=10)
    
    # 模拟数据
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    
    for price in prices:
        value = indicator.update(price)
        print(f"价格={price}, 动量={value:.2%}")
```

### 2. 组合指标

```python
"""
组合指标：将多个指标组合成一个信号
"""

from bobquant.indicator import MA, RSI, MACD

class CompositeIndicator:
    """组合指标"""
    
    def __init__(self):
        self.ma = MA(20)
        self.rsi = RSI(14)
        self.macd = MACD(12, 26, 9)
    
    def update(self, bar) -> dict:
        """更新所有指标并返回信号"""
        self.ma.update(bar.close)
        self.rsi.update(bar.close)
        self.macd.update(bar.close)
        
        # 计算各指标信号
        ma_signal = 1 if bar.close > self.ma.value else -1
        rsi_signal = 1 if self.rsi.value < 30 else (-1 if self.rsi.value > 70 else 0)
        macd_signal = 1 if self.macd.dif > self.macd.dea else -1
        
        # 综合信号
        total_signal = ma_signal + rsi_signal + macd_signal
        
        return {
            "ma_signal": ma_signal,
            "rsi_signal": rsi_signal,
            "macd_signal": macd_signal,
            "total_signal": total_signal,
            "recommendation": self._interpret(total_signal)
        }
    
    def _interpret(self, signal: int) -> str:
        """解释信号"""
        if signal >= 2:
            return "强烈买入"
        elif signal == 1:
            return "买入"
        elif signal == 0:
            return "持有"
        elif signal == -1:
            return "卖出"
        else:
            return "强烈卖出"


# 使用示例
if __name__ == "__main__":
    composite = CompositeIndicator()
    
    # 模拟 K 线
    bar = type('Bar', (), {"close": 100, "high": 102, "low": 98})
    
    for i in range(30):
        bar.close = 100 + i
        result = composite.update(bar)
        print(f"Day {i}: 信号={result['total_signal']}, 建议={result['recommendation']}")
```

---

## 回测示例

### 1. 简单回测

```python
"""
简单回测示例
"""

from bobquant.backtest import BacktestEngine
from bobquant.strategy import MAStrategy

# 创建回测引擎
engine = BacktestEngine(
    strategy=MAStrategy(fast_period=5, slow_period=20),
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=1000000,
    commission_rate=0.0005,
    slippage=0.001
)

# 运行回测
results = engine.run()

# 打印结果
print("=" * 50)
print("回测结果")
print("=" * 50)
print(f"初始资金：{results.initial_capital:,.2f}")
print(f"最终资金：{results.final_capital:,.2f}")
print(f"总收益：{results.total_return:.2%}")
print(f"年化收益：{results.annual_return:.2%}")
print(f"夏普比率：{results.sharpe_ratio:.2f}")
print(f"最大回撤：{results.max_drawdown:.2%}")
print(f"交易次数：{results.total_trades}")
print(f"胜率：{results.win_rate:.2%}")

# 生成报告
results.generate_report("backtest_report.html")
```

### 2. 多股票回测

```python
"""
多股票组合回测
"""

from bobquant.backtest import PortfolioBacktest
from bobquant.strategy import MultiFactorStrategy

# 创建组合回测
backtest = PortfolioBacktest(
    strategy=MultiFactorStrategy(),
    universe=["600519.SH", "000858.SZ", "002415.SZ"],
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=1000000,
    rebalance_days=5
)

# 运行回测
results = backtest.run()

# 分析各股票贡献
for symbol, contribution in results.contribution.items():
    print(f"{symbol}: 贡献收益 {contribution:.2%}")

# 生成报告
results.generate_report("portfolio_backtest.html")
```

### 3. 参数扫描回测

```python
"""
参数扫描回测
"""

from bobquant.backtest import BacktestEngine
from bobquant.strategy import MAStrategy

# 参数范围
fast_periods = [5, 10, 15]
slow_periods = [20, 30, 40]

results = []

# 扫描所有参数组合
for fast in fast_periods:
    for slow in slow_periods:
        engine = BacktestEngine(
            strategy=MAStrategy(fast_period=fast, slow_period=slow),
            start_date="2023-01-01",
            end_date="2023-12-31",
            initial_capital=1000000
        )
        
        result = engine.run()
        results.append({
            "fast": fast,
            "slow": slow,
            "sharpe": result.sharpe_ratio,
            "return": result.total_return,
            "drawdown": result.max_drawdown
        })

# 找出最优参数
best = max(results, key=lambda x: x["sharpe"])
print(f"最优参数：快={best['fast']}, 慢={best['slow']}")
print(f"夏普比率：{best['sharpe']:.2f}")
print(f"总收益：{best['return']:.2%}")
```

---

## 数据示例

### 1. 获取行情数据

```python
"""
获取行情数据示例
"""

from bobquant.data import get_market_data, get_realtime_data

# 获取日线数据
df = get_market_data(
    symbol="600519.SH",
    interval="1d",
    start="2023-01-01",
    end="2023-12-31"
)
print(df.head())

# 获取分钟数据
df = get_market_data(
    symbol="600519.SH",
    interval="1m",
    start="2023-01-01 09:30:00",
    end="2023-01-01 15:00:00"
)
print(df.head())

# 获取实时行情
tick = get_realtime_data("600519.SH")
print(f"当前价：{tick['price']}")
print(f"涨跌幅：{tick['change']:.2%}")
```

### 2. 获取财务数据

```python
"""
获取财务数据示例
"""

from bobquant.data import get_financial_data

# 获取财务数据
financials = get_financial_data("600519.SH")

print(f"市盈率：{financials['pe_ratio']}")
print(f"市净率：{financials['pb_ratio']}")
print(f"ROE: {financials['roe']:.2%}")
print(f"毛利率：{financials['gross_margin']:.2%}")
print(f"净利润：{financials['net_profit']:.2f}亿")
```

### 3. 数据预处理

```python
"""
数据预处理示例
"""

import pandas as pd
from bobquant.data import get_market_data

# 获取数据
df = get_market_data("600519.SH", "1d", "2023-01-01", "2023-12-31")

# 处理缺失值
df = df.fillna(method='ffill')  # 前向填充
df = df.dropna()  # 或删除缺失值

# 计算收益率
df['return'] = df['close'].pct_change()

# 计算对数收益率
df['log_return'] = np.log(df['close'] / df['close'].shift(1))

# 滚动统计
df['rolling_mean'] = df['return'].rolling(20).mean()
df['rolling_std'] = df['return'].rolling(20).std()

# 归一化
df['close_norm'] = (df['close'] - df['close'].min()) / (df['close'].max() - df['close'].min())

print(df.head())
```

---

## 工具示例

### 1. 使用交易工具

```python
"""
交易工具使用示例
"""

import asyncio
from bobquant.tools.trading import place_order, cancel_order, get_position

async def main():
    # 下单
    result = await place_order(
        symbol="600519",
        side="buy",
        quantity=100,
        price=1800.0,
        order_type="limit"
    )
    print(f"下单结果：{result}")
    
    # 查询持仓
    position = await get_position(symbol="600519")
    print(f"持仓：{position}")
    
    # 撤单
    if result.get("order_id"):
        cancel_result = await cancel_order(order_id=result["order_id"])
        print(f"撤单结果：{cancel_result}")

asyncio.run(main())
```

### 2. 使用数据工具

```python
"""
数据工具使用示例
"""

import asyncio
from bobquant.tools.data import get_market_data, get_realtime_data

async def main():
    # 获取历史数据
    df = await get_market_data(
        symbol="600519",
        interval="1d",
        start="2023-01-01",
        end="2023-12-31"
    )
    print(df.head())
    
    # 获取实时数据
    tick = await get_realtime_data(symbols=["600519", "000858"])
    print(tick)

asyncio.run(main())
```

### 3. 使用风控工具

```python
"""
风控工具使用示例
"""

import asyncio
from bobquant.tools.risk import risk_check, set_stop_loss, get_risk_metrics

async def main():
    # 风险检查
    result = await risk_check(
        symbol="600519",
        quantity=1000,
        price=1800.0,
        side="buy"
    )
    print(f"风控检查：{'通过' if result['passed'] else '失败'}")
    
    # 设置止损
    sl_result = await set_stop_loss(
        symbol="600519",
        stop_loss_price=1700.0,
        stop_profit_price=2000.0
    )
    print(f"止损设置：{sl_result}")
    
    # 获取风险指标
    metrics = await get_risk_metrics(account_id="account_001")
    print(f"VaR: {metrics['var_95']:.2%}")
    print(f"最大回撤：{metrics['max_drawdown']:.2%}")

asyncio.run(main())
```

---

## 风控示例

### 1. 仓位管理

```python
"""
仓位管理示例
"""

from bobquant.risk_management import PositionManager

class MyPositionManager:
    def __init__(self, account):
        self.account = account
        self.max_position_pct = 0.10  # 单票最大 10%
        self.max_total_position = 0.80  # 总仓位最大 80%
        self.max_positions = 10  # 最多持有 10 只
    
    def calculate_buy_quantity(self, symbol, price, signal_strength=1.0):
        """计算买入数量"""
        # 基础仓位
        base_value = self.account.total_assets * self.max_position_pct
        
        # 根据信号强度调整
        actual_value = base_value * signal_strength
        
        # 检查总仓位
        current_position_value = sum(
            pos['volume'] * pos['price'] 
            for pos in self.account.positions.values()
        )
        available_value = (
            self.account.total_assets * self.max_total_position - 
            current_position_value
        )
        
        # 取较小值
        value = min(actual_value, available_value)
        
        # 计算数量 (100 股的整数倍)
        quantity = int(value / price / 100) * 100
        
        return max(0, quantity)
```

### 2. 止损管理

```python
"""
止损管理示例
"""

from bobquant.risk_management import StopLossManager

class MyStopLossManager:
    def __init__(self):
        self.stop_losses = {}
    
    def set_stop_loss(self, symbol, entry_price, stop_loss_pct=0.05, 
                      trailing=False, trailing_pct=0.03):
        """设置止损"""
        self.stop_losses[symbol] = {
            "entry_price": entry_price,
            "stop_loss_price": entry_price * (1 - stop_loss_pct),
            "trailing": trailing,
            "trailing_pct": trailing_pct,
            "highest_price": entry_price
        }
    
    def update(self, symbol, current_price):
        """更新止损价 (移动止损)"""
        if symbol not in self.stop_losses:
            return None
        
        sl = self.stop_losses[symbol]
        
        if sl["trailing"]:
            # 更新最高价
            sl["highest_price"] = max(sl["highest_price"], current_price)
            
            # 更新止损价
            new_stop = sl["highest_price"] * (1 - sl["trailing_pct"])
            sl["stop_loss_price"] = max(sl["stop_loss_price"], new_stop)
        
        # 检查是否触发
        if current_price <= sl["stop_loss_price"]:
            return "triggered"
        
        return None
    
    def check_all(self, prices):
        """检查所有止损"""
        triggered = []
        for symbol, price in prices.items():
            result = self.update(symbol, price)
            if result == "triggered":
                triggered.append(symbol)
        return triggered
```

---

## Web 示例

### 1. Streamlit 页面

```python
"""
Streamlit 页面示例
"""

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="BobQuant", layout="wide")

# 标题
st.title("📊 BobQuant 数据看板")

# 侧边栏
st.sidebar.header("设置")
symbol = st.sidebar.text_input("股票代码", "600519.SH")
period = st.sidebar.selectbox("周期", ["1d", "1w", "1m", "3m", "6m", "1y"])

# 加载数据
@st.cache_data
def load_data(symbol, period):
    from bobquant.data import get_market_data
    return get_market_data(symbol, "1d", "2023-01-01", "2023-12-31")

df = load_data(symbol, period)

# 主要指标
col1, col2, col3, col4 = st.columns(4)
col1.metric("最新价", f"{df['close'].iloc[-1]:.2f}")
col2.metric("涨跌幅", f"{df['close'].pct_change().iloc[-1]:.2%}")
col3.metric("成交量", f"{df['volume'].iloc[-1]:,.0f}")
col4.metric("成交额", f"{df['amount'].iloc[-1]/1e8:.2f}亿")

# K 线图
fig = px candlestick(
    df,
    x=df.index,
    open='open', high='high', low='low', close='close',
    title=f"{symbol} K 线图"
)
st.plotly_chart(fig, use_container_width=True)

# 成交量图
fig_vol = px.bar(df, x=df.index, y='volume', title="成交量")
st.plotly_chart(fig_vol, use_container_width=True)
```

### 2. 实时数据更新

```python
"""
实时数据更新示例
"""

import streamlit as st
import time
from bobquant.data import get_realtime_data

st.title("实时行情")

# 占位符
placeholder = st.empty()

# 持续更新
while True:
    with placeholder.container():
        # 获取数据
        tick = get_realtime_data("600519.SH")
        
        # 显示
        st.metric(
            label="贵州茅台",
            value=f"{tick['price']:.2f}",
            delta=f"{tick['change']:.2%}"
        )
    
    time.sleep(3)  # 3 秒刷新
```

---

## 实用脚本

### 1. 批量回测脚本

```python
#!/usr/bin/env python3
"""
批量回测脚本
"""

from bobquant.backtest import BacktestEngine
from bobquant.strategy import MAStrategy
import pandas as pd

# 股票列表
stocks = ["600519.SH", "000858.SZ", "002415.SZ", "300750.SZ"]

results = []

for symbol in stocks:
    print(f"回测 {symbol}...")
    
    engine = BacktestEngine(
        strategy=MAStrategy(),
        symbols=[symbol],
        start_date="2023-01-01",
        end_date="2023-12-31",
        initial_capital=100000
    )
    
    result = engine.run()
    
    results.append({
        "symbol": symbol,
        "return": result.total_return,
        "sharpe": result.sharpe_ratio,
        "drawdown": result.max_drawdown,
        "trades": result.total_trades
    })

# 保存结果
df = pd.DataFrame(results)
print(df)
df.to_csv("backtest_results.csv", index=False)
```

### 2. 数据下载脚本

```python
#!/usr/bin/env python3
"""
批量数据下载脚本
"""

from bobquant.data import get_market_data
import pandas as pd
from datetime import datetime

# 股票列表
stocks = ["600519.SH", "000858.SZ", "002415.SZ"]

for symbol in stocks:
    print(f"下载 {symbol}...")
    
    # 下载日线数据
    df = get_market_data(symbol, "1d", "2020-01-01", datetime.now().strftime("%Y-%m-%d"))
    df.to_csv(f"data/{symbol.replace('.', '_')}_daily.csv")
    
    # 下载分钟数据 (最近 30 天)
    df_min = get_market_data(symbol, "1m", "2023-12-01", datetime.now().strftime("%Y-%m-%d"))
    df_min.to_csv(f"data/{symbol.replace('.', '_')}_1m.csv")

print("下载完成!")
```

### 3. 绩效报告脚本

```python
#!/usr/bin/env python3
"""
绩效报告生成脚本
"""

import json
import pandas as pd
from datetime import datetime

# 加载交易记录
with open("logs/trades.json") as f:
    trades = json.load(f)

# 转换为 DataFrame
df = pd.DataFrame(trades)

# 计算绩效
total_trades = len(df)
win_trades = len(df[df['pnl'] > 0])
win_rate = win_trades / total_trades if total_trades > 0 else 0
total_pnl = df['pnl'].sum()
avg_pnl = df['pnl'].mean()
max_win = df['pnl'].max()
max_loss = df['pnl'].min()

# 生成报告
report = f"""
# 交易绩效报告
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 总体统计
- 总交易次数：{total_trades}
- 盈利次数：{win_trades}
- 胜率：{win_rate:.2%}
- 总盈亏：{total_pnl:.2f}
- 平均盈亏：{avg_pnl:.2f}
- 最大盈利：{max_win:.2f}
- 最大亏损：{max_loss:.2f}

## 按月统计
"""

# 按月统计
df['month'] = pd.to_datetime(df['time']).dt.to_period('M')
monthly = df.groupby('month')['pnl'].agg(['sum', 'count', 'mean'])
report += monthly.to_markdown()

# 保存报告
with open("reports/performance.md", "w") as f:
    f.write(report)

print("报告已生成：reports/performance.md")
```

---

## 总结

以上示例涵盖了 BobQuant 的主要使用场景。你可以根据需要修改和组合这些示例，创建适合自己的策略和工具。

**提示**:
- 所有示例代码都在 `docs/examples/` 目录下有完整版本
- 运行示例前请确保已安装所有依赖
- 实盘交易前请充分测试

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
