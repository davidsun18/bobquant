# BobQuant 工具系统迁移指南

从旧版工具迁移到新的工具系统。

## 迁移概述

新版工具系统借鉴 Claude Code 的架构，提供：
- ✅ 统一的工具基类
- ✅ Schema 验证
- ✅ 权限检查
- ✅ 审计日志
- ✅ 工具注册表

## 迁移步骤

### 步骤 1: 更新导入

**旧版:**
```python
from bobquant.core.executor import OrderExecutor
from bobquant.data.provider import DataProvider
```

**新版:**
```python
from bobquant.tools import Tool, ToolContext, ToolResult
from bobquant.tools.trading import PlaceOrderTool
from bobquant.tools.data import GetMarketDataTool
```

### 步骤 2: 重构为工具类

**旧版 (函数式):**
```python
async def place_order(symbol, side, quantity, price=None):
    # 验证
    if quantity <= 0:
        raise ValueError("数量必须大于 0")
    
    # 执行
    order_id = await executor.submit(symbol, side, quantity, price)
    return {"order_id": order_id, "status": "submitted"}
```

**新版 (类式):**
```python
from bobquant.tools import Tool, ToolResult, to_json_schema, SchemaField

class PlaceOrderTool(Tool):
    name = "place_order"
    description_text = "执行交易订单"
    
    input_schema = to_json_schema({
        "symbol": SchemaField(field_type="string", required=True),
        "side": SchemaField(field_type="string", enum=["buy", "sell"]),
        "quantity": SchemaField(field_type="integer", min_value=1),
        "price": SchemaField(field_type="number", required=False),
    })
    
    async def call(self, args, context, on_progress=None):
        symbol = args["symbol"]
        side = args["side"]
        quantity = args["quantity"]
        price = args.get("price")
        
        # 执行逻辑
        order_id = await self._execute_order(symbol, side, quantity, price)
        
        return ToolResult(data={
            "order_id": order_id,
            "status": "submitted",
        })
```

### 步骤 3: 添加权限检查

**新版新增:**
```python
async def check_permissions(self, input_data, context):
    quantity = input_data.get("quantity", 0)
    price = input_data.get("price", 0)
    estimated_value = quantity * (price or 10)
    
    # 大额订单需要确认
    if estimated_value > 100000:
        return PermissionResult(
            behavior="ask",
            message=f"大额订单（约{estimated_value:,.0f}元），请确认",
        )
    
    return PermissionResult(behavior="allow")
```

### 步骤 4: 添加审计日志

**新版新增:**
```python
async def call(self, args, context, on_progress=None):
    # 记录开始
    self._log_audit(context, "order_start", {
        "symbol": args["symbol"],
        "side": args["side"],
        "quantity": args["quantity"],
    })
    
    try:
        # 执行逻辑
        result = await self._execute(...)
        
        # 记录完成
        self._log_audit(context, "order_completed", {
            "order_id": result["order_id"],
        })
        
        return ToolResult(data=result)
    except Exception as e:
        # 记录失败
        self._log_audit(context, "order_failed", {
            "error": str(e),
        })
        raise
```

### 步骤 5: 注册工具

**方式 1: 装饰器**
```python
from bobquant.tools import register_tool

@register_tool(category="trading")
class PlaceOrderTool(Tool):
    ...
```

**方式 2: 手动注册**
```python
from bobquant.tools import get_registry

registry = get_registry()
registry.register(PlaceOrderTool, category="trading")
```

### 步骤 6: 使用工具注册表调用

**旧版:**
```python
result = await place_order("600519", "buy", 100)
```

**新版:**
```python
from bobquant.tools import get_registry, ToolContext

registry = get_registry()
tool = registry.get("place_order")

context = ToolContext(
    options={"mode": "live"},
    tool_use_id="order_001",
)

result = await tool.call({
    "symbol": "600519",
    "side": "buy",
    "quantity": 100,
}, context)

print(result.data)
```

## 工具映射表

| 旧版模块 | 旧版函数/类 | 新版工具 |
|----------|-------------|----------|
| `core.executor` | `OrderExecutor.submit` | `PlaceOrderTool` |
| `core.executor` | `OrderExecutor.cancel` | `CancelOrderTool` |
| `core.account` | `Account.get_position` | `GetPositionTool` |
| `data.provider` | `DataProvider.get_market_data` | `GetMarketDataTool` |
| `data.provider` | `DataProvider.get_history` | `GetHistoryDataTool` |
| `risk_manager` | `RiskManager.check` | `RiskCheckTool` |
| `risk_manager` | `RiskManager.set_stop_loss` | `SetStopLossTool` |

## 完整迁移示例

### 示例：行情数据获取

**旧版代码:**
```python
# data/fetcher.py
async def get_market_data(symbol, date=None):
    """获取行情数据"""
    if not symbol:
        raise ValueError("股票代码不能为空")
    
    date = date or datetime.now().strftime("%Y-%m-%d")
    
    # 从数据源获取
    data = await source.fetch(symbol, date)
    
    return {
        "symbol": symbol,
        "date": date,
        "open": data["open"],
        "high": data["high"],
        "low": data["low"],
        "close": data["close"],
        "volume": data["volume"],
    }

# 使用
data = await get_market_data("600519")
```

**新版代码:**
```python
# tools/data/market_data.py
from bobquant.tools import Tool, ToolResult, to_json_schema, SchemaField

class GetMarketDataTool(Tool):
    name = "get_market_data"
    description_text = "获取股票行情数据"
    
    input_schema = to_json_schema({
        "symbol": SchemaField(field_type="string", required=True),
        "date": SchemaField(field_type="string", required=False),
        "fields": SchemaField(field_type="array", required=False),
    })
    
    async def call(self, args, context, on_progress=None):
        symbol = args["symbol"]
        date = args.get("date", datetime.now().strftime("%Y-%m-%d"))
        fields = args.get("fields", ["open", "high", "low", "close", "volume"])
        
        self._log_audit(context, "market_data_query", {
            "symbol": symbol,
            "date": date,
        })
        
        # 获取数据
        data = await self._fetch_from_source(symbol, date)
        
        result = {
            "symbol": symbol,
            "date": date,
            "data": {k: v for k, v in data.items() if k in fields},
            "timestamp": datetime.now().isoformat(),
        }
        
        return ToolResult(data=result)
    
    def is_read_only(self, input_data):
        return True

# 使用
from bobquant.tools import get_registry, ToolContext

registry = get_registry()
tool = registry.get("get_market_data")

context = ToolContext(options={}, tool_use_id="req_001")
result = await tool.call({
    "symbol": "600519",
    "fields": ["open", "close", "volume"],
}, context)

print(result.data)
```

## 迁移检查清单

- [ ] 更新所有导入语句
- [ ] 将函数重构为工具类
- [ ] 定义输入 Schema
- [ ] 实现权限检查
- [ ] 添加审计日志
- [ ] 注册工具到注册表
- [ ] 更新调用代码使用工具注册表
- [ ] 测试所有工具功能
- [ ] 更新文档

## 回滚方案

如果迁移后遇到问题，可以：

1. 保留旧版代码在 `archive/legacy/` 目录
2. 使用功能开关控制新旧版本
3. 逐步迁移，先迁移非关键工具

```python
# config.py
USE_NEW_TOOL_SYSTEM = True

# usage.py
if USE_NEW_TOOL_SYSTEM:
    tool = registry.get("place_order")
    result = await tool.call(args, context)
else:
    result = await legacy_place_order(**args)
```

## 获取帮助

迁移过程中遇到问题：

1. 查看 [README.md](./README.md) 了解工具系统
2. 查看示例代码 `tests/` 目录
3. 检查审计日志排查问题
