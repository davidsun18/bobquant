"""
止损止盈工具

设置和管理止损止盈订单。
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


class SetStopLossTool(Tool):
    """设置止损工具
    
    为持仓设置止损止盈。
    """
    
    name = "set_stop_loss"
    description_text = "设置止损止盈价格（支持移动止损）"
    search_hint = "stop_loss, stop_profit, risk_management, exit"
    max_result_size_chars = 5000
    aliases = ["set_stop_profit", "set_stop"]
    
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=True,
            description="股票代码",
        ),
        "stop_loss_price": SchemaField(
            field_type="number",
            required=False,
            description="止损价格",
            min_value=0,
        ),
        "stop_profit_price": SchemaField(
            field_type="number",
            required=False,
            description="止盈价格",
            min_value=0,
        ),
        "trailing_stop": SchemaField(
            field_type="boolean",
            required=False,
            description="是否启用移动止损",
            default=False,
        ),
        "trailing_percent": SchemaField(
            field_type="number",
            required=False,
            description="移动止损百分比",
            min_value=0,
            max_value=100,
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """设置止损止盈"""
        symbol = args["symbol"]
        stop_loss = args.get("stop_loss_price")
        stop_profit = args.get("stop_profit_price")
        trailing = args.get("trailing_stop", False)
        trailing_percent = args.get("trailing_percent", 0)
        
        self._log_audit(context, "set_stop_loss", {
            "symbol": symbol,
            "stop_loss": stop_loss,
            "stop_profit": stop_profit,
            "trailing": trailing,
        })
        
        await asyncio.sleep(0.1)
        
        stop_id = f"STOP_{datetime.now().strftime('%Y%m%d%H%M%S')}_{symbol}"
        
        result = {
            "stop_id": stop_id,
            "symbol": symbol,
            "stop_loss_price": stop_loss,
            "stop_profit_price": stop_profit,
            "trailing_stop": trailing,
            "trailing_percent": trailing_percent,
            "status": "active",
            "created_at": datetime.now().isoformat(),
        }
        
        return ToolResult(data=result)
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return False
    
    def is_destructive(self, input_data: Dict[str, Any]) -> bool:
        return True


class GetStopLossTool(Tool):
    """查询止损工具
    
    查询当前的止损止盈设置。
    """
    
    name = "get_stop_loss"
    description_text = "查询当前止损止盈设置"
    search_hint = "stop_loss, stop_profit, query, status"
    max_result_size_chars = 10000
    
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=False,
            description="股票代码（可选，不填返回全部）",
        ),
        "status": SchemaField(
            field_type="string",
            required=False,
            description="状态过滤",
            enum=["all", "active", "triggered", "cancelled"],
            default="active",
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """查询止损止盈"""
        symbol = args.get("symbol")
        status = args.get("status", "active")
        
        await asyncio.sleep(0.1)
        
        # 模拟止损数据
        stops = [
            {
                "stop_id": "STOP_20240115093000_600519",
                "symbol": "600519",
                "stop_loss_price": 1750.00,
                "stop_profit_price": 1900.00,
                "trailing_stop": True,
                "trailing_percent": 5,
                "current_price": 1815.00,
                "status": "active",
                "created_at": "2024-01-15T09:30:00",
            },
        ]
        
        # 过滤
        if symbol:
            stops = [s for s in stops if s["symbol"] == symbol]
        if status != "all":
            stops = [s for s in stops if s["status"] == status]
        
        result = {
            "stops": stops,
            "count": len(stops),
            "timestamp": datetime.now().isoformat(),
        }
        
        return ToolResult(data=result)
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True
