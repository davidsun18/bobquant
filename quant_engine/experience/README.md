# BobQuant 自学习系统使用指南 (v2.1)

## 概述

v2.1 引入了**自学习经验系统**，让 BobQuant 从"静态规则执行者"变成"会积累经验的交易员"。

### 核心思想

```
普通量化:  人写规则 → 静态系统
BobQuant:  规则兜底 + 经验积累 → 动态成长
```

### 四大模块

| 模块 | 职责 | 文件 |
|------|------|------|
| ExperienceLibrary | 存储决策快照和经验条目 | `experience/experience_lib.py` |
| ReviewAgent | 自动复盘历史决策 | `experience/review_agent.py` |
| ExperienceInjector | 新决策时召回历史经验 | `experience/experience_injector.py` |
| FeedbackLoop | 每周自动微调规则参数 | `experience/feedback_loop.py` |

---

## 工作流程

### 1. 决策留痕 (自动生成)

每次信号生成时，系统自动记录 `DecisionSnapshot`：

```python
# signal_generator.py 内部自动执行
snapshot = DecisionSnapshot(
    code="000001",
    direction="buy",
    regime_state="normal",      # 当时市场状态
    regime_adx=20.0,            # ADX 值
    regime_vol_percentile=0.50, # 波动率分位
    price=15.50,                # 决策价格
    atr_20=0.30,                # ATR
    grid_level=0,               # 网格层级
    reason="网格买入信号",
)
lib.save_snapshot(snapshot)
```

**存储位置:** `quant_engine/experience/snapshots/<date>.jsonl`

### 2. 自动复盘 (定时执行)

`ReviewAgent` 定期检查历史快照（默认 24 小时后）：

```python
from quant_engine.experience import get_review_agent

reviewer = get_review_agent(review_hours=24)
result = reviewer.run_review(market_prices={
    "000001": 16.00,  # 当前价格
    "600519": 1850.0,
})

# 结果示例:
# {
#     "reviewed_count": 5,
#     "win_count": 3,
#     "loss_count": 2,
#     "experiences_added": 4,
# }
```

**复盘逻辑:**
- 对比"决策价格"和"当前价格"，计算实际收益
- 收益 > 1% → 标记为 WIN
- 收益 < -1% → 标记为 LOSS
- 生成经验条目（带场景标签）归档到经验库

### 3. 经验注入 (信号生成时自动触发)

下次生成信号时，系统自动召回相关历史经验：

```python
# 内部流程 (signal_generator.py)
context_tags = {
    "regime": "normal",
    "adx_range": "low",
    "vol_range": "normal",
    "grid_level": "entry",
    "signal_type": "buy",
}

experiences = lib.retrieve(context_tags, top_k=5)
# 返回类似:
# [
#   "[成功] 000001 正常市场下买入成功 (收益 +3.2%)",
#   "[失败] 600519 预警市场下买入失败 (亏损 -2.1%) — 忽略高波动",
# ]

# 计算置信度调整
adjustment = compute_adjustment(experiences)  # 例如 +8.5

# 如果调整后置信度低于门槛，拦截信号
```

### 4. 反馈闭环 (每周执行)

```python
from quant_engine.experience import get_feedback_loop

feedback = get_feedback_loop()
adjustments = feedback.run_weekly_review(
    trade_history=recent_trades,
    current_config={
        "conviction_threshold": 50.0,
        "grid_spacing_multiplier": 1.0,
        "stop_loss_multiplier": 1.0,
    }
)

# 可能返回:
# [
#   {
#       "parameter": "conviction_threshold",
#       "old_value": 50.0,
#       "new_value": 55.0,
#       "reason": "胜率 42% < 45%，提高门槛以过滤低质量信号",
#   }
# ]
```

---

## 在 TradingEngine 中使用

```python
from quant_engine import TradingEngine

engine = TradingEngine(config)
engine.load_state()

# === 盘中 ===
engine.update_benchmark(benchmark_df)
engine.update_prices(market_prices)
signals = engine.generate_signals(stock_data)  # 自动记录快照 + 经验注入

for sig in signals:
    engine.execute(sig)

# === 收盘后 ===
# 复盘历史决策
review_result = engine.run_review(market_prices)
print(f"复盘: {review_result['win_count']} 胜, {review_result['loss_count']} 负")

# === 每周日 ===
# 规则自适应调整
adjustments = engine.run_weekly_review()
for adj in adjustments:
    print(f"调整: {adj['parameter']} {adj['old_value']} → {adj['new_value']}")

# === 查询经验库 ===
summary = engine.get_experience_summary()
print(f"总决策: {summary['stats']['total_decisions']}")
print(f"总经验: {summary['stats']['total_experiences']}")
print(f"胜率: {summary['stats']['overall_win_rate']:.0%}")
```

---

## 经验标签体系

系统使用标准化标签描述场景，确保经验可检索：

| 标签 | 取值 | 说明 |
|------|------|------|
| `regime` | normal / warning / soft_circuit_break / hard_circuit_break | 市场状态 |
| `adx_range` | low (<25) / medium (25-35) / high (>35) | 趋势强度 |
| `vol_range` | low (<30%) / normal (30-70%) / high (>70%) | 波动率分位 |
| `grid_level` | entry / grid_early / grid_deep | 网格层级 |
| `position_type` | new_open / add_position | 是否已有持仓 |
| `signal_type` | buy / sell | 信号方向 |

**检索逻辑:** 至少 2 个标签匹配才视为"相似场景"，按匹配数 + 近期权重排序。

---

## 配置参数

```python
config = {
    "experience": {
        "enabled": True,                  # 是否启用经验系统
        "top_k": 5,                       # 召回经验条数
        "conviction_threshold": 30.0,     # 信号置信度门槛
    },
    "feedback_loop": {
        "max_step_pct": 0.10,             # 每次最大调整幅度 10%
        "min_samples": 20,                # 最小样本量
        "consecutive_loss_pause": 5,      # 连续亏损暂停阈值
    },
}
```

---

## 安全机制

1. **步长限制** — 每次参数调整最多 10%，防止剧烈变化
2. **连续亏损暂停** — 连续 5 次亏损后暂停自动调整
3. **最小样本量** — 少于 20 笔交易不做调整
4. **经验衰减** — 超过 1 年的经验权重递减
5. **所有调整留痕** — 支持回滚

---

## 数据文件

```
quant_engine/experience/
├── snapshots/                    # 决策快照（按日期）
│   ├── 2026-04-30.jsonl
│   ├── 2026-05-01.jsonl
│   └── ...
├── experiences.json              # 经验条目主库
├── stats.json                    # 统计信息
├── feedback_log.json             # 反馈调整历史
└── adaptive_config.json          # 自适应参数（当前值）
```

---

## 单元测试

```bash
# 运行全部测试 (65 个)
pytest quant_engine/tests/ quant_engine/experience/tests/ -v

# 只测经验系统
pytest quant_engine/experience/tests/ -v
```

---

*BobQuant v2.1 — 让量化系统像交易员一样成长*
