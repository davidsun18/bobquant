# Tushare 数据源使用指南

## 简介

Tushare 是专业的财经数据接口库，提供 A 股、港股、美股、基金、期货、数字货币等市场的行情、财务、交易数据。

官网：https://tushare.pro

## 特点

- ✅ 数据质量高，更新及时
- ✅ 接口稳定，支持并发
- ✅ 覆盖 A 股全市场数据
- ✅ 提供丰富的财务、基本面数据
- ⚠️ 需要注册获取 token
- ⚠️ 部分高级接口需要积分

## 快速开始

### 1. 安装依赖

```bash
pip3 install tushare
```

### 2. 获取 Token

1. 访问 https://tushare.pro 注册账号
2. 登录后在个人中心获取 API Token
3. 初始注册赠送 100 积分，可满足基础数据需求

### 3. 设置 Token

**方式一：环境变量 (推荐)**
```bash
export TUSHARE_TOKEN='your_token'
```

**方式二：代码中传入**
```python
from data.provider import get_provider

provider = get_provider('tushare', token='your_token')
```

## 使用示例

### 获取实时行情

```python
from data.provider import get_provider

# 创建 Tushare 数据源
provider = get_provider('tushare', token='your_token', retry=3)

# 获取单只股票行情
quote = provider.get_quote('600519.SH')
print(f"贵州茅台：{quote['current']}元，涨跌幅：{quote['change']:+.2f}%")

# 批量获取多只股票
quotes = provider.get_quotes(['600519.SH', '000001.SZ', '601318.SH'])
for code, data in quotes.items():
    print(f"{code}: {data['current']}元")
```

### 获取历史 K 线

```python
# 获取 60 天历史数据
df = provider.get_history('600519.SH', days=60)

print(df.head())
print(f"最新收盘价：{df['close'].iloc[-1]:.2f}元")
```

### 获取财务数据

```python
financial = provider.get_financial_data('600519.SH')
print(f"市盈率：{financial['pe']}")
print(f"市净率：{financial['pb']}")
print(f"净资产收益率：{financial['roe']:.2f}%")
```

### 获取股票基本信息

```python
info = provider.get_stock_info('600519.SH')
print(f"名称：{info['name']}")
print(f"地区：{info['area']}")
print(f"行业：{info['industry']}")
print(f"上市日期：{info['list_date']}")
```

## 支持的数据类型

| 方法 | 功能 | 数据内容 |
|------|------|----------|
| `get_quote(code)` | 实时行情 | 名称、当前价、开盘价、昨收价、最高、最低、涨跌幅、成交量 |
| `get_history(code, days)` | 历史 K 线 | 日期、开盘、最高、最低、收盘、成交量 |
| `get_quotes(codes)` | 批量行情 | 多只股票的实时行情字典 |
| `get_financial_data(code)` | 财务数据 | PE、PB、EPS、ROE、总资产、总负债、净利润 |
| `get_stock_info(code)` | 股票信息 | 名称、地区、行业、市场、上市日期、总股本、流通股本 |

## 股票代码格式

Tushare 使用以下格式：
- 上交所股票：`600519.SH`
- 深交所股票：`000001.SZ`

Provider 会自动转换常见格式：
- `sh600519` → `600519.SH`
- `sz000001` → `000001.SZ`
- `600519` → `600519.SH` (自动识别市场)

## 测试

运行测试脚本验证数据源：

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant/data
export TUSHARE_TOKEN='your_token'
python3 test_tushare.py
```

## 注意事项

1. **Token 安全**: 不要将 token 提交到代码仓库，建议使用环境变量
2. **积分限制**: 部分高级接口需要一定积分才能调用
3. **调用频率**: 建议设置 delay >= 1 秒避免触发频率限制
4. **网络环境**: 确保能访问 tushare.pro API

## 与其他数据源对比

| 特性 | Tushare | AkShare | 腾讯财经 |
|------|---------|---------|----------|
| 数据质量 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 稳定性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| 覆盖范围 | A 股为主 | 全市场 | A 股 |
| 是否需要 token | 是 | 否 | 否 |
| 财务数据 | 丰富 | 一般 | 无 |
| 实时性 | 高 | 高 | 高 |

## 故障排查

### 问题 1: 获取数据返回 None

**原因**: Token 未设置或无效

**解决**: 
```bash
export TUSHARE_TOKEN='your_token'
```

### 问题 2: 积分不足

**原因**: 部分接口需要一定积分

**解决**: 
- 签到获取积分 (每日 +10)
- 完善个人信息
- 贡献社区

### 问题 3: 调用频率过高

**原因**: 短时间内请求过多

**解决**: 
- 增加 delay 参数
- 使用批量接口 `get_quotes` 代替多次 `get_quote`

## 参考资料

- Tushare 官方文档：https://tushare.pro/document/2
- 接口积分说明：https://tushare.pro/document/1?doc_id=13
- GitHub: https://github.com/waditu/tushare
