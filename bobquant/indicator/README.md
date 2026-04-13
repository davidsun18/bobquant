# BobQuant 指标模块

技术指标、TA-Lib 集成、自定义指标。

---

## 📁 模块结构

```
indicator/
├── __init__.py              # 模块导出
├── technical.py             # 技术指标
├── talib_advanced.py        # TA-Lib 高级用法
└── TALIB_ADVANCED_USAGE.md  # TA-Lib 使用文档
```

---

## 🚀 快速开始

### 1. 使用内置指标

```python
from bobquant.indicator import MA, MACD, RSI

# 移动平均
ma = MA(20)
ma.update(100)
ma.update(101)
print(ma.value)

# MACD
macd = MACD(12, 26, 9)
macd.update(100)
print(f"DIF: {macd.dif}, DEA: {macd.dea}")

# RSI
rsi = RSI(14)
rsi.update(100)
print(f"RSI: {rsi.value}")
```

### 2. 使用 TA-Lib

```python
from bobquant.indicator import TALib

talib = TALib()

# SMA
sma = talib.SMA(close, timeperiod=20)

# MACD
macd, signal, hist = talib.MACD(close)

# RSI
rsi = talib.RSI(close, timeperiod=14)
```

---

## 📖 指标列表

### 趋势指标

| 指标 | 类名 | 说明 |
|------|------|------|
| 移动平均 | MA | 简单移动平均 |
| 指数平均 | EMA | 指数移动平均 |
| MACD | MACD | 平滑异同移动平均 |
| 布林带 | BollingerBands | 布林带 |

### 动量指标

| 指标 | 类名 | 说明 |
|------|------|------|
| RSI | RSI | 相对强弱指标 |
| KDJ | KDJ | 随机指标 |
| Williams %R | WilliamsR | 威廉指标 |

### 波动率指标

| 指标 | 类名 | 说明 |
|------|------|------|
| ATR | ATR | 平均真实波幅 |
| 标准差 | STD | 标准差 |

### 成交量指标

| 指标 | 类名 | 说明 |
|------|------|------|
| OBV | OBV | 能量潮 |
| 成交量 MA | VolumeMA | 成交量移动平均 |

---

## 💡 使用示例

### 示例 1: 均线组合

```python
from bobquant.indicator import MA

ma5 = MA(5)
ma10 = MA(10)
ma20 = MA(20)

for price in prices:
    ma5.update(price)
    ma10.update(price)
    ma20.update(price)
    
    # 金叉
    if ma5.value > ma10.value and ma5.prev_value <= ma10.prev_value:
        print("金叉信号")
    
    # 死叉
    if ma5.value < ma10.value and ma5.prev_value >= ma10.prev_value:
        print("死叉信号")
```

### 示例 2: MACD 策略

```python
from bobquant.indicator import MACD

macd = MACD(12, 26, 9)

for price in prices:
    macd.update(price)
    
    # 金叉
    if macd.dif > macd.dea and macd.prev_dif <= macd.prev_dea:
        print("买入信号")
    
    # 死叉
    if macd.dif < macd.dea and macd.prev_dif >= macd.prev_dea:
        print("卖出信号")
```

### 示例 3: RSI 超买超卖

```python
from bobquant.indicator import RSI

rsi = RSI(14)

for price in prices:
    rsi.update(price)
    
    if rsi.value < 30:
        print("超卖，买入信号")
    elif rsi.value > 70:
        print("超买，卖出信号")
```

### 示例 4: 布林带

```python
from bobquant.indicator import BollingerBands

bb = BollingerBands(period=20, std_dev=2)

for price in prices:
    bb.update(price)
    
    if price <= bb.lower:
        print("触及下轨，买入信号")
    elif price >= bb.upper:
        print("触及上轨，卖出信号")
```

---

## 🔧 TA-Lib 集成

### 安装 TA-Lib

```bash
# Ubuntu
sudo apt install libta-lib-dev
pip install ta-lib

# macOS
brew install ta-lib
pip install ta-lib

# Windows
# 下载预编译包安装
```

### 使用 TA-Lib

```python
from bobquant.indicator import TALib

talib = TALib()

# 重叠研究
sma = talib.SMA(close, timeperiod=20)
ema = talib.EMA(close, timeperiod=20)
wma = talib.WMA(close, timeperiod=20)

# 动量指标
rsi = talib.RSI(close, timeperiod=14)
macd, signal, hist = talib.MACD(close)
kdj_k, kdj_d = talib.STOCH(high, low, close)

# 波动率指标
atr = talib.ATR(high, low, close, timeperiod=14)
bb_upper, bb_middle, bb_lower = talib.BBANDS(close)

# 成交量指标
obv = talib.OBV(close, volume)
```

---

## 📚 相关文档

- [TA-Lib 高级用法](./TALIB_ADVANCED_USAGE.md)
- [策略示例](../docs/EXAMPLES.md)

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
