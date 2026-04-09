# BobQuant 集成计划 - 4 个核心模块

**创建时间**: 2026-04-10 07:50  
**状态**: 🚧 进行中  

---

## ✅ 已完成

### 1. 三重障碍法标签生成器
- **文件**: `bobquant/ml/features.py`
- **状态**: ✅ 已创建并集成到 bobquant 模块
- **下一步**: 更新 `predictor.py` 使用新的标签生成方法

### 2. TWAP/VWAP 执行器
- **文件**: `order_execution/twap_executor.py`
- **状态**: ✅ 已创建（独立模块）
- **下一步**: 集成到 `bobquant/core/executor.py`

### 3. 风险管理器
- **文件**: `risk_management/risk_manager.py`
- **状态**: ✅ 已创建（独立模块）
- **下一步**: 集成到 `bobquant/strategy/engine.py`

---

## 🔧 立即集成任务

### 任务 1: 更新 ML 标签生成 (优先级：⭐⭐⭐)

**当前代码** (`bobquant/ml/predictor.py` 第 111 行):
```python
# 7. 目标变量 (T+1 是否上涨)
features['target'] = (df['close'].shift(-1) > df['close']).astype(int)
```

**改进为三重障碍法**:
```python
from bobquant.ml.features import apply_triple_barrier

# 生成事件
events = df[['close']].copy()

# 应用三重障碍法
labels = apply_triple_barrier(
    close=df['close'],
    high=df['high'],
    low=df['low'],
    events=events,
    pt_sl=(1.0, 1.0),
    t1=pd.Timedelta('5D'),
    min_ret=0.02
)

features['target'] = labels
```

**预期效果**:
- 标签更符合实际交易场景（考虑止盈/止损）
- 提升 ML 模型预测的实用性

---

### 任务 2: 集成 TWAP 执行器 (优先级：⭐⭐)

**当前代码** (`bobquant/core/executor.py`):
```python
def execute_order(self, code, action, price, shares):
    # 直接下单
    self.account.execute(code, action, price, shares)
```

**改进为 TWAP 执行**:
```python
from bobquant.order_execution.twap_executor import TWAPExecutor, TWAPOrder, OrderSide

def execute_order(self, code, action, price, shares, use_twap=False):
    if use_twap and shares > 10000:  # 大单使用 TWAP
        twap_order = TWAPOrder(
            symbol=code,
            total_quantity=shares,
            duration_minutes=10,
            num_slices=5,
            side=OrderSide.BUY if action == 'buy' else OrderSide.SELL
        )
        order_id = self.twap_exec.submit_twap(twap_order)
        return {'status': 'twap_submitted', 'order_id': order_id}
    else:
        # 直接下单
        self.account.execute(code, action, price, shares)
```

**预期效果**:
- 大单拆分，降低市场冲击
- 提升实盘执行质量

---

### 任务 3: 集成新风险管理器 (优先级：⭐⭐⭐)

**当前代码** (`bobquant/strategy/engine.py`):
```python
class RiskManager:
    def check(self, code, pos, current_price):
        # 简单的止盈止损检查
        if current_price < pos['avg_price'] * 0.95:
            return {'action': 'sell', 'reason': '止损'}
```

**改进为综合风控**:
```python
from bobquant.risk_management.risk_manager import RiskManager, RiskLimits

# 初始化
limits = RiskLimits(
    max_position_value=500000,
    max_portfolio_exposure=2000000,
    max_drawdown=0.10,
    max_daily_loss=50000
)
self.risk_mgr = RiskManager(limits, initial_capital=1000000)

# 检查订单
def check_order(self, code, side, quantity, price):
    allowed, reason = self.risk_mgr.check_order(code, side, quantity, price)
    return {'action': 'sell' if allowed else 'hold', 'reason': reason}
```

**预期效果**:
- 8 项风控检查，避免违规交易
- 实时回撤和亏损监控

---

## 📋 集成时间表

| 任务 | 优先级 | 预计时间 | 状态 |
|------|--------|---------|------|
| ML 标签生成更新 | ⭐⭐⭐ | 30 分钟 | ⏳ 待执行 |
| TWAP 执行器集成 | ⭐⭐ | 45 分钟 | ⏳ 待执行 |
| 新风险管理器集成 | ⭐⭐⭐ | 30 分钟 | ⏳ 待执行 |
| 单元测试 | ⭐⭐ | 60 分钟 | ⏳ 待执行 |
| 模拟盘验证 | ⭐⭐⭐ | 1 天 | ⏳ 待执行 |

---

## 🎯 验收标准

### ML 标签生成
- [ ] `predictor.py` 使用三重障碍法生成标签
- [ ] 标签分布合理（正负样本平衡）
- [ ] 回测显示 ML 策略效果提升

### TWAP 执行器
- [ ] 大单（>10000 股）自动使用 TWAP
- [ ] 执行日志显示拆分订单详情
- [ ] 冲击成本降低（对比直接下单）

### 风险管理器
- [ ] 每笔订单通过风控检查
- [ ] 回撤超限时自动停止交易
- [ ] 风控日志完整记录

---

## 📝 执行日志

### 2026-04-10 07:45
- ✅ 创建 `bobquant/ml/features.py` (三重障碍法)
- ⏳ 等待更新 `predictor.py`

### 2026-04-10 07:50
- 📋 创建本集成计划
- ⏳ 等待用户确认是否立即执行集成

---

*最后更新：2026-04-10 07:50*
