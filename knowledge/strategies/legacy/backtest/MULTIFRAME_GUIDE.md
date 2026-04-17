# Backtrader 多时间框架分析使用指南

## 📋 概述

本模块实现了基于 Backtrader 的多时间框架分析系统，专门用于优化做 T 策略。

**核心功能：**
- ✅ 同时使用日线 + 分钟线数据
- ✅ 多时间框架信号确认
- ✅ 应用于做 T 策略优化

## 📁 文件结构

```
bobquant/backtest/
├── backtrader_multiframe.py    # 核心模块
├── test_multiframe.py          # 测试脚本
└── MULTIFRAME_GUIDE.md         # 使用指南（本文件）
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip3 install backtrader
```

### 2. 导入模块

```python
from backtrader_multiframe import (
    MultiFrameStrategy,
    T0MultiFrameStrategy,
    MultiFrameAnalyzer
)
```

### 3. 使用示例

#### 方式一：信号分析器（离线分析）

```python
import pandas as pd
from backtrader_multiframe import MultiFrameAnalyzer

# 准备数据
daily_df = pd.read_csv('daily_data.csv')  # 日线数据
minute_df = pd.read_csv('minute_data.csv')  # 分钟线数据

# 创建分析器
analyzer = MultiFrameAnalyzer(daily_df, minute_df)

# 分析信号
results = analyzer.analyze_signals()

# 查看结果
print(f"总信号数：{results['total_signals']}")
print(f"买入信号：{results['buy_signals']}")
print(f"卖出信号：{results['sell_signals']}")
```

#### 方式二：Backtrader 回测

```python
import backtrader as bt
from backtrader_multiframe import T0MultiFrameStrategy

# 创建 Cerebro 引擎
cerebro = bt.Cerebro()

# 添加策略
cerebro.addstrategy(T0MultiFrameStrategy)

# 添加数据（日线 + 分钟线）
data_daily = bt.feeds.PandasData(dataname=daily_df, ...)
data_minute = bt.feeds.PandasData(dataname=minute_df, ...)
cerebro.adddata(data_daily)
cerebro.adddata(data_minute)

# 设置资金和手续费
cerebro.broker.setcash(100000.0)
cerebro.broker.setcommission(commission=0.0003)

# 运行回测
results = cerebro.run()
```

## 📊 多时间框架策略逻辑

### 核心原则

```
┌─────────────────────────────────────────────────────┐
│                  多时间框架决策流程                   │
├─────────────────────────────────────────────────────┤
│  1. 日线确定趋势方向                                 │
│     ↓                                               │
│  2. 分钟线寻找入场点                                 │
│     ↓                                               │
│  3. 多时间框架信号确认                               │
│     ↓                                               │
│  4. 执行交易                                        │
└─────────────────────────────────────────────────────┘
```

### 信号确认规则

| 日线趋势 | 分钟线信号 | 操作 | 胜率 |
|---------|-----------|------|------|
| 上涨 | 买入 | **强买入** | 高 |
| 下跌 | 卖出 | **强卖出** | 高 |
| 上涨 | 卖出 | 观望/减仓 | 低 |
| 下跌 | 买入 | 观望 | 低 |
| 震荡 | RSI<20 | 轻仓买入 | 中 |
| 震荡 | RSI>80 | 轻仓卖出 | 中 |

### 技术指标

#### 日线指标（趋势判断）
- **SMA5 / SMA20**：快慢均线判断趋势
- **RSI(14)**：动量指标，>50 为强势
- **MACD**：趋势确认（可选）

#### 分钟线指标（入场时机）
- **SMA5 / SMA20**：短期趋势
- **Bollinger Bands(20, 2)**：支撑/压力位
- **RSI(14)**：超买超卖判断

## 💡 做 T 策略优化建议

### 1. 信号优化

```python
# 增加成交量确认
if volume > sma_volume * 1.5:  # 放量
    signal_strength *= 1.2

# 增加大盘过滤
if market_trend == 'up' and stock_trend == 'up':
    signal_strength *= 1.3
```

### 2. 仓位管理

```python
# 根据趋势强度动态调整仓位
def calculate_position_size(trend_strength):
    if trend_strength > 0.8:
        return 0.5  # 50% 仓位
    elif trend_strength > 0.5:
        return 0.3  # 30% 仓位
    else:
        return 0.1  # 10% 仓位
```

### 3. 止盈止损

```python
# 移动止损
def update_stop_loss(entry_price, current_price, profit_target):
    if current_price > entry_price * (1 + profit_target * 0.5):
        # 盈利达到一半目标时，启动移动止损
        return current_price * 0.995  # 0.5% 回撤止损
    return entry_price * 0.995  # 初始止损
```

### 4. 时间过滤

```python
# 只在流动性好的时段交易
def is_good_trading_time(current_time):
    # 开盘后 30 分钟
    if current_time.hour == 9 and current_time.minute >= 30:
        return True
    # 收盘前 30 分钟
    if current_time.hour == 14 and current_time.minute >= 30:
        return True
    return False
```

## 🧪 测试运行

```bash
cd bobquant/backtest
python3 test_multiframe.py
```

### 测试输出示例

```
============================================================
测试多时间框架信号分析
============================================================
生成示例数据...
  ✓ 日线数据：60 条
  ✓ 分钟线数据：1200 条

分析信号...
------------------------------------------------------------
信号统计结果
------------------------------------------------------------
总信号数：1117
买入信号：1117
卖出信号：0
```

## 📈 性能优化

### 1. 数据预处理

```python
# 预计算指标，避免重复计算
def preprocess_data(df):
    df['sma_fast'] = df['close'].rolling(5).mean()
    df['sma_slow'] = df['close'].rolling(20).mean()
    df['rsi'] = calculate_rsi(df['close'], 14)
    return df
```

### 2. 信号缓存

```python
# 缓存日线趋势，避免重复计算
@lru_cache(maxsize=1000)
def get_daily_trend(date):
    # ... 计算逻辑
    return trend
```

### 3. 并行处理

```python
# 多股票并行分析
from multiprocessing import Pool

with Pool(processes=4) as pool:
    results = pool.map(analyze_stock, stock_list)
```

## ⚠️ 注意事项

1. **数据对齐**：确保日线和分钟线数据的时间戳正确对齐
2. **未来函数**：避免使用未来数据，确保信号基于历史信息
3. **过拟合**：不要在单一股票上过度优化参数
4. **交易成本**：回测时考虑手续费和滑点
5. **流动性**：分钟线策略需要足够的流动性支持

## 🔧 参数调优

### 策略参数

```python
cerebro.addstrategy(
    T0MultiFrameStrategy,
    fast_period=5,        # 快线周期
    slow_period=20,       # 慢线周期
    rsi_period=14,        # RSI 周期
    base_position=0.5,    # 底仓比例
    t0_size=0.3,          # 做 T 仓位
    profit_target=0.01,   # 止盈目标
    stop_loss=0.005,      # 止损
    max_trades_per_day=3  # 每日最大交易次数
)
```

### 推荐参数范围

| 参数 | 推荐范围 | 说明 |
|-----|---------|------|
| fast_period | 3-10 | 短线敏感度高 |
| slow_period | 15-30 | 趋势判断 |
| rsi_period | 10-20 | 标准 14 |
| t0_size | 0.2-0.5 | 根据风险偏好 |
| profit_target | 0.005-0.02 | 0.5%-2% |

## 📚 参考资料

- [Backtrader 官方文档](https://www.backtrader.com/docu/)
- [多时间框架分析原理](https://www.investopedia.com/terms/m/multiple-time-frames.asp)
- [做 T 策略实战](../docs/做 T 策略指南.md)

## 📞 技术支持

如有问题，请查看：
1. 测试脚本 `test_multiframe.py`
2. Backtrader 文档
3. 联系开发团队

---

**最后更新**: 2026-04-10
**版本**: v1.0
