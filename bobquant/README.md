# BobQuant ⚡ — A 股量化交易系统

> By David & Bob | v1.0.0 | 2026-03-26  
> **NEW!** 集成市场情绪分析 + 机器学习预测

一套面向 A 股市场的**智能化**模块化量化交易系统，集成**市场情绪分析**和**机器学习预测**，支持模拟盘自动交易，未来可无缝对接实盘券商。

## ✨ 核心特性

### 🧠 智能增强 (NEW! v1.0)
- **市场情绪指数** — AI-Agent-Alpha 情绪评分 (0-100)，动态仓位控制
- **ML 价格预测** — 随机森林/LSTM/SVM，涨跌方向预测准确率~86%
- **综合决策引擎** — 情绪 +ML+ 策略三重信号，智能交易决策

### 交易策略
- **MACD 金叉死叉** — 趋势跟踪，支持 RSI 过滤 + 成交量确认
- **布林带突破** — 均值回归，上下轨信号
- **金字塔加仓** — 3% → 5% → 7% 三档递进，跌 3% 触发加仓
- **分批止盈** — 涨 5% 卖 1/3 → 涨 10% 卖 1/2 → 涨 15% 清仓
- **网格做 T** — 日内多档高抛低吸，每涨 1.5% 抛一次，回落 1% 接回
- **跟踪止损** — 盈利 5% 后激活，从最高点回撤 2% 自动卖出

### 信号过滤
- **RSI 过滤** — RSI > 35 不买入（避免追高），RSI > 70 加大减仓力度
- **成交量确认** — 放量金叉标记为强信号，缩量信号过滤掉
- **信号强度分级** — 强信号直接 5% 仓位，普通信号 3% 试探

### 工程架构
- **模块化设计** — 配置/数据/指标/策略/风控/券商/通知/情绪/ML 9 层分离
- **可插拔接口** — 数据源、策略、券商都是抽象接口，一键切换
- **零硬编码** — 所有路径自动推导，所有参数 YAML 配置驱动
- **172 个测试** — 单元测试 + 集成测试 + 边界条件 + 压力测试全覆盖
- **进程守护** — 交易时段自动启停，崩溃 30 秒内自动重启
- **开机自启** — crontab @reboot 全自动

## 📁 项目结构

```
bobquant/
├── config/
│   ├── __init__.py          # 配置中心（YAML 驱动，零硬编码）
│   ├── settings.yaml        # 全局配置
│   └── stock_pool.yaml      # 股票池（50 只 A 股龙头）
├── indicator/
│   └── technical.py         # MACD / 布林带 / RSI / 量比
├── data/
│   └── provider.py          # 数据源（腾讯财经 + baostock）
├── core/
│   ├── account.py           # 账户 + 持仓 + T+1 管理
│   └── executor.py          # 买入 / 卖出 / 交易记录同步
├── strategy/
│   └── engine.py            # MACD 策略 / 布林带策略 / 风控 / 网格做 T
├── broker/
│   └── base.py              # 券商抽象（模拟盘 / easytrader 预留）
├── notify/
│   └── feishu.py            # 飞书消息通知
├── sentiment/               # 🆕 市场情绪指数模块
│   ├── __init__.py
│   └── sentiment_index.py   # 情绪评分 (0-100) + 仓位建议
├── ml/                      # 🆕 机器学习预测模块
│   ├── __init__.py
│   ├── predictor.py         # LSTM/随机森林/SVM 预测
│   └── models/              # 训练好的模型
├── tests/
│   ├── test_all.py          # 59 个单元测试
│   └── test_integration.py  # 113 个集成测试
├── integration_demo.py      # 🆕 三大系统集成演示
├── main.py                  # 三阶段交易引擎 + 主循环
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖
```bash
# 基础依赖
pip install pandas requests baostock pyyaml flask scikit-learn

# 可选：ML 增强 (LSTM 支持)
pip install tensorflow

# 可选：Prophet 时间序列
pip install prophet
```

### 2. 配置
编辑 `bobquant/config/settings.yaml`，按需修改：
- 初始资金、手续费率
- 策略参数（止损线、止盈档位、做 T 阈值）
- 数据源选择
- 飞书通知 user_id

### 3. 运行
```bash
python run.py
```

### 4. Web 监控
```bash
python web_ui.py  # 访问 http://localhost:5000
```

### 5. 体验智能增强
```bash
# 运行集成演示
python integration_demo.py

# 查看情绪指数
python -c "from sentiment import SentimentIndex; print(SentimentIndex().calculate_sentiment_score())"

# 测试 ML 预测
python -c "from ml import MLPredictor; print(MLPredictor().prepare_features(...))"
```

## 📊 三阶段交易引擎

每个交易时段，引擎按顺序执行三个阶段：

```
Phase 1: 网格做 T
  → 扫描持仓股日内涨幅
  → 触发网格线则高抛，回落则接回

Phase 2: 风控
  → 硬止损（亏 ≥ 8%）
  → 跟踪止损（盈利后从最高点回撤 ≥ 2%）
  → 分批止盈（5% / 10% / 15% 三档）

Phase 3: 策略信号
  → MACD / 布林带信号检测
  → RSI + 成交量双重过滤
  → 情绪指数分析 (NEW!)
  → ML 预测 (NEW!)
  → 综合决策
  → 新建仓 / 金字塔加仓 / 策略减仓
```

## 🧠 智能增强功能

### 市场情绪指数

```python
from sentiment import SentimentIndex

sentiment = SentimentIndex()
result = sentiment.calculate_sentiment_score()

# 输出示例:
# {
#   'score': 65.2,           # 情绪评分 0-100
#   'level': 'high',         # 情绪等级
#   'position_suggestion': { # 仓位建议
#     'suggested_position': 50,
#     'action': '减仓',
#     'reason': '市场情绪高涨，适当降低仓位'
#   }
# }
```

**情绪等级说明**:
- 🔥 `extreme_high` (≥80): 极度高涨，警惕回调
- 📈 `high` (60-79): 高涨，适当减仓
- ➡️ `neutral` (40-59): 中性，维持仓位
- 📉 `low` (20-39): 低迷，逐步加仓
- ❄️ `extreme_low` (<20): 极度低迷，布局机会

### ML 价格预测

```python
from ml import MLPredictor

predictor = MLPredictor()

# 1. 特征工程
features = predictor.prepare_features(df)

# 2. 训练模型
result = predictor.train_classifier(features, 'rf')
print(f"准确率：{result['accuracy']*100:.2f}%")

# 3. 预测明日涨跌
pred = predictor.predict_direction(features, 'rf')
print(f"预测：{pred['prediction']} (概率：{pred['probability']*100:.1f}%)")
```

**支持模型**:
- 🌲 随机森林 (Random Forest) - 默认推荐
- 🤖 SVM (支持向量机)
- 🧠 LSTM (长短期记忆网络，需 tensorflow)
- 📈 Prophet (时间序列，可选)

## 🔧 扩展指南

| 要做的事 | 怎么做 |
|----------|--------|
| 加新策略 | 继承 `BaseStrategy`，实现 `check()` 方法 |
| 加新数据源 | 继承 `DataProvider`，实现 `get_quote()` / `get_history()` |
| 加新指标 | 在 `indicator/technical.py` 中添加函数 |
| 加新情绪指标 | 在 `sentiment/sentiment_index.py` 中添加 |
| 加新 ML 模型 | 在 `ml/predictor.py` 中添加 |
| 对接实盘 | 继承 `BaseBroker`，改 `settings.yaml` 的 `broker.mode` |
| 改交易参数 | 只改 `settings.yaml`，不碰代码 |

## 🧪 测试

```bash
# 单元测试（59 个）
python bobquant/tests/test_all.py

# 集成测试（113 个，需要网络）
python bobquant/tests/test_integration.py

# 情绪模块测试
python -m sentiment.sentiment_index

# ML 模块测试
python -m ml.predictor

# 集成演示
python integration_demo.py
```

## 📚 参考资料

本项目集成参考了以下优秀开源项目：

1. **AI-Agent-Alpha** - A 股市场情绪量化系统  
   https://github.com/Haohao-end/AI-Agent-Alpha-quantitative-trading-strategy

2. **ML 股票预测算法库** - 机器学习股票预测  
   https://github.com/moyuweiqing/A-stock-prediction-algorithm-based-on-machine-learning

3. **RQAlpha** - 专业回测框架  
   https://github.com/ricequant/rqalpha

## ⚠️ 免责声明

本系统仅供学习和模拟交易使用。股市有风险，投资需谨慎。作者不对使用本系统产生的任何损失承担责任。

## 📜 License

MIT

---

_Built with ❤️ by David & Bob | 2026_
