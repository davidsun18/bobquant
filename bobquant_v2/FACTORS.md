# BobQuant V2 - P0+P1 因子库

## 📊 已实现因子

### 🔴 P0 - 核心必备因子

| 因子 | 说明 | 信号 | 用途 |
|------|------|------|------|
| **MA** | 移动平均线(5/10/20/60) | 价格>MA买入 | 趋势判断 |
| **MACD** | 异同移动平均线 | 金叉买入,死叉卖出 | 趋势跟踪 |
| **RSI** | 相对强弱指标(14) | <30超卖买入,>70超买卖出 | 超买超卖 |
| **Volume MA** | 成交量均线 | 放量确认 | 量能确认 |
| **Momentum** | 价格动量(5/10/20日) | 正动量买入 | 趋势强度 |

### 🟠 P1 - 重要增强因子

| 因子 | 说明 | 信号 | 用途 |
|------|------|------|------|
| **Bollinger** | 布林带(20,2) | 突破上轨买入,跌破下轨卖出 | 波动率、突破 |
| **KDJ** | 随机指标(9,3,3) | 金叉买入,死叉卖出 | 短期买卖点 |
| **ATR** | 真实波幅(14) | 用于止损计算 | 风险控制 |

## 🎯 信号生成

### 综合评分算法

```python
基础分: 50分
+ MACD金叉: +20分
+ MACD死叉: -20分
+ KDJ金叉: +15分
+ KDJ死叉: -15分
+ RSI超卖: +10分
+ RSI超买: -10分

结果: 0-100分
  80-100: 强烈买入
  70-79:  买入
  30-69:  观望
  20-29:  卖出
  0-19:   强烈卖出
```

## 📈 策略配置

### 预定义策略

```python
# 保守策略 - 严格条件，少交易
conservative = {
    'rsi_buy': 25,      # RSI<25才买
    'rsi_sell': 75,     # RSI>75才卖
    'score_buy': 75,    # 评分>75才买
    'score_sell': 25,   # 评分<25才卖
}

# 平衡策略 - 适中条件
balanced = {
    'rsi_buy': 30,
    'rsi_sell': 70,
    'score_buy': 70,
    'score_sell': 30,
}

# 激进策略 - 宽松条件，多交易
aggressive = {
    'rsi_buy': 35,
    'rsi_sell': 65,
    'score_buy': 60,
    'score_sell': 40,
}
```

## 💻 使用示例

### 1. 计算指标

```python
from bobquant_v2.indicator.technical import all_indicators

# 一次性计算所有P0+P1指标
df = all_indicators(df)

# 结果包含:
# - ma5, ma10, ma20, ma60
# - macd_line, macd_signal, macd_golden, macd_death
# - rsi, rsi_overbought, rsi_oversold
# - kdj_k, kdj_d, kdj_j, kdj_golden, kdj_death
# - boll_mid, boll_upper, boll_lower, boll_pct
# - atr, atr_pct
# - mom5, mom10, mom20
```

### 2. 生成信号

```python
from bobquant_v2.indicator.technical import generate_signals

signals = generate_signals(df)
# 返回:
# {
#   'macd_signal': 'buy'/'sell'/'hold',
#   'rsi_signal': 'overbought'/'oversold'/'normal',
#   'kdj_signal': 'buy'/'sell'/'hold',
#   'boll_signal': 'break_upper'/'break_lower'/'squeeze'/'normal',
#   'composite_score': 0-100
# }
```

### 3. 策略分析

```python
from bobquant_v2.strategy.factor_strategy import create_strategy

# 创建策略
strategy = create_strategy('balanced')

# 分析股票
signal = strategy.analyze(code, name, df, quote)
# 返回 Signal对象:
# - code: 股票代码
# - name: 股票名称
# - signal: STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL
# - score: 0-100分
# - reasons: ['MACD金叉', 'RSI超卖', ...]
# - confidence: 'high'/'medium'/'low'
```

### 4. 获取交易建议

```python
# 获取仓位建议
suggestion = strategy.get_position_suggestion(signal, current_pos)
# 返回:
# {
#   'action': 'buy'/'sell'/'hold',
#   'shares': 1000,
#   'reason': '贵州茅台: MACD金叉, RSI超卖 (评分:85)'
# }
```

## 📊 测试结果

```
✅ 贵州茅台: ¥1416.02
   MACD: 中性
   RSI: 54.5 (正常)
   KDJ: K=19.5, D=28.8, J=1.0 (超卖)
   布林带: 45.1% (中轨)
   综合评分: 50

✅ 宁德时代: ¥416.18
   MACD: 中性
   RSI: 76.9 (超买)
   KDJ: K=58.2, D=57.3, J=59.9 (金叉)
   布林带: 79.7% (接近上轨)
   综合评分: 55

✅ 工商银行: ¥7.40
   MACD: 中性
   RSI: 64.7 (正常)
   KDJ: K=54.3, D=61.0, J=40.7 (中性)
   布林带: 74.6%
   综合评分: 50
```

## 🔧 技术细节

### 缓存机制
- 指标计算结果自动缓存
- 实时行情3秒缓存
- 避免重复计算和网络请求

### 数据要求
- 最少需要30天历史数据
- 数据格式: open, high, low, close, volume
- 支持baostock数据源

### 性能
- 批量行情获取: 10线程并行
- 单只股票指标计算: <10ms
- 30只股票批量分析: <1秒

## 🚀 下一步

### P2因子（可选）
- [ ] 基本面因子 (PE/PB/ROE)
- [ ] 资金流向因子
- [ ] 行业轮动因子
- [ ] 波动率因子 (ATR已实现)

### P3因子（未来）
- [ ] 机器学习预测
- [ ] 模式识别
- [ ] 强化学习优化

## 📁 文件结构

```
bobquant_v2/
├── indicator/
│   └── technical.py      # P0+P1因子实现 (300行)
├── strategy/
│   └── factor_strategy.py # 策略引擎 (200行)
├── test_factors.py       # 测试脚本
└── FACTORS.md           # 本文档
```

**总计: 约500行代码实现完整因子库**
