# BobQuant 权限系统

借鉴 Claude Code 的权限管理模式，为 BobQuant 交易系统实现智能风控和审批流程。

## 架构概览

```
permissions/
├── __init__.py          # 模块导出
├── engine.py            # 权限引擎核心
├── rules.py             # 规则匹配引擎
├── classifier.py        # AI 分类器
├── example.py           # 使用示例
└── README.md            # 本文档
```

## 核心组件

### 1. 权限引擎 (PermissionEngine)

位于 `engine.py`，负责整体权限控制流程。

#### PermissionMode 权限模式

| 模式 | 说明 | 使用场景 |
|------|------|----------|
| `ACCEPT_EDITS` | 允许交易，自动执行 | 可信策略、小额交易 |
| `BYPASS_PERMISSIONS` | 跳过风控，完全信任 | 测试环境、紧急操作 |
| `DEFAULT` | 默认询问，需要确认 | 生产环境默认模式 |
| `PLAN` | 计划模式，只规划不执行 | 回测、模拟 |
| `AUTO` | AI 分类，智能决策 | 推荐生产模式 |

#### 优雅期处理 (Grace Period)

- **200ms 防误触机制**：防止快速连续操作导致的误判
- 同一标的的连续请求会触发优雅期检查
- 优雅期内不会重复询问用户

#### 拒绝追踪和降级

- 连续拒绝 3 次后自动降级到更严格模式
- 拒绝计数 5 分钟后自动衰减
- 用户确认成功后重置计数

### 2. 规则匹配引擎 (RuleMatcher)

位于 `rules.py`，实现通配符规则匹配。

#### 规则格式

```
Type(Pattern)
```

- `Type`: 规则类型 (Trade, Risk, Cancel, Modify)
- `Pattern`: 通配符模式

#### 通配符支持

| 符号 | 含义 | 示例 |
|------|------|------|
| `*` | 匹配任意字符 | `Trade(000001.*)` |
| `?` | 匹配单个字符 | `Trade(6000??)` |

#### 预定义规则示例

```python
# 允许特定股票
Trade(000001.*)     # 允许交易平安银行
Trade(600.*)        # 允许交易沪市主板
Trade(000.*)        # 允许交易深市主板

# 需要确认
Trade(300.*)        # 创业板需要确认
Trade(688.*)        # 科创板需要确认

# 风控规则
Risk(*)             # 允许所有风控操作
```

### 3. AI 分类器 (TradeClassifier)

位于 `classifier.py`，智能判断交易风险。

#### 风险评分维度

1. **金额风险** (0-30 分)：交易金额大小
2. **板块风险** (0-20 分)：主板/创业板/科创板
3. **策略风险** (0-20 分)：网格/TWAP/动量等
4. **买卖方向** (0-10 分)：买入风险高于卖出
5. **市场波动** (0-20 分)：涨跌幅、量比
6. **流动性** (0-10 分)：换手率

#### 风险等级

| 等级 | 分数范围 | 决策 |
|------|----------|------|
| LOW | 0-25 | 自动批准 |
| NORMAL | 25-50 | 根据金额决定 |
| HIGH | 50-75 | 需要确认 |
| CRITICAL | 75-100 | 自动拒绝 |

#### 内置规则

- `rule_new_stock_high_limit`: 新股涨停不买入
- `rule_profit_take_auto_approve`: 盈利>20% 卖出自动批准
- `rule_loss_cut_auto_approve`: 止损卖出自动批准
- `rule_grid_trade_auto_approve`: 网格交易自动批准

## 使用示例

### 基础用法

```python
from bobquant.permissions import PermissionEngine, PermissionMode, PermissionRequest

# 创建引擎
engine = PermissionEngine(mode=PermissionMode.AUTO)

# 创建请求
request = PermissionRequest(
    action="trade",
    symbol="sh.600000",
    side="buy",
    quantity=100,
    price=10.5,
)

# 检查权限
response = engine.check_permission(request)

if response.granted:
    # 执行交易
    execute_trade()
elif response.requires_confirmation:
    # 等待用户确认
    confirmed = ask_user(response.reason)
    engine.confirm_permission(request, confirmed)
```

### 规则配置

```python
from bobquant.permissions import RuleMatcher, Rule, RuleAction, create_rule

# 创建匹配器
matcher = RuleMatcher()

# 添加规则
matcher.add_rule(create_rule(
    pattern="Trade(000001.*)",
    action="allow",
    priority=100,
    description="允许交易平安银行"
))

matcher.add_rule(create_rule(
    pattern="Trade(300.*)",
    action="ask",
    priority=80,
    description="创业板需要确认"
))

# 匹配规则
result = matcher.match("000001", "trade")
# {'action': 'allow', 'rule': 'Trade(000001.*)'}
```

### AI 分类器配置

```python
from bobquant.permissions import TradeClassifier

# 创建分类器
classifier = TradeClassifier(
    auto_approve_threshold=10000,   # 1 万以下自动批准
    auto_deny_threshold=100000,     # 10 万以上自动拒绝
)

# 添加自定义规则
classifier.add_custom_rule(rule_profit_take_auto_approve)

# 分类交易
result = classifier.classify(
    symbol="sh.600000",
    side="buy",
    quantity=100,
    price=10.0,
    strategy="grid",
    board_type="主板",
)

print(result)
# {'granted': True, 'reason': '低风险交易', 'risk_level': 'LOW'}
```

### 完整集成

```python
from bobquant.permissions import (
    PermissionEngine, PermissionMode,
    RuleMatcher, DefaultRules,
    TradeClassifier,
)

# 初始化所有组件
engine = PermissionEngine(
    mode=PermissionMode.AUTO,
    grace_period_ms=200.0,
    denial_threshold=3,
)

matcher = RuleMatcher()
matcher.add_rules(DefaultRules.get_default_rules())

classifier = TradeClassifier(auto_approve_threshold=10000)
classifier.add_custom_rule(rule_profit_take_auto_approve)

# 集成分类器到引擎
def classifier_callback(request):
    return classifier.classify(
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        price=request.price or 0,
        strategy=request.strategy,
    )

engine.classifier_callback = classifier_callback

# 使用
request = PermissionRequest(...)
response = engine.check_permission(request, rule_matcher=matcher)
```

## 运行示例

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
python -m permissions.example
```

## 与交易系统集成

### 在 main.py 中集成

```python
from bobquant.permissions import PermissionEngine, PermissionMode

# 初始化权限引擎
permission_engine = PermissionEngine(mode=PermissionMode.AUTO)

# 在交易执行前检查
def execute_order(symbol, side, quantity, price, strategy):
    request = PermissionRequest(
        action="trade",
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        strategy=strategy,
    )
    
    response = permission_engine.check_permission(request)
    
    if not response.granted:
        if response.requires_confirmation:
            # 发送通知等待确认
            send_confirmation_request(response)
            return False
        else:
            logger.warning(f"交易被拒绝：{response.reason}")
            return False
    
    # 执行交易
    return True
```

## 配置建议

### 生产环境

```python
PermissionEngine(
    mode=PermissionMode.AUTO,       # AI 智能决策
    grace_period_ms=200.0,          # 200ms 防误触
    denial_threshold=3,             # 3 次拒绝后降级
)

TradeClassifier(
    auto_approve_threshold=5000,    # 5000 以下自动批准
    auto_deny_threshold=50000,      # 5 万以上自动拒绝
)
```

### 测试环境

```python
PermissionEngine(
    mode=PermissionMode.ACCEPT_EDITS,  # 自动执行
    grace_period_ms=0,                 # 无优雅期
    denial_threshold=999,              # 不降级
)
```

### 保守模式

```python
PermissionEngine(
    mode=PermissionMode.DEFAULT,    # 所有交易都询问
    grace_period_ms=500.0,          # 500ms 优雅期
    denial_threshold=2,             # 2 次拒绝后降级
)
```

## API 参考

### PermissionEngine

| 方法 | 说明 |
|------|------|
| `set_mode(mode)` | 切换权限模式 |
| `check_permission(request, rule_matcher)` | 检查权限 |
| `confirm_permission(request, confirmed)` | 用户确认 |
| `get_status()` | 获取引擎状态 |

### RuleMatcher

| 方法 | 说明 |
|------|------|
| `add_rule(rule)` | 添加规则 |
| `remove_rule(pattern)` | 移除规则 |
| `match(target, action_type)` | 匹配规则 |
| `get_rules()` | 获取所有规则 |

### TradeClassifier

| 方法 | 说明 |
|------|------|
| `classify(...)` | 分类交易请求 |
| `add_custom_rule(func)` | 添加自定义规则 |
| `remove_custom_rule(func)` | 移除自定义规则 |

## 故障排除

### 常见问题

1. **所有交易都被拒绝**
   - 检查权限模式是否为 `DEFAULT` 或 `PLAN`
   - 检查规则匹配器配置
   - 查看拒绝计数是否触发降级

2. **优雅期不生效**
   - 确认 `grace_period_ms > 0`
   - 检查请求的 `action:symbol` 键是否一致

3. **AI 分类器返回异常**
   - 检查分类器回调是否正确设置
   - 查看日志中的详细错误信息

### 日志级别

```python
import logging
logging.getLogger('bobquant.permissions').setLevel(logging.DEBUG)
```

## 扩展开发

### 添加自定义规则

```python
def my_custom_rule(features):
    if features.symbol == "000001" and features.side == "buy":
        return {
            'granted': True,
            'reason': '特殊策略允许',
            'risk_level': 'LOW',
        }
    return None

classifier.add_custom_rule(my_custom_rule)
```

### 添加新的权限模式

```python
class PermissionMode(Enum):
    # ... 现有模式 ...
    CUSTOM_MODE = auto()  # 新 modes

# 在 PermissionEngine 中处理
if self.mode == PermissionMode.CUSTOM_MODE:
    # 自定义逻辑
    pass
```

## 版本历史

- **v1.0** (2026-04-11): 初始版本
  - 实现 5 种权限模式
  - 通配符规则匹配
  - AI 风险分类器
  - 优雅期和降级机制
