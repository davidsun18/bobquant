# 🤖 自动执行设置完成

**设置时间**: 2026-03-28 12:35 (周六)  
**首次执行**: 2026-03-31 09:00 (周一)  
**状态**: ✅ 已激活

---

## ⏰ 定时任务

### 已设置 Cron 任务

```bash
# 每个交易日执行 2 次
0 9 * * 1-5   # 早上 9 点 (开盘前)
0 14 * * 1-5  # 下午 2 点 (盘中)
```

**执行内容**:
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 auto_trade_v2.py >> logs/auto_trade.log 2>&1
```

---

## 📋 自动执行流程

### 阶段 1: 减仓 (周一 09:30-10:00)

**自动卖出**:
```
❌ 今世缘 (sh.603198) - 400 股
❌ 同仁堂 (sh.600436) - 300 股
❌ 其他非划分股票
```

**预计回笼**: ~2 万

---

### 阶段 2: V2 建仓 (周一 10:00-11:00)

**第 1 批 (30% 资金)**:
```
✅ 兆易创新 (sh.603986) - 2500 股 (目标价<95)
✅ 北方华创 (sz.002371) - 600 股 (目标价<360)
✅ 海康威视 (sz.002415) - 6000 股 (目标价<40)
✅ 宁德时代 (sz.300750) - 1200 股 (目标价<185)
```

**条件**:
- 价格 < 目标价
- 信号评分 ≥ 70
- 资金充足

---

### 阶段 3: 风控检查 (每日执行)

**检查项目**:
```
✅ 总仓位 ≤ 80%
✅ 单只股票 ≤ 15%
✅ 现金储备 ≥ 20%
✅ 无重叠股票
```

---

## 📊 监控方式

### 1. 日志文件
```
位置：/home/openclaw/.openclaw/workspace/quant_strategies/logs/auto_trade.log

查看命令:
tail -f logs/auto_trade.log
```

### 2. 账户文件
```
位置：/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json

实时更新持仓和现金
```

### 3. 交易记录
```
位置：/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json

记录所有买卖交易
```

---

## ⚠️ 安全措施

### 1. 交易时间检查
```python
# 周末不执行
if now.weekday() >= 5:
    return "周末休市"

# 非交易时间不执行
if now.hour < 9 or now.hour >= 15:
    return "非交易时间"
```

### 2. 价格验证
```python
# 获取实时价格
price = get_realtime_price(code)
if not price:
    print("无法获取价格，跳过")
    continue
```

### 3. 资金检查
```python
# 确保不超买
if required_cash > cash_available * 0.3:
    print("资金不足，跳过")
    continue
```

### 4. 仓位限制
```python
# 总仓位不超过 80%
if position_ratio > 0.80:
    print("仓位超限，暂停买入")
    return False
```

---

## 📅 执行时间表

### 下周一 (03-31)
```
09:00 - 第 1 次自动检查
09:30 - 开盘，开始减仓
10:00 - V2 第 1 批建仓
14:00 - 第 2 次自动检查
14:30 - V2 第 2 批建仓 (如有资金)
15:00 - 收盘检查
```

### 下周二 - 周五 (04-01 ~ 04-04)
```
09:00 - 自动检查信号
14:00 - 自动建仓/调仓
15:00 - 收盘风控检查
```

---

## 🎯 预期进度

### Day 1 (03-31 周一)
- ✅ 完成减仓 (回笼 2 万)
- ✅ V2 建仓 30-50% (约 15-25 万)
- ✅ 总仓位 55-75%

### Day 2-3 (04-01 ~ 04-02)
- ✅ V2 建仓 60-80%
- ✅ 观察现有策略网格做 T

### Day 4-5 (04-03 ~ 04-04)
- ✅ V2 建仓完成 (80-100%)
- ✅ 两个策略并行运行
- ✅ 周末总结

---

## 📞 通知机制

### 自动记录
所有交易自动记录到:
- `logs/auto_trade.log`
- `sim_trading/交易记录.json`

### 手动检查
```bash
# 查看最新日志
tail -50 logs/auto_trade.log

# 查看持仓
cat sim_trading/account_ideal.json | jq .positions

# 查看现金
cat sim_trading/account_ideal.json | jq .cash
```

---

## ⚙️ 手动控制

### 暂停自动交易
```bash
# 注释掉 cron 任务
crontab -e
# 在行首添加 #
# 0 9 * * 1-5 ...
# 0 14 * * 1-5 ...
```

### 手动执行一次
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 auto_trade_v2.py
```

### 查看执行历史
```bash
cat logs/auto_trade.log
```

---

## 📁 相关文件

| 文件 | 说明 | 位置 |
|------|------|------|
| `auto_trade_v2.py` | 自动交易脚本 | `quant_strategies/` |
| `v2_strategy_config.yaml` | V2 配置 | `bobquant_v2/config/` |
| `account_ideal.json` | 账户数据 | `sim_trading/` |
| `交易记录.json` | 交易历史 | `sim_trading/` |
| `auto_trade.log` | 执行日志 | `logs/` |

---

## ✅ 设置确认

- [x] 自动交易脚本创建 ✅
- [x] Cron 定时任务设置 ✅
- [x] 日志文件准备 ✅
- [x] 风控措施配置 ✅
- [x] 股票池划分 ✅
- [x] V2 配置文件 ✅

---

## 🚀 状态

**当前状态**: ⏸️ 等待周一开盘

**首次执行**: 2026-03-31 09:00 (周一)

**监控命令**:
```bash
# 实时查看执行日志
tail -f logs/auto_trade.log
```

---

_设置完成：2026-03-28 12:35_  
_自动执行：2026-03-31 09:00 (周一)_  
_祝交易顺利！📈_
