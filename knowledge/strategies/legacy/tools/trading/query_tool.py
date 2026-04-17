"""
订单查询工具

用于查询订单状态和历史。
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import asyncio

from ..base import (
    Tool,
    ToolContext,
    ToolResult,
    ToolProgress,
)
from ..schema import to_json_schema, SchemaField


class GetOrderTool(Tool):
    """单个订单查询工具"""
    
    name = "get_order"
    description_text = "查询单个订单的详细信息和状态"
    search_hint = "order, status, query, trade"
    max_result_size_chars = 10000
    
    input_schema = to_json_schema({
        "order_id": SchemaField(
            field_type="string",
            required=True,
            description="订单 ID",
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """查询订单"""
        order_id = args["order_id"]
        
        await asyncio.sleep(0.1)
        
        # 模拟订单数据
        result = {
            "order_id": order_id,
            "symbol": "600519",
            "side": "buy",
            "quantity": 100,
            "price": 1800.00,
            "order_type": "limit",
            "status": "filled",
            "filled_quantity": 100,
            "filled_price": 1798.50,
            "create_time": "2024-01-15T09:30:00",
            "update_time": "2024-01-15T09:30:05",
        }
        
        return ToolResult(data=result)
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True


class GetOrdersTool(Tool):
    """订单列表查询工具"""
    
    name = "get_orders"
    description_text = "查询订单列表（支持状态、时间过滤）"
    search_hint = "orders, list, history, trades"
    max_result_size_chars = 100000
    
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=False,
            description="股票代码（可选）",
        ),
        "status": SchemaField(
            field_type="string",
            required=False,
            description="订单状态",
            enum=["all", "pending", "filled", "cancelled", "rejected"],
            default="all",
        ),
        "start_time": SchemaField(
            field_type="string",
            required=False,
            description="开始时间（ISO 格式）",
        ),
        "end_time": SchemaField(
            field_type="string",
            required=False,
            description="结束时间（ISO 格式）",
        ),
        "limit": SchemaField(
            field_type="integer",
            required=False,
            description="返回数量限制",
            default=100,
            min_value=1,
            max_value=1000,
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """查询订单列表"""
        symbol = args.get("symbol")
        status = args.get("status", "all")
        limit = args.get("limit", 100)
        
        await asyncio.sleep(0.2)
        
        # 模拟订单列表
        orders = [
            {
                "order_id": "ORD_20240115093000_600519",
                "symbol": "600519",
                "side": "buy",
                "quantity": 100,
                "price": 1800.00,
                "status": "filled",
                "create_time": "2024-01-15T09:30:00",
            },
            {
                "order_id": "ORD_20240115100000_000858",
                "symbol": "000858",
                "side": "sell",
                "quantity": 200,
                "price": 148.00,
                "status": "pending",
                "create_time": "2024-01-15T10:00:00",
            },
        ]
        
        # 过滤
        if symbol:
            orders = [o for o in orders if o["symbol"] == symbol]
        if status != "all":
            orders = [o for o in orders if o["status"] == status]
        
        # 限制数量
        orders = orders[:limit]
        
        result = {
            "orders": orders,
            "total": len(orders),
            "timestamp": datetime.now().isoformat(),
        }
        
        return ToolResult(data=result)
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def is_concurrency_safe(self, input_data: Dict[str, Any]) -> bool:
        return True
