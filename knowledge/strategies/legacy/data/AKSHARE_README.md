# BobQuant AkShare 数据源

## 概述

AkShare 数据源提供 A 股市场的实时行情、历史 K 线、财务数据和资金流向数据。数据来源于新浪财经和东方财富网。

## 安装

AkShare 已预装：
```bash
pip3 install akshare  # 版本 1.18.44
```

## 使用方法

### 1. 基本使用

```python
from data.provider import get_provider

# 获取 AkShare 数据源实例
provider = get_provider('akshare', retry=3, delay=1.0)

# 获取实时行情
quote = provider.get_quote('sh600519')
print(f"贵州茅台：{quote['current']}元 ({quote['change']:+.2f}%)")

# 获取历史数据 (30 天)
df = provider.get_history('sh600519', days=30)
print(f"最新收盘价：{df['close'].iloc[-1]}元")

# 批量获取行情
quotes = provider.get_quotes(['sh600519', 'sz000001', 'sh601318'])
```

### 2. 高级功能

```python
# 获取财务数据
financial = provider.get_financial_data('sh600519')
print(f"市盈率：{financial['pe']}, 市净率：{financial['pb']}")

# 获取资金流向
flow = provider.get_money_flow('sh600519', days=10)
print(f"主力净流入：{flow['net_flow'].iloc[-1]}万元")
```

## 支持的数据类型

| 功能 | 方法 | 说明 |
|------|------|------|
| 实时行情 | `get_quote(code)` | 获取单只股票实时行情 |
| 批量行情 | `get_quotes(codes)` | 批量获取多只股票行情 |
| 历史 K 线 | `get_history(code, days)` | 获取历史日线数据 (前复权) |
| 财务数据 | `get_financial_data(code)` | 获取 PE、PB、EPS、ROE 等指标 |
| 资金流向 | `get_money_flow(code, days)` | 获取主力资金流向数据 |

## 股票代码格式

- **沪市 A 股**: `sh600519` 或 `600519` (自动添加前缀)
- **深市 A 股**: `sz000001` 或 `000001` (自动添加前缀)
- 支持不带市场前缀的代码，会自动识别

## 性能优化建议

1. **批量获取**: 使用 `get_quotes()` 而非多次调用 `get_quote()`
2. **缓存数据**: AkShare 每次获取全量 A 股数据，建议缓存结果
3. **合理延迟**: 设置 `delay=1.0` 避免过于频繁的请求
4. **重试机制**: 设置 `retry=3` 应对临时网络问题

## 注意事项

1. **网络依赖**: 需要访问中国大陆地区的数据源
2. **数据延迟**: 实时行情有 15 分钟延迟
3. **交易时间**: 仅在交易时段 (9:30-11:30, 13:00-15:00) 有实时数据
4. **速率限制**: 建议控制请求频率，避免被封 IP

## 测试

运行测试脚本验证功能：
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python3 data/test_akshare_quick.py
```

## 数据源对比

| 特性 | AkShare | Tencent | yfinance |
|------|---------|---------|----------|
| A 股支持 | ✓ | ✓ | ✓ |
| 港股支持 | ✗ | ✗ | ✓ |
| 美股支持 | ✗ | ✗ | ✓ |
| 财务数据 | ✓ | ✗ | ✓ |
| 资金流向 | ✓ | ✗ | ✗ |
| 响应速度 | 慢 (30-60s) | 快 (<1s) | 中 (2-5s) |
| 稳定性 | 中 | 高 | 高 |

## 故障排查

### 常见问题

**Q: 连接超时/失败**
- A: 检查网络连接，确认能访问东方财富网 (quote.eastmoney.com)

**Q: 数据获取慢**
- A: AkShare 需要获取全量 A 股数据后筛选，首次调用较慢属正常现象

**Q: 返回数据为空**
- A: 检查股票代码格式，确认是有效的 A 股代码

## 参考链接

- [AkShare 官方文档](https://akshare.akfamily.xyz/)
- [新浪财经](http://vip.stock.finance.sina.com.cn/)
- [东方财富网](https://quote.eastmoney.com/)
