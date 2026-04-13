# yfinance 数据源使用指南

## 概述

yfinance 数据源已集成到 BobQuant，支持美股、港股、A 股数据获取。

**注意：yfinance 有严格的速率限制**，建议在生产环境中使用付费 API 或添加缓存机制。

## 安装

```bash
pip3 install yfinance
```

## 快速开始

### 1. 基础使用

```python
from data.provider import get_provider

# 获取 yfinance 数据源实例
provider = get_provider('yfinance', retry=3, delay=3.0)

# 获取实时行情
quote = provider.get_quote('AAPL')
print(quote)
# 输出：{'name': 'Apple Inc.', 'current': 175.43, 'open': 174.20, ...}

# 获取历史数据 (60 天)
df = provider.get_history('AAPL', days=60)
print(df.head())

# 批量获取
quotes = provider.get_quotes(['AAPL', 'MSFT', 'GOOGL'])
```

### 2. 股票代码格式

| 市场 | 格式示例 | yfinance 格式 |
|------|---------|--------------|
| 美股 | `AAPL`, `GOOGL` | `AAPL`, `GOOGL` |
| A 股 (上证) | `sh600519` | `600519.SS` |
| A 股 (深证) | `sz000001` | `000001.SZ` |
| 港股 | `hk00700` | `0700.HK` |

### 3. 参数配置

```python
provider = get_provider('yfinance', 
    retry=3,      # 重试次数
    timeout=30,   # 超时时间 (秒)
    delay=3.0     # 请求间隔 (秒)，建议 >= 3 避免速率限制
)
```

## 返回数据格式

### get_quote() 返回值

```python
{
    'name': 'Apple Inc.',        # 股票名称
    'current': 175.43,           # 当前价格
    'open': 174.20,              # 开盘价
    'pre_close': 173.50,         # 昨收价
    'high': 176.00,              # 最高价
    'low': 173.80,               # 最低价
    'change': 1.11,              # 涨跌幅 (%)
    'volume': 52340000           # 成交量
}
```

### get_history() 返回值

```python
# pandas DataFrame，索引为日期
              open     high      low    close     volume
date                                                    
2024-01-02  174.20  176.00   173.80   175.43  52340000
2024-01-03  175.50  177.20   174.90   176.80  48920000
...
```

## 速率限制说明

yfinance 对频繁请求有限制：

- **症状**: `Too Many Requests. Rate limited.`
- **解决**:
  1. 增加 `delay` 参数 (建议 3-5 秒)
  2. 减少重试次数
  3. 等待 1-2 分钟后重试
  4. 使用缓存避免重复请求
  5. 生产环境考虑使用付费 API (如 Alpha Vantage, Polygon)

## 最佳实践

### 1. 添加缓存

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedYFinanceProvider(YFinanceProvider):
    def __init__(self, *args, cache_ttl=300, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache_ttl = cache_ttl
        self._quote_cache = {}
    
    def get_quote(self, code):
        # 检查缓存
        if code in self._quote_cache:
            cached_time, cached_data = self._quote_cache[code]
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                return cached_data
        
        # 获取新数据
        quote = super().get_quote(code)
        if quote:
            self._quote_cache[code] = (datetime.now(), quote)
        return quote
```

### 2. 批量获取优化

```python
# 批量获取时添加延迟
codes = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
provider = get_provider('yfinance', delay=3.0)

for i, code in enumerate(codes):
    quote = provider.get_quote(code)
    if i < len(codes) - 1:
        time.sleep(3)  # 避免速率限制
```

### 3. 错误处理

```python
try:
    quote = provider.get_quote('AAPL')
    if quote:
        print(f"价格：{quote['current']}")
    else:
        print("获取失败，稍后重试")
except Exception as e:
    print(f"错误：{e}")
```

## 测试

运行测试脚本：

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python3 data/test_yfinance.py
```

## 与其他数据源对比

| 特性 | yfinance | 腾讯财经 |
|------|---------|---------|
| 覆盖市场 | 全球 (美/港/A 股) | 主要 A 股 |
| 实时性 | 延迟 15 分钟 | 实时 |
| 速率限制 | 严格 | 较宽松 |
| 历史数据 | 完整 | 有限 |
| 稳定性 | 中等 | 高 |
| 推荐场景 | 回测、研究 | 实盘交易 |

## 故障排查

### 问题 1: Too Many Requests

**原因**: 请求过于频繁

**解决**:
- 增加 delay 参数
- 等待 1-2 分钟
- 使用缓存

### 问题 2: 数据为空

**原因**: 股票代码错误或市场休市

**解决**:
- 检查代码格式 (如 sh600519)
- 确认交易时间

### 问题 3: 导入错误

**原因**: yfinance 未安装

**解决**:
```bash
pip3 install yfinance
```

## 参考链接

- yfinance GitHub: https://github.com/ranaroussi/yfinance
- Yahoo Finance: https://finance.yahoo.com/
