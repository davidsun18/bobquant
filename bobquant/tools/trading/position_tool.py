"""
持仓查询工具

用于查询当前持仓信息。
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
from ..schema import SchemaBuilder, to_json_schema, SchemaField


class GetPositionTool(Tool):
    """持仓查询工具
    
    查询当前持仓情况，包括：
    - 持仓数量
    - 成本价
    - 当前价
    - 盈亏
    """
    
    name = "get_position"
    description_text = "查询当前持仓信息（数量、成本、盈亏等）"
    search_hint = "position, holding, portfolio, stock"
    max_result_size_chars = 50000
    aliases = ["query_position", "get_holdings"]
    
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=False,
            description="股票代码（可选，不填返回全部持仓）",
        ),
        "include_details": SchemaField(
            field_type="boolean",
            required=False,
            description="是否包含详细信息",
            default=True,
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """查询持仓"""
        symbol = args.get("symbol")
        include_details = args.get("include_details", True)
        
        self._log_audit(context, "position_query", {
            "symbol": symbol or "all",
            "include_details": include_details,
        })
        
        try:
            # 模拟持仓数据（实际应从交易系统获取）
            await asyncio.sleep(0.1)
            
            # 示例持仓数据
            positions = [
                {
                    "symbol": "600519",
                    "name": "贵州茅台",
                    "quantity": 100,
                    "cost_price": 1800.00,
                    "current_price": 1850.00,
                    "market_value": 185000.00,
                    "profit_loss": 5000.00,
                    "profit_rate": 0.0278,
                },
                {
                    "symbol": "000858",
                    "name": "五粮液",
                    "quantity": 500,
                    "cost_price": 150.00,
                    "current_price": 145.00,
                    "market_value": 72500.00,
                    "profit_loss": -2500.00,
                    "profit_rate": -0.0333,
                },
            ]
            
            # 过滤
            if symbol:
                positions = [p for p in positions if p["symbol"] == symbol]
            
            # 计算汇总
            total_market_value = sum(p["market_value"] for p in positions)
            total_profit_loss = sum(p["profit_loss"] for p in positions)
            total_cost = total_market_value - total_profit_loss
            
            result = {
                "positions": positions if include_details else [],
                "summary": {
                    "total_market_value": total_market_value,
                    "total_cost": total_cost,
                    "total_profit_loss": total_profit_loss,
                    "total_profit_rate": total_profit_loss / total_cost if total_cost > 0 else 0,
                    "position_count": len(positions),
                },
                "timestamp": datetime.now().isoformat(),
            }
            
            return ToolResult(data=result)
            
        except Exception as e:
            self._log_audit(context, "position_query_failed", {
                "error": str(e),
            })
            raise
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def is_concurrency_safe(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def get_activity_description(
        self,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if input_data and input_data.get("symbol"):
            return f"查询持仓：{input_data['symbol']}"
        return "查询全部持仓"
