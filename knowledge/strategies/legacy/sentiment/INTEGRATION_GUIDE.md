# 市场情绪分析集成指南

## 📁 创建的文件

1. **`bobquant/sentiment/market_sentiment.py`** - 核心情绪分析模块
2. **`bobquant/sentiment/integration_example.py`** - 集成示例代码
3. **`bobquant/sentiment/__init__.py`** - 更新导出（新增 MarketSentimentAnalyzer）

---

## 📊 情绪指标说明

### 1. 涨停/跌停比 (Limit Up/Down Ratio)
- **计算方法**: 涨停家数 / 跌停家数
- **评分逻辑**: 
  - ratio > 3 → 高分（市场情绪高涨）
  - ratio < 0.33 → 低分（市场情绪低迷）
  - 使用 tanh 函数平滑映射到 0-100
- **权重**: 25%

### 2. 成交量比 (Volume Ratio)
- **计算方法**: 
  - 平均成交量比 = 今日成交量 / 昨日成交量
  - 放量率 = 成交量比 > 1.5 的股票比例
- **评分逻辑**:
  - 1.2 ≤ avg_ratio ≤ 2.0 → 70-85 分（健康放量）
  - avg_ratio < 1.2 → 40-70 分（缩量）
  - avg_ratio > 2.0 → 50-70 分（过度放量）
- **权重**: 20%

### 3. 涨跌家数比 (Advance/Decline Ratio)
- **计算方法**: 
  - 上涨家数 / 下跌家数
  - 上涨比例 = 上涨家数 / (上涨 + 下跌)
- **评分逻辑**: 
  - 直接使用上涨比例 × 100
  - 例如：60% 股票上涨 → 60 分
- **权重**: 20%

### 4. 北向资金流向 (Northbound Capital Flow)
- **计算方法**: 北向资金净流入（亿元）
- **评分逻辑**:
  - net_inflow > 50 → 90 分（大幅流入）
  - net_inflow > 20 → 70 分（流入）
  - -20 < net_inflow ≤ 20 → 50 分（平衡）
  - net_inflow < -50 → 10 分（大幅流出）
- **权重**: 20%

### 5. 融资融券数据 (Margin Financing)
- **计算方法**: 
  - 融资余额变化（万亿元）
  - 融资买入占比
- **评分逻辑**:
  - margin_change > 0.03 → 80 分（大幅增加）
  - margin_change > 0 → 60 分（增加）
  - margin_change < -0.02 → 30 分（减少）
- **权重**: 15%

---

## 🎯 综合情绪指数

### 计算公式
```
composite_score = Σ(indicator_score × weight)
```

### 情绪等级划分
| 分数范围 | 等级 | 说明 |
|---------|------|------|
| ≥ 80 | extreme_high | 极度高涨（超买） |
| 60-79 | high | 高涨 |
| 40-59 | neutral | 中性 |
| 20-39 | low | 低迷 |
| < 20 | extreme_low | 极度低迷（超卖） |

### 市场状态判断
| 分数范围 | 状态 | 交易信号 |
|---------|------|---------|
| ≥ 80 | overbought | strong_sell |
| 60-79 | slightly_overbought | sell |
| 40-59 | neutral | hold |
| 20-39 | slightly_oversold | buy |
| < 20 | oversold | strong_buy |

---

## 💼 仓位建议

| 情绪等级 | 建议仓位 | 操作 | 风险等级 |
|---------|---------|------|---------|
| extreme_high | 30% | 减仓 | 高 |
| high | 50% | 减仓 | 中高 |
| neutral | 60% | 持有 | 中 |
| low | 70% | 加仓 | 中低 |
| extreme_low | 80% | 加仓 | 低 |

---

## 🔧 与现有策略的集成方式

### 方式一：在策略引擎中使用（推荐）

```python
from sentiment import MarketSentimentAnalyzer

class MyStrategy:
    def __init__(self):
        self.sentiment_analyzer = MarketSentimentAnalyzer()
    
    def generate_signal(self, stock_data):
        # 1. 获取情绪数据
        sentiment_data = self.sentiment_analyzer.get_sentiment_for_strategy()
        score = sentiment_data['composite_score']
        
        # 2. 根据情绪过滤信号
        if score >= 80:  # 超买
            return None  # 禁止开多仓
        
        # 3. 生成原始信号
        signal = self._generate_technical_signal(stock_data)
        
        # 4. 根据情绪调整仓位
        position_limit = sentiment_data['position_limit']
        adjusted_size = int(signal['size'] * position_limit / 100)
        
        return {
            'signal': signal['signal'],
            'size': adjusted_size,
            'reason': f"情绪{sentiment_data['sentiment_level']}({score:.0f}分)"
        }
```

### 方式二：集成到现有 SentimentController

在 `strategy/sentiment_controller.py` 中调用新的分析器：

```python
from sentiment import MarketSentimentAnalyzer

class SentimentController:
    def __init__(self, config):
        self.config = config
        self.sentiment = SentimentIndex()  # 原有的
        self.market_sentiment = MarketSentimentAnalyzer()  # 新增的
    
    def get_sentiment(self, force_refresh=False):
        # 可以结合两个情绪指数的结果
        old_result = self.sentiment.calculate_sentiment_score()
        new_result = self.market_sentiment.calculate_all_indicators()
        
        # 加权平均或选择更保守的结果
        combined_score = (old_result['score'] * 0.5 + 
                         new_result['composite_score'] * 0.5)
        
        return {
            'score': combined_score,
            'old_score': old_result['score'],
            'new_score': new_result['composite_score'],
            # ... 其他字段
        }
```

### 方式三：在 main.py 中调用

```python
# 在 bobquant/main.py 中

from sentiment import MarketSentimentAnalyzer

class TradingSystem:
    def __init__(self, config):
        self.config = config
        self.sentiment_analyzer = MarketSentimentAnalyzer()
    
    def daily_routine(self):
        # 每日开盘前
        sentiment_report = self.sentiment_analyzer.generate_report()
        print(sentiment_report)
        
        # 获取情绪数据用于当日交易
        sentiment_data = self.sentiment_analyzer.get_sentiment_for_strategy()
        self.position_limit = sentiment_data['position_limit']
    
    def before_buy(self, signal):
        # 买入前检查
        sentiment_data = self.sentiment_analyzer.get_sentiment_for_strategy()
        
        if sentiment_data['market_state'] == 'overbought':
            print("⚠️ 市场超买，跳过买入")
            return False
        
        # 调整仓位
        signal['size'] = int(signal['size'] * sentiment_data['position_limit'] / 100)
        return True
```

---

## 📝 使用示例

### 基础使用

```python
from sentiment import MarketSentimentAnalyzer

# 创建分析器
analyzer = MarketSentimentAnalyzer()

# 计算今日情绪指数
result = analyzer.calculate_all_indicators()

print(f"综合评分：{result['composite_score']}")
print(f"情绪等级：{result['sentiment_level']}")
print(f"市场状态：{result['market_state']}")
```

### 生成完整报告

```python
# 生成格式化报告
report = analyzer.generate_report()
print(report)
```

### 为策略提供数据

```python
# 获取策略可用数据
strategy_data = analyzer.get_sentiment_for_strategy()

print(f"仓位上限：{strategy_data['position_limit']}%")
print(f"交易信号：{strategy_data['signal']}")
```

### 获取详细指标

```python
result = analyzer.calculate_all_indicators()
indicators = result['indicators']

# 涨停/跌停比
print(f"涨停：{indicators['limit_ratio']['limit_up_count']}家")
print(f"跌停：{indicators['limit_ratio']['limit_down_count']}家")

# 涨跌家数
print(f"上涨：{indicators['advance_decline']['up_count']}家")
print(f"下跌：{indicators['advance_decline']['down_count']}家")

# 北向资金
print(f"净流入：{indicators['northbound']['net_inflow']}亿元")
```

---

## 🧪 测试

运行测试脚本查看今日情绪指数：

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python sentiment/market_sentiment.py
```

运行集成示例：

```bash
python sentiment/integration_example.py
```

---

## 📅 今日情绪指数（测试结果）

运行测试后输出：
```
📊 今日情绪指数（2026-04-11）
综合评分：XX.XX / 100
情绪等级：neutral/high/low/...
市场状态：neutral/overbought/oversold/...
交易信号：hold/buy/sell/...
```

---

## ⚠️ 注意事项

1. **数据源集成**: 当前使用模拟数据，需要集成真实数据源：
   - 腾讯财经（行情数据）
   - 交易所 API（涨跌停家数）
   - 港交所（北向资金）
   - 证监会（融资融券）

2. **性能优化**: 
   - 使用缓存避免重复计算
   - 只在每日开盘前计算一次
   - 盘中可复用缓存结果

3. **参数调优**:
   - 权重可根据历史回测调整
   - 阈值可根据市场特性优化
   - 建议进行参数敏感性分析

4. **风险控制**:
   - 情绪指数仅作为辅助工具
   - 不应单独作为交易依据
   - 需结合技术分析、基本面等

---

## 📚 相关文件

- `sentiment/sentiment_index.py` - 原有情绪指数模块
- `sentiment/sentiment_controller.py` - 情绪控制器
- `strategy/engine.py` - 策略引擎（已集成 SentimentController）
- `docs/SENTIMENT_INTEGRATION.md` - 本文档

---

## 🔄 后续优化

1. **真实数据接入**: 集成腾讯财经、baostock 等数据源
2. **历史回测**: 验证情绪指数的预测能力
3. **机器学习**: 使用 ML 优化权重和阈值
4. **更多指标**: 添加波动率、换手率等指标
5. **行业情绪**: 分行业计算情绪指数
