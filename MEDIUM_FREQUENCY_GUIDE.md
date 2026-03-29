# 📊 中频交易模块使用指南

**版本**: v1.0  
**创建时间**: 2026-03-29  
**状态**: ✅ 已完成基础框架

---

## 🎯 功能概述

中频交易模块是在现有 V2 系统基础上新增的交易策略，特点：

| 指标 | 参数 |
|------|------|
| **交易频率** | 5-30 分钟调仓 |
| **持仓周期** | 1-5 天 |
| **策略类型** | 网格 + 波段 + 动量 |
| **数据源** | 新浪财经分钟线 |
| **延迟要求** | <500ms |

---

## 🏗️ 模块结构

```
medium_frequency/
├── __init__.py              # 模块初始化
├── data_fetcher.py          # 数据获取器 (新浪分钟线)
├── signal_generator.py      # 信号生成器 (3 种策略)
├── execution_engine.py      # 执行引擎
├── risk_monitor.py          # 风险监控器
└── config/
    └── mf_config.yaml       # 配置文件
```

---

## 🚀 快速开始

### 1. 模拟模式测试

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies

# 执行一次检查 (模拟模式)
python3 scripts/run_medium_frequency.py --once --dry-run
```

### 2. 实盘模式 (谨慎使用!)

```bash
# 先修改配置文件
vim medium_frequency/config/mf_config.yaml
# 设置：dry_run: false

# 启动交易循环
python3 scripts/run_medium_frequency.py
```

### 3. 后台运行

```bash
# 使用 nohup
nohup python3 scripts/run_medium_frequency.py > logs/mf.log 2>&1 &

# 查看进程
ps aux | grep medium_frequency

# 停止交易
pkill -f run_medium_frequency
```

---

## 📈 三种策略

### 1️⃣ 网格策略

**原理**: 价格每波动一定比例就买卖

**参数**:
```yaml
grid:
  grid_size: 0.015           # 网格间距 1.5%
  position_per_grid: 0.03    # 每格仓位 3%
  max_grids: 8               # 最多 8 格
```

**适用**: 震荡行情，波动率高的股票

---

### 2️⃣ 波段策略

**原理**: RSI 超卖 + MACD 金叉 → 买入

**参数**:
```yaml
swing:
  rsi_oversold: 30           # RSI<30 超卖
  rsi_overbought: 70         # RSI>70 超买
  macd_fast: 12
  macd_slow: 26
```

**适用**: 趋势行情，白酒/银行等

---

### 3️⃣ 动量策略

**原理**: 突破 20 周期高点 + 成交量放大 → 买入

**参数**:
```yaml
momentum:
  breakout_period: 20        # 突破周期
  volume_confirm: 1.5        # 成交量 1.5 倍
```

**适用**: 强势股，龙头股

---

## ⚙️ 配置说明

### 核心配置

```yaml
medium_frequency:
  check_interval: 300        # 5 分钟检查一次
  trading_hours:
    morning: "09:30-11:30"
    afternoon: "13:00-15:00"
  
  stock_pool:                # 15 只股票
    - code: "sh.603986"
      name: "兆易创新"
```

### 风控配置

```yaml
risk_control:
  max_position_per_stock: 0.10   # 单只≤10%
  max_total_position: 0.60       # 总仓位≤60%
  stop_loss: -0.03               # -3% 止损
  take_profit: 0.08              # +8% 止盈
  max_trades_per_day: 5          # 每日最多 5 笔
```

---

## 📊 监控指标

### 实时查看

```bash
# 查看最新日志
tail -f logs/medium_frequency.log

# 查看今日交易
cat sim_trading/交易记录.json | jq '.[] | select(.strategy | contains("grid") or contains("swing") or contains("momentum"))'
```

### 交易统计

```python
from medium_frequency.execution_engine import ExecutionEngine

engine = ExecutionEngine(...)
stats = engine.get_stats()

print(f"今日交易：{stats['today_trades']}笔")
print(f"今日盈亏：¥{stats['today_profit']:.2f}")
```

---

## ⚠️ 注意事项

### 1. 数据源限制
- 使用新浪财经 API，免费但非实时
- 可能有 100-200ms 延迟
- 不适合真正的高频交易

### 2. 交易成本
- 频繁交易手续费累积
- 每次交易成本约 0.06% (买卖双向)
- 网格间距要覆盖成本

### 3. 风险控制
- 建议先用模拟模式测试
- 设置严格的止损止盈
- 监控连续亏损

### 4. 适用场景
- ✅ 震荡行情 (网格策略)
- ✅ 趋势行情 (波段策略)
- ✅ 强势股 (动量策略)
- ❌ 单边暴跌 (所有策略都可能亏损)

---

## 🔧 故障排查

### 问题 1: 数据获取失败
```bash
# 测试 API
python3 -c "
from medium_frequency.data_fetcher import MinuteDataFetcher
f = MinuteDataFetcher()
df = f.get_minute_kline('sh.603986', period=5, limit=10)
print(df)
"
```

### 问题 2: 无交易信号
- 检查 K 线数据是否足够 (至少 30 条)
- 调整策略参数 (降低阈值)
- 可能是市场平静期

### 问题 3: 风控限制
```bash
# 查看风控日志
grep "风控" logs/medium_frequency.log
```

---

## 📝 下一步优化

### 短期 (1-2 周)
- [ ] 添加更多策略 (T+0、套利)
- [ ] 优化参数 (回测验证)
- [ ] 添加飞书通知

### 中期 (1 个月)
- [ ] 接入 Level-2 数据
- [ ] 优化延迟 (<100ms)
- [ ] 接入券商 API

### 长期 (3 个月)
- [ ] 机器学习预测
- [ ] 多账户管理
- [ ] 实盘验证

---

## 📞 支持

遇到问题？检查以下内容：

1. **配置文件**: `medium_frequency/config/mf_config.yaml`
2. **日志文件**: `logs/medium_frequency.log`
3. **交易记录**: `sim_trading/交易记录.json`

---

_最后更新：2026-03-29_  
_状态：基础框架完成，等待实盘测试_
