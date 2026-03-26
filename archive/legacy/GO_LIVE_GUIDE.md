# 🚀 BobQuant v1.0 上线运行指南

**上线时间**: 2026-03-26  
**模式**: 模拟盘自动交易  
**状态**: ✅ 准备就绪

---

## 📋 上线配置

### 已启用功能
- ✅ **ML 预测** - 随机森林涨跌预测 (87% 准确率)
- ✅ **情绪指数** - 市场情绪评分 + 仓位控制
- ✅ **综合决策** - 多信号源投票 + 情绪过滤
- ✅ **LSTM** - TensorFlow 价格预测 (可选)

### 关键参数
```yaml
ml:
  enabled: true
  probability_threshold: 0.6  # 低于 60% 不交易
  
sentiment:
  enabled: true
  position:
    base: 60  # 基础仓位 60%
```

---

## 🚀 启动方式

### 方式 1: 快速启动 (推荐)
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
./start_v1.sh
```

### 方式 2: 直接运行
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python3 -m bobquant.main
```

### 方式 3: 后台运行
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
nohup python3 -m bobquant.main > logs/bobquant_v1.log 2>&1 &
echo $! > bobquant.pid
```

---

## 📊 每日优化流程

### 1. 查看早盘情绪 (每天 9:15 前)
```bash
python3 -c "
from strategy.sentiment_controller import SentimentController
c = SentimentController({})
print(c.get_daily_report())
"
```

### 2. 运行集成测试 (每天 9:25 前)
```bash
python3 test_integration_v1.py
```

### 3. 生成每日报告 (收盘后 15:30)
```bash
python3 daily_report.py
```

### 4. 查看日志
```bash
tail -f logs/bobquant.log
```

---

## 📈 监控指标

### 实时关注
- **情绪评分** - 高于 70 减仓，低于 30 加仓
- **ML 置信度** - 低于 60% 的信号自动过滤
- **仓位上限** - 根据情绪动态调整 (30%-90%)

### 每日统计
- **交易笔数** - 目标 3-10 笔/天
- **胜率** - 目标>55%
- **ML 准确率** - 目标>80%

---

## ⚙️ 优化调整

### 根据表现调整参数

**如果交易过于频繁**:
```yaml
ml:
  probability_threshold: 0.7  # 提高到 70%
```

**如果仓位过高**:
```yaml
sentiment:
  position:
    base: 50  # 降低到 50%
```

**如果 ML 准确率低于 70%**:
```yaml
ml:
  min_train_samples: 100  # 增加训练样本
```

---

## 📁 重要文件

### 核心文件
- `main.py` - 主交易引擎 (已集成 v1.0)
- `strategy/engine.py` - 综合决策引擎
- `config/settings.yaml` - 配置文件

### 日志文件
- `logs/bobquant.log` - 交易日志
- `logs/trade.log` - 交易记录

### 报告文件
- `daily_report.py` - 每日报告生成
- `TEST_REPORT_20260326.md` - 测试报告

---

## ⚠️ 注意事项

### 模拟盘模式
- ✅ 可以大胆测试各种策略
- ✅ 无需担心资金风险
- ⚠️ 仍需监控异常交易

### 自动交易
- ✅ 交易时段自动运行 (9:25-11:35, 12:55-15:05)
- ✅ 每 30 秒检查一次信号
- ⚠️ 每天收盘后检查日志

### 优化决策
- 📊 每天生成优化报告
- 💡 我提供优化建议
- ✅ 你决定是否调整

---

## 🎯 第一周目标

### 观察重点
1. **ML 预测准确率** - 统计每日预测 vs 实际
2. **情绪指数有效性** - 高/低情绪时的市场表现
3. **综合决策效果** - 与传统策略对比

### 预期效果
- 日均交易：3-10 笔
- 胜率：>55%
- ML 准确率：>80%

---

## 🆘 常见问题

**Q: 如何停止运行？**  
A: `Ctrl+C` 或 `kill $(cat bobquant.pid)`

**Q: 如何查看当前状态？**  
A: `tail -f logs/bobquant.log`

**Q: 如何调整参数？**  
A: 编辑 `config/settings.yaml`，重启生效

**Q: 如何查看今日交易？**  
A: `cat logs/trade.log | grep $(date +%Y-%m-%d)`

---

_BobQuant v1.0 - 智能化量化交易系统_  
_上线时间：2026-03-26_  
_Ready to trade! ⚡_
