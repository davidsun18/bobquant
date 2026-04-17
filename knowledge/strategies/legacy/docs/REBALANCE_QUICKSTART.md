# 🔄 自动调仓快速入门

## 📌 30 秒快速开始

### 1️⃣ 启用调仓（30 秒）

编辑配置文件：
```bash
nano bobquant/config/settings.yaml
```

找到 `rebalance:` 部分，修改：
```yaml
rebalance:
  enabled: true              # ← 改为 true
  mode: "equal_weight"       # 等权重调仓
  frequency: "weekly"        # 每周一调仓
  rebalance_day: 0           # 0=周一
  threshold_pct: 0.05        # 偏离 5% 触发
  stock_pool: []             # 为空则使用主股票池
```

### 2️⃣ 重启 BobQuant

```bash
cd bobquant
./start_sim_v2_2.sh
```

### 3️⃣ 查看调仓日志

```bash
tail -f bobquant/logs/sim_trading/模拟盘日志.log
```

---

## 🎯 常用配置场景

### 场景 1: 等权重调仓（推荐新手）

```yaml
rebalance:
  enabled: true
  mode: "equal_weight"
  frequency: "weekly"
  rebalance_day: 0           # 每周一
  threshold_pct: 0.05        # 偏离 5% 才调仓
```

**效果**: 每周一检查，如果某只股票仓位偏离超过 5%，自动调回平均权重。

---

### 场景 2: 目标仓位调仓（进阶）

```yaml
rebalance:
  enabled: true
  mode: "target_weight"
  frequency: "monthly"
  rebalance_day: 1           # 每月 1 日
  threshold_pct: 0.10        # 偏离 10% 才调仓
  target_positions:
    sh.600000: 0.30          # 浦发银行 30%
    sh.600036: 0.30          # 招商银行 30%
    sz.000001: 0.25          # 平安银行 25%
    sz.000002: 0.15          # 万科 A 15%
```

**效果**: 每月 1 日检查，自动调整到目标仓位比例。

---

### 场景 3: 保守调仓（低频）

```yaml
rebalance:
  enabled: true
  mode: "equal_weight"
  frequency: "monthly"
  rebalance_day: 25          # 每月 25 日
  threshold_pct: 0.15        # 偏离 15% 才调仓
  min_trade_value: 5000      # 最小交易 5000 元
```

**效果**: 每月调仓一次，减少交易频率和成本。

---

### 场景 4: 积极调仓（高频）

```yaml
rebalance:
  enabled: true
  mode: "equal_weight"
  frequency: "daily"
  threshold_pct: 0.03        # 偏离 3% 就调仓
  min_trade_value: 1000      # 最小交易 1000 元
```

**效果**: 每日检查调仓，保持仓位精确匹配目标。

⚠️ **注意**: 高频调仓会增加交易成本，请谨慎使用。

---

## 📊 调仓示例

### 等权重调仓示例

**初始状态**:
- 总资产：¥1,000,000
- 持仓：
  - 股票 A: ¥600,000 (60%)
  - 股票 B: ¥200,000 (20%)
  - 股票 C: ¥0 (0%)
  - 股票 D: ¥0 (0%)
- 现金：¥200,000

**目标配置** (等权重):
- 每只股票 25% = ¥250,000

**调仓订单**:
1. 🔴 卖出 股票 A 35,000 股 @ ¥10 = ¥350,000
2. 🟢 买入 股票 B 1,428 股 @ ¥35 = ¥50,000
3. 🟢 买入 股票 C 4,166 股 @ ¥12 = ¥50,000
4. 🟢 买入 股票 D 2,000 股 @ ¥25 = ¥50,000

**调仓后**:
- 每只股票约 25%
- 现金剩余约¥0

---

## ⚠️ 常见问题

### Q1: 为什么没有触发调仓？

**检查清单**:
- [ ] `enabled` 是否为 `true`
- [ ] 是否到调仓日（周一/每月 1 日）
- [ ] 偏离度是否超过阈值

**解决方法**:
```bash
# 查看调仓状态
cat bobquant/logs/rebalance_state.json

# 手动测试
python3 tests/test_rebalance.py
```

---

### Q2: 调仓失败怎么办？

**可能原因**:
1. 现金不足
2. T+1 限制（今日买入不可卖）
3. 股票停牌

**解决方法**:
- 等待下一调仓日
- 手动调整仓位
- 检查股票状态

---

### Q3: 调仓成本太高？

**优化建议**:
1. 提高阈值（如 5% → 10%）
2. 降低频率（如 weekly → monthly）
3. 提高最小交易金额

```yaml
rebalance:
  threshold_pct: 0.10        # 提高阈值
  frequency: "monthly"       # 降低频率
  min_trade_value: 5000      # 提高最小交易金额
```

---

### Q4: 如何查看调仓历史？

```bash
# 查看调仓状态文件
cat bobquant/logs/rebalance_state.json

# 查看日志
grep "调仓" bobquant/logs/sim_trading/模拟盘日志.log
```

---

## 🔧 高级技巧

### 技巧 1: 临时关闭调仓

```yaml
rebalance:
  enabled: false  # 临时关闭
```

重启 BobQuant 即可生效。

---

### 技巧 2: 调整调仓日

```yaml
# 改为每周五调仓
rebalance:
  frequency: "weekly"
  rebalance_day: 4  # 4=周五
```

---

### 技巧 3: 自定义股票池

```yaml
rebalance:
  stock_pool:  # 只调仓这 4 只
    - sh.600000
    - sh.600036
    - sz.000001
    - sz.000002
```

---

### 技巧 4: 查看调仓摘要

在 Python 中：
```python
from bobquant.strategy.rebalance import create_rebalance_engine

engine = create_rebalance_engine(config)
summary = engine.get_rebalance_summary()
print(summary)
```

---

## 📈 最佳实践

### ✅ 推荐配置

```yaml
rebalance:
  enabled: true
  mode: "equal_weight"
  frequency: "weekly"
  rebalance_day: 0           # 周一
  threshold_pct: 0.05        # 5%
  min_trade_value: 1000      # ¥1000
  respect_t1: true
  notify_enabled: true
```

**优点**:
- 每周检查一次，频率适中
- 5% 阈值过滤不必要的交易
- 遵守 T+1 规则
- 飞书通知及时知晓

---

### ❌ 避免的配置

```yaml
# 避免：过于频繁
rebalance:
  frequency: "daily"
  threshold_pct: 0.01  # 1% 就调仓 → 成本太高！

# 避免：过于复杂
rebalance:
  mode: "target_weight"
  target_positions:
    stock1: 0.123  # 过于精确，难以维护
    stock2: 0.456
```

---

## 📞 获取帮助

### 文档

- 完整文档：`bobquant/docs/REBALANCE_STRATEGY.md`
- 实现总结：`quant_strategies/REBALANCE_IMPLEMENTATION_SUMMARY.md`

### 测试

```bash
cd bobquant
python3 tests/test_rebalance.py
```

### 日志

```bash
tail -f bobquant/logs/sim_trading/模拟盘日志.log | grep 调仓
```

---

## 🎓 学习路径

1. **入门**: 使用等权重 + 周频调仓
2. **进阶**: 尝试目标仓位调仓
3. **高级**: 自定义调仓策略
4. **专家**: 修改 rebalance.py 源码

---

_快速入门指南 | 版本 v1.0 | 2026-04-11_
