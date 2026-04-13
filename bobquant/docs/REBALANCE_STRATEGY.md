# 🔄 BobQuant 自动调仓策略 v1.0

## 📋 概述

自动调仓策略是 BobQuant v2.5 新增的核心功能，用于定期自动调整投资组合仓位，确保实际仓位与目标配置保持一致。

### 核心功能

- ✅ **定期调仓**: 支持每日/每周/每月调仓
- ✅ **等权重调仓**: 所有股票平均分配仓位
- ✅ **目标仓位调仓**: 自定义每只股票的目标仓位比例
- ✅ **调仓阈值**: 只有偏离度超过阈值才触发（默认 5%）
- ✅ **自动生成订单**: 智能生成买卖订单，优化交易顺序
- ✅ **交易成本考虑**: 计算佣金、印花税、滑点
- ✅ **T+1 限制**: 自动遵守 A 股 T+1 交易规则
- ✅ **无缝集成**: 与现有交易引擎完美集成

---

## 🎯 调仓模式

### 1. 等权重调仓 (Equal Weight)

所有股票平均分配仓位，适合分散投资。

**示例配置**:
```yaml
rebalance:
  enabled: true
  mode: "equal_weight"
  stock_pool:
    - sh.600000
    - sh.600036
    - sz.000001
    - sz.000002
```

**目标仓位**: 每只股票 25%

### 2. 目标仓位调仓 (Target Weight)

自定义每只股票的目标仓位比例，适合有偏好的配置。

**示例配置**:
```yaml
rebalance:
  enabled: true
  mode: "target_weight"
  target_positions:
    sh.600000: 0.30  # 30%
    sh.600036: 0.30  # 30%
    sz.000001: 0.25  # 25%
    sz.000002: 0.15  # 15%
```

---

## ⚙️ 配置参数

### 完整配置示例

```yaml
# settings.yaml
rebalance:
  # 基础配置
  enabled: false                    # 是否启用自动调仓
  mode: "equal_weight"              # equal_weight / target_weight
  
  # 调仓频率
  frequency: "weekly"               # daily / weekly / monthly
  rebalance_day: 0                  # 周一 (0-6) / 每月第几天 (1-31)
  
  # 调仓阈值
  threshold_pct: 0.05               # 偏离 5% 触发调仓
  min_trade_value: 1000             # 最小交易金额 1000 元
  
  # 交易成本
  commission_rate: 0.0005           # 佣金万分之五
  stamp_duty_rate: 0.001            # 印花税千分之一
  slippage: 0.001                   # 滑点 0.1%
  
  # 仓位限制
  max_position_pct: 0.10            # 单票最大仓位 10%
  min_position_pct: 0.02            # 单票最小仓位 2%
  
  # 目标仓位 (仅在 target_weight 模式下使用)
  target_positions: {}
  
  # 股票池 (为空则使用主股票池)
  stock_pool: []
  
  # T+1 限制
  respect_t1: true                  # 是否遵守 T+1 交易规则
  
  # 通知
  notify_enabled: true              # 是否发送调仓通知
```

### 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | false | 是否启用自动调仓 |
| `mode` | string | "equal_weight" | 调仓模式：`equal_weight` / `target_weight` |
| `frequency` | string | "weekly" | 调仓频率：`daily` / `weekly` / `monthly` |
| `rebalance_day` | int | 0 | 调仓日：周几 (0-6) 或每月第几天 (1-31) |
| `threshold_pct` | float | 0.05 | 触发调仓的偏离阈值 (5%) |
| `min_trade_value` | float | 1000 | 最小交易金额 (低于此值不交易) |
| `commission_rate` | float | 0.0005 | 佣金率 (万分之五) |
| `stamp_duty_rate` | float | 0.001 | 印花税率 (千分之一，仅卖出) |
| `slippage` | float | 0.001 | 滑点 (0.1%) |
| `max_position_pct` | float | 0.10 | 单只股票最大仓位 |
| `min_position_pct` | float | 0.02 | 单只股票最小仓位 |
| `target_positions` | dict | {} | 目标仓位配置 |
| `stock_pool` | list | [] | 调仓股票池 (为空使用主股票池) |
| `respect_t1` | bool | true | 是否遵守 T+1 限制 |
| `notify_enabled` | bool | true | 是否发送飞书通知 |

---

## 🚀 使用指南

### 1. 启用调仓

编辑 `bobquant/config/settings.yaml`:

```yaml
rebalance:
  enabled: true
  mode: "equal_weight"
  frequency: "weekly"
  rebalance_day: 0  # 每周一调仓
  threshold_pct: 0.05
  stock_pool:
    - sh.600000
    - sh.600036
    - sz.000001
    - sz.000002
```

### 2. 运行测试

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python tests/test_rebalance.py
```

### 3. 查看调仓日志

调仓日志保存在 `bobquant/logs/rebalance_state.json`:

```json
{
  "last_rebalance_date": "2026-04-14",
  "history": [
    {
      "date": "2026-04-14",
      "mode": "equal_weight",
      "orders_count": 4,
      "total_value": 250000,
      "total_cost": 875
    }
  ]
}
```

---

## 📊 调仓流程

### 流程图

```
┌─────────────────────┐
│   开始调仓检查      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 是否到调仓日？      │─── 否 ───> 跳过
└──────────┬──────────┘
           │ 是
           ▼
┌─────────────────────┐
│ 计算当前仓位        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 计算目标仓位        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 偏离度 > 阈值？     │─── 否 ───> 跳过
└──────────┬──────────┘
           │ 是
           ▼
┌─────────────────────┐
│ 生成调仓订单        │
│ (先卖后买)          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 检查 T+1 限制       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 执行交易            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 保存状态 + 通知     │
└─────────────────────┘
```

### 调仓步骤

1. **检查调仓日**: 根据频率配置判断是否应该调仓
2. **计算总资产**: 现金 + 所有持仓市值
3. **计算目标价值**: 根据模式计算每只股票的目标价值
4. **计算偏离度**: 当前价值 vs 目标价值
5. **生成订单**: 
   - 先卖出超配的股票（释放现金）
   - 后买入低配的股票（使用释放的现金）
6. **T+1 检查**: 确保卖出的股票是可卖的（非今日买入）
7. **执行交易**: 通过 Executor 执行买卖订单
8. **记录状态**: 保存调仓历史，发送通知

---

## 💡 实战示例

### 示例 1: 等权重调仓

**初始状态**:
- 总资产：¥1,000,000
- 持仓：sh.600000 100% (¥1,000,000)
- 现金：¥0

**目标配置** (4 只股票等权重):
- sh.600000: 25% = ¥250,000
- sh.600036: 25% = ¥250,000
- sz.000001: 25% = ¥250,000
- sz.000002: 25% = ¥250,000

**调仓订单**:
1. 🔴 卖出 sh.600000 75,000 股 @ ¥10.0 = ¥750,000
2. 🟢 买入 sh.600036 7,142 股 @ ¥35.0 = ¥250,000
3. 🟢 买入 sz.000001 20,833 股 @ ¥12.0 = ¥250,000
4. 🟢 买入 sz.000002 10,000 股 @ ¥25.0 = ¥250,000

**调仓后**:
- 每只股票约 25% 仓位
- 现金剩余约¥0

### 示例 2: 阈值触发

**配置**: `threshold_pct: 0.05` (5%)

**场景 A**: 当前仓位 [52%, 48%]，目标 [50%, 50%]
- 偏离度：2% < 5%
- **结果**: 不触发调仓

**场景 B**: 当前仓位 [60%, 40%]，目标 [50%, 50%]
- 偏离度：10% > 5%
- **结果**: 触发调仓

---

## ⚠️ 注意事项

### 1. T+1 限制

- 今日买入的股票明日才能卖出
- 调仓时会优先检查可卖股数
- 如果可卖股数不足，可能无法完全调仓到位

### 2. 交易成本

每次调仓都会产生交易成本：
- **佣金**: 0.05% (买卖双向)
- **印花税**: 0.1% (仅卖出)
- **滑点**: 0.1% (估算)

**建议**: 不要过于频繁调仓（如每日），推荐每周或每月。

### 3. 现金管理

- 调仓会优先卖出释放现金，再买入
- 确保有足够的现金完成买入订单
- 如果现金不足，会按最大可买数量调整

### 4. 最小交易金额

- 默认最小交易金额：¥1,000
- 低于此金额的仓位调整会被忽略
- 避免产生过多小额交易

### 5. 调仓时间

- 建议在非交易时段执行（如盘后）
- 避免在盘中频繁调仓影响其他策略

---

## 🔧 高级用法

### 1. 自定义调仓股票池

调仓股票池可以独立于主股票池：

```yaml
rebalance:
  stock_pool:
    - sh.600000  # 只调仓这 4 只
    - sh.600036
    - sz.000001
    - sz.000002
```

### 2. 动态调整阈值

根据市场波动率动态调整阈值：

```python
# 在策略中动态修改
if market_volatility > 0.03:
    config.threshold_pct = 0.08  # 高波动时放宽阈值
else:
    config.threshold_pct = 0.05  # 正常阈值
```

### 3. 分批调仓

大额调仓可以分多天执行：

```yaml
rebalance:
  min_trade_value: 5000  # 提高最小交易金额
  frequency: "daily"     # 每天调一点
  threshold_pct: 0.10    # 较高阈值
```

### 4. 与策略信号结合

调仓不影响策略信号交易：

```
调仓订单 (Phase 4)
  ↓
策略信号订单 (Phase 3)
  ↓
做 T 订单 (Phase 1)
  ↓
高频订单 (Phase 0)
```

所有订单会合并执行，调仓优先级较低。

---

## 📈 性能优化

### 1. 减少 API 调用

- 调仓时使用并行获取价格
- 缓存调仓状态，避免重复计算

### 2. 订单优化

- 先卖后买，释放现金
- 合并同向订单（多个买入合并）
- 优先处理大额订单

### 3. 日志管理

- 调仓日志单独保存
- 保留最近 50 次调仓记录
- 自动清理过期日志

---

## 🐛 故障排查

### 问题 1: 调仓未触发

**检查**:
1. `enabled` 是否为 `true`
2. 是否到调仓日 (`frequency` + `rebalance_day`)
3. 偏离度是否超过阈值

### 问题 2: 订单执行失败

**检查**:
1. 现金是否充足
2. T+1 限制（今日买入不可卖）
3. 最小交易数量（100 股整数倍）

### 问题 3: 调仓后仓位仍偏离

**原因**:
- 现金不足
- T+1 限制导致无法卖出
- 股票停牌或无价格数据

**解决**: 等待下一调仓日或手动调整

---

## 📚 API 参考

### RebalanceConfig

```python
config = RebalanceConfig({
    'enabled': True,
    'mode': 'equal_weight',
    'frequency': 'weekly',
    'threshold_pct': 0.05,
    'stock_pool': ['sh.600000', 'sh.600036']
})
```

### RebalanceEngine

```python
engine = RebalanceEngine(config, log_callback, notify_callback)

# 检查是否应该调仓
should, reason = engine.should_rebalance()

# 检查仓位偏离
needs, deviation, reason = engine.check_position_deviation(account, prices)

# 生成调仓订单
orders = engine.generate_rebalance_orders(account, prices, stock_names)

# 执行调仓
result = engine.execute_rebalance(account, executor, prices, stock_names)

# 获取调仓摘要
summary = engine.get_rebalance_summary()
```

### 工厂函数

```python
# 从配置创建引擎
engine = create_rebalance_engine(config_dict, log_callback, notify_callback)

# 从全局配置读取
config = get_rebalance_config_from_settings()
```

---

## 📝 更新日志

### v1.0 (2026-04-11)

- ✅ 初始版本发布
- ✅ 等权重调仓
- ✅ 目标仓位调仓
- ✅ 调仓阈值触发
- ✅ T+1 限制处理
- ✅ 交易成本计算
- ✅ 集成到主交易引擎
- ✅ 飞书通知支持

---

## 📞 支持

如有问题或建议，请：
1. 查看日志文件 `bobquant/logs/rebalance_state.json`
2. 运行测试 `python tests/test_rebalance.py`
3. 联系开发者

---

_文档生成：2026-04-11_  
_版本：v1.0_  
_作者：BobQuant Team_
