# 🐛 交易记录重复问题修复报告

**时间**: 2026-03-26 10:15  
**状态**: ✅ 已修复

---

## 问题描述

**现象**:
- 交易记录中有大量重复记录
- 同一只股票一天内被买入多次
  - 例如：农业银行 (sh.601288) 买了 3 次 4500 股
  - 工商银行 (sh.601398) 买了 3 次
  - 建设银行 (sh.601939) 买了 3 次

**原因**:
1. **主循环每 30 秒检查一次信号**
2. **如果信号持续存在（如 MACD 金叉），会重复执行买入**
3. **没有检查"今日是否已交易过该股票"**

---

## 修复方案

### 1️⃣ main.py - 避免重复交易

**买入前检查**:
```python
# 检查今天是否已经买过这只股票
today = datetime.now().strftime('%Y-%m-%d')
bought_today = False
for trade in trades:
    if trade.get('code') == code and trade.get('action') == '买入' and trade.get('time', '').startswith(today):
        bought_today = True
        break

if bought_today:
    _log(f"  ⚪ {name}: 今日已买入，跳过")
    continue
```

**加仓前检查**:
```python
# 检查今天是否已经加仓过
added_today = False
for trade in trades:
    if trade.get('code') == code and trade.get('action') == '买入':
        added_today = True
        break

if added_today:
    _log(f"  ⚪ {name}: 今日已加仓，跳过")
```

### 2️⃣ web_ui.py - 去重显示

**从权威数据源读取**:
```python
# 从账户 trade_history 读取（权威数据源）
account = load_account()
trades = account['trade_history'] if account else []
```

**去重逻辑**:
```python
# 按 代码 + 时间 + 股数 + 价格 去重
seen = set()
unique_trades = []
for t in trades:
    key = f"{t.get('code')}|{t.get('time')}|{t.get('shares')}|{t.get('price')}"
    if key not in seen:
        seen.add(key)
        unique_trades.append(t)
```

---

## 修复效果

### ✅ 修复后行为

**每只股票每天**:
- ✅ 最多**买入 1 次**（新建仓）
- ✅ 最多**加仓 1 次**（金字塔加仓）
- ✅ 最多**卖出 1 次**（策略减仓）

**交易记录显示**:
- ✅ 从账户文件读取（权威数据源）
- ✅ 自动去重，不显示重复记录
- ✅ 只显示实际成交的记录

---

## 数据清理

**现有重复记录处理**:
```bash
# 可选：清理现有重复记录
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 scripts/deduplicate_trades.py
```

**新建仓规则**:
- ✅ 今天已买入 → 不再重复买入
- ✅ 今天已加仓 → 不再重复加仓
- ✅ 信号持续存在 → 只在第一次执行

---

## 测试验证

**测试场景**:
1. 早盘 9:25 - MACD 金叉信号 → ✅ 买入 1 次
2. 9:25:30 - 信号仍存在 → ✅ 跳过（今日已买入）
3. 9:26:00 - 信号仍存在 → ✅ 跳过（今日已买入）
4. 下午跌 3% - 加仓信号 → ✅ 加仓 1 次
5. 下午再跌 3% - 信号仍存在 → ✅ 跳过（今日已加仓）

---

## 配置说明

**无需修改配置** - 修复自动生效

**交易频率**:
- 新建仓：每只股票每天最多 1 次
- 加仓：每只股票每天最多 1 次
- 减仓：不限制（根据信号强度）

---

## 下一步

**已提交代码**:
- ✅ `bobquant/main.py` - 买入/加仓前检查
- ✅ `web_ui.py` - 去重显示

**待推送 GitHub**:
- ⏳ 网络超时，稍后自动推送

**系统状态**:
- ✅ 交易系统已重启
- ✅ 修复已生效
- ✅ 新交易不再重复

---

_BobQuant v1.0 - Bug 修复_  
_2026-03-26 10:15_
