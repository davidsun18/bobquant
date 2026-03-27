# BobQuant V2 - 完整因子库 (P0+P1+P2)

## 📊 三层因子架构

### 🔴 P0 - 核心必备因子 (5个)

| 因子 | 用途 | 信号 |
|------|------|------|
| **MA** | 移动平均线 | 价格>MA买入 |
| **MACD** | 异同移动平均线 | 金叉买入,死叉卖出 |
| **RSI** | 相对强弱指标 | <30超卖买入,>70超买卖出 |
| **Volume MA** | 成交量均线 | 放量确认 |
| **Momentum** | 价格动量 | 正动量买入 |

### 🟠 P1 - 重要增强因子 (3个)

| 因子 | 用途 | 信号 |
|------|------|------|
| **Bollinger** | 布林带 | 突破上轨买入,跌破下轨卖出 |
| **KDJ** | 随机指标 | 金叉买入,死叉卖出 |
| **ATR** | 真实波幅 | 止损计算 |

### 🟡 P2 - 高级精细化因子 (5类)

| 类别 | 因子 | 用途 |
|------|------|------|
| **趋势强度** | ADX, 趋势一致性, 持续性 | 判断趋势质量 |
| **波动率** | 历史波动率, 波动率状态 | 风险控制 |
| **资金流向** | MFI, 资金流强度 | 确认资金态度 |
| **技术形态** | 锤子线, 吞没, 星线 | 寻找入场点 |
| **多时间周期** | 短/中/长期一致性 | 确认大方向 |

---

## 🎯 评分体系

### 三级评分流程

```
Step 1: P0基础评分 (0-100)
        MA + MACD + RSI + Volume + Momentum
        
Step 2: P1增强评分 (调整±30分)
        + Bollinger突破
        + KDJ金叉/死叉
        + ATR止损
        
Step 3: P2精细化评分 (调整±25分)
        + 趋势强度 (+10/-10)
        + 波动率收缩 (+5)
        + 资金流入 (+8)
        + 技术形态 (+8/-8)
        + 多周期一致 (+10/-10)
        
最终评分: 0-100分
```

### 信号分级

| 评分 | P1信号 | P2信号 | 仓位建议 |
|------|--------|--------|----------|
| 85-100 | STRONG_BUY | STRONG_BUY | 100% |
| 70-84 | BUY | BUY | 80% |
| 55-69 | - | WEAK_BUY | 40% |
| 45-54 | HOLD | HOLD | 0% |
| 30-44 | - | WEAK_SELL | -20% |
| 15-29 | SELL | SELL | -60% |
| 0-14 | STRONG_SELL | STRONG_SELL | -100% |

---

## 💻 使用方式

### 基础用法 (P0+P1)

```python
from bobquant_v2.indicator.technical import all_indicators
from bobquant_v2.strategy.factor_strategy import create_strategy

# 计算指标
df = all_indicators(df)

# P1策略
strategy = create_strategy('balanced')
signal = strategy.analyze(code, name, df, quote)
# signal.score: 0-100分
```

### 高级用法 (P0+P1+P2)

```python
from bobquant_v2.indicator.technical import all_indicators
from bobquant_v2.strategy.p2_strategy import create_p2_strategy

# 计算所有指标 (包括P2)
df = all_indicators(df, include_p2=True)

# P2策略
strategy = create_p2_strategy('balanced')
p2_signal = strategy.analyze_p2(code, name, df, quote)

# P2信号包含:
# - p1_score: P1基础评分
# - p2_adjustment: P2调整分数
# - final_score: 最终评分
# - risk_level: 风险等级 (low/medium/high)
# - suggested_position: 建议仓位 (0-1)
```

---

## 📈 实测数据

### 贵州茅台 (sh.600519)

```
P0指标:
  MACD: -3.48 (中性)
  RSI: 54.5 (正常)
  MA20: ¥1421.39

P1指标:
  KDJ: K=19.5, D=28.8 (超卖区)
  布林带: 45.1% (中轨)
  ATR: 25.38

P2指标:
  趋势强度: 100 (strong)
  波动率: 20.7% (normal)
  MFI: 48 (中性)
  形态得分: 30
  多周期一致性: 0.00

技术形态:
  锤子线: ❌
  吞没形态: ✅
  星线形态: ❌
  多头排列: ❌

P2调整后评分: 60分 (WEAK_BUY)
```

---

## 🏗️ 代码结构

```
bobquant_v2/
├── indicator/
│   ├── technical.py      # P0+P1因子 (300行)
│   └── advanced.py       # P2因子 (400行)
├── strategy/
│   ├── factor_strategy.py   # P1策略 (200行)
│   └── p2_strategy.py       # P2策略 (300行)
├── test_factors.py       # P1测试
├── test_p2_factors.py    # P2测试
└── FACTORS_COMPLETE.md   # 本文档

总计: 约1200行代码实现完整三级因子库
```

---

## 🚀 三种策略风格

### Conservative (保守)
- RSI区间: 25-75
- 评分要求: 75分才买
- 风险承受: 低波动率
- 特点: 少交易，高胜率

### Balanced (平衡) - 默认
- RSI区间: 30-70
- 评分要求: 70分才买
- 风险承受: 中等波动率
- 特点: 平衡收益和风险

### Aggressive (激进)
- RSI区间: 35-65
- 评分要求: 60分就买
- 风险承受: 高波动率
- 特点: 多交易，追求高收益

---

## 📊 性能指标

| 操作 | 耗时 |
|------|------|
| P0+P1指标计算 | <10ms |
| P0+P1+P2指标计算 | <20ms |
| 单股策略分析 | <30ms |
| 30股批量分析 | <1秒 |
| 实时行情获取 | <500ms |

---

## ✅ 测试状态

- [x] P0因子测试通过
- [x] P1因子测试通过
- [x] P2因子测试通过
- [x] 策略引擎测试通过
- [x] 实时数据测试通过

---

## 🎯 使用建议

### 实盘交易建议
1. **先用P1策略** - 稳定可靠，适合大部分情况
2. **P2用于精细筛选** - 在P1信号基础上优化入场点
3. **关注风险等级** - P2会给出风险评级，控制仓位
4. **多周期确认** - P2的多时间周期一致性很重要

### 回测建议
1. 分别测试P1和P2的表现
2. 对比不同风格(conservative/balanced/aggressive)
3. 优化P2配置参数
4. 验证P2是否真正提升收益

---

**完整的三级因子库已实现，可以开始实盘测试！** 🎉📊
