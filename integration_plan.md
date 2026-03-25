# BobQuant 三大系统集成方案

## 📋 集成目标

将三个优秀的量化项目集成到 BobQuant 系统中：

1. **AI-Agent-Alpha 情绪指数系统** → 市场情绪量化模块
2. **ML 股票预测算法库** → 机器学习预测模块
3. **RQAlpha 回测框架** → 架构参考与数据源集成

---

## 🎯 集成方案

### 1️⃣ AI-Agent-Alpha 情绪指数系统

**集成位置**: `bobquant/sentiment/`

**核心功能**:
- 市场情绪评分 (0-100)
- 涨跌停比、连板表现、炸板率等指标
- AI 情绪分析报告
- 仓位管理建议

**集成步骤**:
```bash
# 1. 创建情绪模块目录
mkdir -p bobquant/sentiment

# 2. 克隆并适配核心逻辑
# 参考: https://github.com/Haohao-end/AI-Agent-Alpha-quantitative-trading-strategy

# 3. 数据源适配
# 原项目用 Tushare → 改为腾讯财经/Infoway (现有数据源)

# 4. 集成到策略引擎
# 情绪分数 → 仓位控制输入
```

**模块结构**:
```
bobquant/sentiment/
├── __init__.py
├── sentiment_index.py      # 情绪指数计算核心
├── indicators.py           # 情绪指标 (涨跌停比/连板/炸板率)
├── ai_analysis.py          # AI 分析报告生成
├── position_control.py     # 基于情绪的仓位控制
└── data_fetcher.py         # 数据获取 (适配现有数据源)
```

**与现有系统集成**:
- 输入：市场数据 (现有 data 模块)
- 输出：情绪分数 → strategy 模块 (仓位控制)
- 配置：settings.yaml 增加情绪相关参数

---

### 2️⃣ ML 股票预测算法库

**集成位置**: `bobquant/ml/` (扩展现有 indicator 模块)

**核心功能**:
- LSTM 价格预测
- Prophet 时间序列
- SVM/随机森林分类
- 回测验证

**集成步骤**:
```bash
# 1. 创建 ML 模块目录
mkdir -p bobquant/ml

# 2. 实现核心算法
# 参考: https://github.com/moyuweiqing/A-stock-prediction-algorithm-based-on-machine-learning

# 3. 依赖安装
pip install tensorflow prophet scikit-learn

# 4. 集成到策略信号
# ML 预测 → 策略信号输入
```

**模块结构**:
```
bobquant/ml/
├── __init__.py
├── lstm_predict.py         # LSTM 价格预测
├── prophet_predict.py      # Prophet 时间序列
├── classifiers.py          # SVM/随机森林/决策树
├── feature_engineering.py  # 特征工程
├── model_trainer.py        # 模型训练与保存
└── backtest.py             # ML 策略回测
```

**与现有系统集成**:
- 输入：历史行情 (现有 data 模块)
- 输出：价格预测 → strategy 模块 (买卖信号)
- 配置：模型参数、训练周期等

---

### 3️⃣ RQAlpha 回测框架参考

**集成方式**: 架构参考 + 数据源对接

**学习要点**:
- 事件驱动架构设计
- Mod Hook 扩展机制
- 风控校验逻辑
- 交易成本计算

**可集成内容**:
```bash
# 1. RQData 数据源 (可选)
# 米筐金融数据 API，无缝对接 RQAlpha
# 可作为现有腾讯财经/Infoway 的补充

# 2. 事件驱动架构参考
# 改进现有策略引擎的事件处理

# 3. 风控模块参考
# 借鉴 sys_risk 模块的风控逻辑
```

**架构改进建议**:
```python
# 参考 RQAlpha 的事件驱动设计
class EventBus:
    """事件总线 - 参考 RQAlpha"""
    def __init__(self):
        self.listeners = {}
    
    def subscribe(self, event_type, callback):
        """订阅事件"""
        pass
    
    def publish(self, event):
        """发布事件"""
        pass

# 现有系统可逐步迁移到事件驱动架构
```

---

## 📅 实施计划

### 阶段 1: 情绪指数系统 (3-5 天)
- [ ] Day 1: 数据源适配 (腾讯财经→情绪指标)
- [ ] Day 2: 情绪指数计算核心实现
- [ ] Day 3: AI 分析报告集成
- [ ] Day 4: 仓位控制逻辑对接
- [ ] Day 5: 测试与优化

### 阶段 2: ML 预测模块 (5-7 天)
- [ ] Day 1-2: LSTM 模型实现
- [ ] Day 3: Prophet/SVM 集成
- [ ] Day 4: 特征工程优化
- [ ] Day 5: 模型训练流程
- [ ] Day 6: 回测验证
- [ ] Day 7: 性能优化

### 阶段 3: 架构优化 (2-3 天)
- [ ] Day 1: 事件驱动架构设计
- [ ] Day 2: 风控模块改进
- [ ] Day 3: 文档与测试

---

## 🔧 技术细节

### 情绪指数计算逻辑

```python
# 核心指标
sentiment_score = (
    limit_up_down_ratio * 0.3 +      # 涨跌停比
    continuous_limit_up_return * 0.2 + # 连板收益
    (1 - bomb_board_rate) * 0.2 +    # 炸板率 (反向)
    high_standard_premium * 0.15 +   # 高标溢价
    prev_limit_up_premium * 0.15     # 昨日涨停溢价
)

# 归一化到 0-100
normalized_score = normalize(sentiment_score, historical_window=60)
```

### LSTM 预测模型

```python
# 输入特征
features = [
    'open', 'high', 'low', 'close', 'volume',
    'ma5', 'ma10', 'ma20',
    'rsi', 'macd', 'bollinger'
]

# 模型结构
model = Sequential([
    LSTM(50, return_sequences=True, input_shape=(60, len(features))),
    Dropout(0.2),
    LSTM(50, return_sequences=False),
    Dropout(0.2),
    Dense(25),
    Dense(1)  # 预测收盘价
])
```

---

## 📊 预期收益

1. **情绪指数**: 改进仓位控制，避免极端行情重仓
2. **ML 预测**: 提高信号准确率，增加策略维度
3. **架构优化**: 提升系统稳定性和扩展性

---

## ⚠️ 注意事项

1. **数据源兼容性**: 确保新模块使用现有数据源 (腾讯财经/Infoway)
2. **性能影响**: ML 模型训练可能耗时，需异步处理
3. **回测验证**: 所有新策略必须经过充分回测
4. **渐进式集成**: 先独立测试，再逐步集成到主系统

---

_创建时间：2026-03-26_
_版本：v1.0_
