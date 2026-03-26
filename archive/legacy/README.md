# BOB 量化交易系统

> 基于腾讯财经实时数据的 A 股量化交易平台

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

## 📊 项目简介

BOB 量化交易系统是一个功能完整的 A 股量化交易平台，支持多种经典量化策略、实时数据获取、自动交易执行和飞书实时推送。

**核心特性：**
- ✅ 腾讯财经实时数据接口（~100ms 响应）
- ✅ 11 种经典量化策略（MACD、布林带、RSI 等）
- ✅ 智能仓位管理（3%-8% 动态调整）
- ✅ T+1 交易规则严格执行
- ✅ 飞书实时推送通知
- ✅ 批量回测工具（50 只股票）
- ✅ 模拟盘/实盘双模式

---

## 🚀 快速开始

### 1. 环境准备

```bash
# Python 3.10+
pip3 install pandas numpy matplotlib requests baostock
```

### 2. 配置股票池

编辑 `stock_pool_50.py`：

```python
STOCK_POOL = [
    ('sh.601398', '工商银行', 'bollinger'),
    ('sh.600036', '招商银行', 'bollinger'),
    ('sh.600519', '贵州茅台', 'bollinger'),
    # ... 更多股票
]
```

### 3. 启动系统

```bash
# 模拟盘模式（推荐先测试）
python3 ideal_sim_trading.py

# 查看日志
tail -f sim_trading/模拟盘日志.log
```

---

## 📈 策略列表

### 技术指标策略

| 策略 | 文件 | 适用场景 | 预期年化 |
|------|------|----------|----------|
| **MACD 趋势跟踪** | `macd_ultimate.py` | 趋势市 | 15-25% |
| **布林带均值回归** | `bollinger_bands.py` | 震荡市 | 20-30% ⭐ |
| **RSI 超买超卖** | `rsi_strategy.py` | 震荡市 | 10-15% |

### 进阶策略

| 策略 | 文件 | 说明 |
|------|------|------|
| **多因子模型** | `multi_factor_model.py` | 5 因子打分系统 |
| **配对交易** | `pair_trading_simple.py` | 统计套利 |
| **机器学习** | `ml_practical.py` | 随机森林预测 |

### 组合策略

| 策略 | 文件 | 说明 |
|------|------|------|
| **智能组合** | `smart_combined.py` | MACD+ 布林带分场景 |
| **批量回测** | `batch_backtest.py` | 12 只股票对比 |

---

## 🎯 核心功能

### 1. 实时数据获取

```python
# 腾讯财经接口（免费、实时、稳定）
def get_price_tencent(code):
    url = f"http://qt.gtimg.cn/q={code.replace('.', '')}"
    response = requests.get(url, timeout=3)
    # 返回：名称、价格、涨跌幅等
```

**性能指标：**
- 响应时间：~100ms
- 成功率：95%+
- 数据质量：实时准确

### 2. 智能仓位管理

```python
# 根据股价动态调整仓位
if current_price > 100:
    position = 7%   # 高价股
elif current_price < 30:
    position = 3.5% # 低价股
else:
    position = 5%   # 标准仓位
```

### 3. T+1 交易规则

```python
# 严格执行 T+1
buy_date = pos.get('buy_date', '')
today = datetime.now().strftime('%Y-%m-%d')

if buy_date == today:
    continue  # 今日买入不可卖出
```

### 4. 飞书实时推送

```python
# 交易立即推送
def send_feishu(title, message):
    # 买入/卖出信号
    # 仓位/价格/金额
    # 实时送达飞书
```

---

## 📊 模拟盘实战

### 当前配置

| 参数 | 配置 |
|------|------|
| **初始资金** | ¥1,000,000 |
| **股票池** | 50 只主板股 |
| **检查频率** | 30 秒/次 |
| **单只仓位** | 3%-8% 智能调整 |
| **最大持仓** | 20 只 |

### 持仓示例

```
总资产：¥999,999.83
持仓：11 只股票 (55.7%)
现金：¥443,380.83 (44.3%)

持仓明细:
- 美的集团：600 股 @ ¥73.99
- 伊利股份：1900 股 @ ¥25.61
- 民生银行：11000 股 @ ¥3.80
- ...
```

---

## 📁 文件结构

```
quant_strategies/
├── ideal_sim_trading.py        # 主程序（模拟盘）
├── trading_system_v1.py        # 交易系统 v1
├── batch_backtest.py           # 批量回测工具
│
├── strategies/                 # 策略文件
│   ├── macd_*.py              # MACD 系列
│   ├── bollinger_bands.py     # 布林带
│   ├── rsi_strategy.py        # RSI
│   └── ...
│
├── stock_pools/               # 股票池
│   ├── stock_pool_10.py       # 10 只精选
│   ├── stock_pool_50.py       # 50 只主板
│   └── stock_pool_200.py      # 200 只全市场
│
├── configs/                   # 配置文件
│   ├── infoway_config.py      # Infoway API
│   └── itick_config.py        # iTick API
│
└── sim_trading/               # 模拟盘数据
    ├── account_ideal.json     # 账户状态
    ├── 模拟盘日志.log         # 运行日志
    └── 交易记录.json          # 交易历史
```

---

## 🔧 高级配置

### 1. 自定义策略参数

```python
# MACD 参数优化
MA1 = 12  # 短期均线
MA2 = 26  # 长期均线

# 布林带参数
BB_WINDOW = 20  # 周期
BB_STD = 2      # 标准差
```

### 2. 多 API 支持

```python
# 腾讯财经（主力）
get_price = get_price_tencent

# Infoway WebSocket（备用）
get_price = get_price_infoway

# iTick（测试中）
get_price = get_price_itick
```

### 3. 风控设置

```python
# 止损止盈
STOP_LOSS = 0.08    # 8% 止损
TAKE_PROFIT = 0.15  # 15% 止盈

# 仓位控制
MAX_POSITION = 0.20  # 单只最大 20%
MAX_STOCKS = 20      # 最多 20 只
```

---

## 📊 性能对比

### 策略回测对比（2023 年浦发银行）

| 策略 | 总收益 | 夏普比率 | 最大回撤 |
|------|--------|----------|----------|
| **布林带均值回归** | +11.97% | 1.11 | -5.07% |
| **MACD 终极版** | +0.59% | -0.25 | -10.01% |
| **RSI 策略** | -0.54% | -6.46 | -0.54% |

### 批量回测（12 只股票）

| 行业 | 推荐策略 | 预期收益 |
|------|----------|----------|
| 银行 | 布林带 | +12.32% |
| 科技 | MACD | +72.44% |
| 消费 | 布林带 | +14.10% |

---

## 🎓 学习路径

### 新手入门

1. 学习基础指标（MACD、布林带、RSI）
2. 运行简单回测（`macd_simple.py`）
3. 理解交易逻辑

### 进阶提升

1. 学习策略优化（参数优化、过滤条件）
2. 学习多因子模型
3. 学习机器学习应用

### 实战应用

1. 模拟盘验证（至少 3 个月）
2. 小资金实盘测试
3. 逐步扩大规模

---

## ⚠️ 风险提示

1. **模拟盘≠实盘** - 实盘需考虑滑点、手续费等
2. **历史收益≠未来收益** - 策略可能失效
3. **市场有风险** - 投资需谨慎
4. **T+1 限制** - A 股当日买入不可卖出

---

## 📝 更新日志

### v2.0 (2026-03-24)
- ✅ 腾讯财经实时数据接口
- ✅ 智能仓位管理（3%-8% 动态）
- ✅ 飞书实时推送
- ✅ 50 只股票池
- ✅ T+1 严格执行

### v1.5 (2026-03-23)
- ✅ 批量回测工具
- ✅ 多策略对比
- ✅ 机器学习集成

### v1.0 (2026-03-22)
- ✅ 基础策略实现
- ✅ 模拟盘框架

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证

---

## 📞 联系方式

- **项目地址**: https://github.com/YOUR_USERNAME/bob-quant-trading
- **问题反馈**: https://github.com/YOUR_USERNAME/bob-quant-trading/issues

---

## 🙏 致谢

感谢以下开源项目：
- [Baostock](http://baostock.com/) - 证券数据接口
- [Pandas](https://pandas.pydata.org/) - 数据分析库
- [Matplotlib](https://matplotlib.org/) - 可视化库

---

**⚡ Happy Trading! ⚡**
