# BobQuant 数据模块

数据源管理、行情接口、历史数据。

---

## 📁 模块结构

```
data/
├── __init__.py              # 模块导出
├── provider.py              # 数据源抽象基类
├── tushare_provider.py      # Tushare 数据源
├── akshare_provider.py      # AkShare 数据源
├── yfinance_provider.py     # yfinance 数据源
└── tests/
    ├── test_tushare.py
    ├── test_akshare.py
    └── test_yfinance.py
```

---

## 🚀 快速开始

### 1. 获取行情数据

```python
from bobquant.data import get_market_data

df = get_market_data(
    symbol="600519.SH",
    interval="1d",
    start="2023-01-01",
    end="2023-12-31"
)

print(df.head())
```

### 2. 获取实时数据

```python
from bobquant.data import get_realtime_data

tick = get_realtime_data("600519.SH")

print(f"最新价：{tick['price']}")
print(f"涨跌幅：{tick['change']:.2%}")
```

### 3. 使用数据源

```python
from bobquant.data import TushareProvider

provider = TushareProvider(token="your_token")
df = provider.get_bar_data("600519.SH", "1d", "2023-01-01", "2023-12-31")
```

---

## 📖 数据源

### 1. Tushare

**特点**: 数据全面、稳定，需要 Token

```python
from bobquant.data import TushareProvider

# 初始化
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
tick = provider.get_realtime_data("600519.SH")
```

**配置**:
```json5
{
  "data": {
    "provider": "tushare",
    "tushare_token": "${env:TUSHARE_TOKEN}"
  }
}
```

### 2. AkShare

**特点**: 免费、开源，数据源丰富

```python
from bobquant.data import AkShareProvider

provider = AkShareProvider()

# 获取日线数据
df = provider.get_bar_data(
    symbol="600519",
    interval="1d",
    start="2023-01-01",
    end="2023-12-31"
)

# 获取实时行情
tick = provider.get_realtime_data("600519")
```

**配置**:
```json5
{
  "data": {
    "provider": "akshare"
  }
}
```

### 3. yfinance

**特点**: 适合美股、全球市场

```python
from bobquant.data import YfinanceProvider

provider = YfinanceProvider()

# 获取美股数据
df = provider.get_bar_data(
    symbol="AAPL",
    interval="1d",
    start="2023-01-01",
    end="2023-12-31"
)

# 获取实时行情
tick = provider.get_realtime_data("AAPL")
```

**配置**:
```json5
{
  "data": {
    "provider": "yfinance"
  }
}
```

---

## 💡 使用示例

### 示例 1: 批量获取数据

```python
from bobquant.data import get_market_data

symbols = ["600519.SH", "000858.SZ", "002415.SZ"]

for symbol in symbols:
    df = get_market_data(symbol, "1d", "2023-01-01", "2023-12-31")
    print(f"{symbol}: {len(df)}条数据")
```

### 示例 2: 数据缓存

```python
from bobquant.data import get_market_data

# 启用缓存
df = get_market_data(
    symbol="600519.SH",
    interval="1d",
    start="2023-01-01",
    end="2023-12-31",
    use_cache=True
)
```

### 示例 3: 数据预处理

```python
from bobquant.data import get_market_data
import pandas as pd

df = get_market_data("600519.SH", "1d", "2023-01-01", "2023-12-31")

# 处理缺失值
df = df.fillna(method='ffill')

# 计算收益率
df['return'] = df['close'].pct_change()

# 重采样
df_weekly = df.resample('W').last()
```

---

## 🔧 配置说明

### 数据源配置

```json5
{
  "data": {
    "provider": "tushare",  // 数据源：tushare | akshare | yfinance
    "cache_enabled": true,  // 启用缓存
    "cache_days": 7,        // 缓存天数
    "timeout": 30           // 超时时间 (秒)
  }
}
```

### Tushare 配置

```json5
{
  "data": {
    "provider": "tushare",
    "tushare_token": "${env:TUSHARE_TOKEN}",
    "tushare_api_url": "https://api.tushare.pro"
  }
}
```

---

## 📊 数据格式

### K 线数据

```python
# 标准列名
df.columns = [
    'open',      # 开盘价
    'high',      # 最高价
    'low',       # 最低价
    'close',     # 收盘价
    'volume',    # 成交量
    'amount',    # 成交额
    'datetime'   # 时间
]
```

### Tick 数据

```python
tick = {
    'symbol': '600519.SH',
    'price': 1800.0,
    'change': 0.02,
    'change_pct': 0.01,
    'volume': 1000000,
    'amount': 1800000000,
    'bid1': 1799.0,
    'ask1': 1801.0,
    'timestamp': '2023-01-01 10:00:00'
}
```

---

## 🐛 故障排查

### 问题 1: 数据获取失败

```python
# 检查数据源连接
from bobquant.data import get_market_data

try:
    df = get_market_data("600519.SH", "1d", "2023-01-01", "2023-01-31")
    print(df.head())
except Exception as e:
    print(f"错误：{e}")
```

### 问题 2: Tushare Token 无效

```bash
# 检查 Token
echo $TUSHARE_TOKEN

# 设置 Token
export TUSHARE_TOKEN="your_token"
```

---

## 📚 相关文档

- [Tushare 文档](./TUSHARE_README.md)
- [AkShare 文档](./AKSHARE_README.md)
- [yfinance 文档](./YFINANCE_README.md)

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
