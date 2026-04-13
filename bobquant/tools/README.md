# BobQuant 工具系统

重构后的工具系统，借鉴 Claude Code 架构设计。

---

## 📁 模块结构

```
tools/
├── __init__.py              # 包导出
├── base.py                  # 工具基类
├── registry.py              # 工具注册表
├── schema.py                # Schema 验证
├── audit.py                 # 审计日志
├── trading/                 # 交易工具
│   ├── order_tool.py        # 下单/撤单
│   ├── position_tool.py     # 持仓查询
│   └── query_tool.py        # 订单查询
├── data/                    # 数据工具
│   ├── market_data.py       # 行情数据
│   ├── history_data.py      # 历史数据
│   └── financial_data.py    # 财务数据
└── risk/                    # 风控工具
    ├── risk_check.py        # 风险检查
    ├── stop_loss.py         # 止损止盈
    └── risk_metrics.py      # 风险指标
```

---

## 🚀 快速开始

### 1. 使用工具

```python
import asyncio
from bobquant.tools import get_registry, ToolContext

async def main():
    registry = get_registry()
    
    # 获取工具
    tool = registry.get("place_order")
    
    # 调用工具
    context = ToolContext(options={"mode": "simulation"})
    result = await tool.call(
        args={"symbol": "600519", "side": "buy", "quantity": 100},
        context=context
    )
    
    print(result.data)

asyncio.run(main())
```

### 2. 创建自定义工具

```python
from bobquant.tools import Tool, ToolContext, ToolResult, to_json_schema, SchemaField

class MyCustomTool(Tool):
    name = "my_custom_tool"
    description_text = "我的自定义工具"
    
    input_schema = to_json_schema({
        "symbol": SchemaField(field_type="string", required=True),
        "quantity": SchemaField(field_type="integer", min_value=1),
    })
    
    async def call(self, args, context, on_progress=None):
        result = {"status": "success"}
        return ToolResult(data=result)

# 注册工具
from bobquant.tools import register_tool
register_tool(category="trading")(MyCustomTool)
```

---

## 📖 工具列表

### 交易工具

| 工具名 | 描述 |
|--------|------|
| `place_order` | 下单（买入/卖出） |
| `cancel_order` | 撤单 |
| `get_position` | 查询持仓 |
| `get_order` | 查询单个订单 |
| `get_orders` | 查询订单列表 |

### 数据工具

| 工具名 | 描述 |
|--------|------|
| `get_market_data` | 获取行情数据 |
| `get_realtime_data` | 获取实时行情 |
| `get_history_data` | 获取历史 K 线 |
| `get_financial_data` | 获取财务数据 |

### 风控工具

| 工具名 | 描述 |
|--------|------|
| `risk_check` | 风险检查 |
| `position_limit` | 仓位限制检查 |
| `set_stop_loss` | 设置止损止盈 |
| `get_stop_loss` | 查询止损设置 |
| `get_risk_metrics` | 计算风险指标 |

---

## 💡 使用示例

### 示例 1: 下单

```python
from bobquant.tools.trading import place_order

result = await place_order(
    symbol="600519",
    side="buy",
    quantity=100,
    price=1800.0,
    order_type="limit"
)

print(f"订单 ID: {result['order_id']}")
```

### 示例 2: 查询持仓

```python
from bobquant.tools.trading import get_position

position = await get_position(symbol="600519")

print(f"持仓：{position['volume']}股")
print(f"成本：{position['cost_price']}")
```

### 示例 3: 风险检查

```python
from bobquant.tools.risk import risk_check

result = await risk_check(
    symbol="600519",
    quantity=1000,
    price=1800.0,
    side="buy"
)

if result['passed']:
    print("风控通过")
else:
    print(f"风控失败：{result['message']}")
```

---

## 🔧 核心组件

### 工具基类

```python
class Tool:
    name: str
    description_text: str
    input_schema: dict
    
    async def call(args, context, on_progress=None) -> ToolResult
    async def check_permissions(input_data, context) -> PermissionResult
```

### 工具注册表

```python
registry = get_registry()

# 注册工具
registry.register(MyTool, category="trading")

# 获取工具
tool = registry.get("my_tool")

# 列出工具
tools = registry.list_tools(category="trading")
```

### Schema 验证

```python
from bobquant.tools import to_json_schema, SchemaField

input_schema = to_json_schema({
    "symbol": SchemaField(field_type="string", required=True),
    "quantity": SchemaField(field_type="integer", min_value=1),
    "price": SchemaField(field_type="number", min_value=0),
})
```

### 审计日志

```python
from bobquant.tools import get_audit_logger

logger = get_audit_logger()

# 记录操作
logger.log(
    action="place_order",
    tool_name="place_order",
    status="success",
    duration_ms=100.5
)

# 查询日志
logs = logger.query(tool_name="place_order", limit=100)
```

---

## 📚 相关文档

- [工具迁移指南](./MIGRATION.md)
- [重构总结](./REFACTOR_SUMMARY.md)

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
