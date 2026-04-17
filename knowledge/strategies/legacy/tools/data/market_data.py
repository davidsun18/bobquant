"""
行情数据工具

获取实时和历史行情数据。
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
import asyncio

from ..base import (
    Tool,
    ToolContext,
    ToolResult,
    ToolProgress,
)
from ..schema import to_json_schema, SchemaField


class GetMarketDataTool(Tool):
    """行情数据工具
    
    获取股票/期货的行情数据，包括：
    - 开盘价、收盘价
    - 最高价、最低价
    - 成交量、成交额
    - 涨跌幅
    """
    
    name = "get_market_data"
    description_text = "获取股票或期货的行情数据（OHLCV、涨跌幅等）"
    search_hint = "market, data, quote, price, stock"
    max_result_size_chars = 50000
    aliases = ["get_quote", "get_price"]
    
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=True,
            description="股票代码",
        ),
        "fields": SchemaField(
            field_type="array",
            required=False,
            description="需要的字段",
            default=["open", "high", "low", "close", "volume", "amount"],
        ),
        "date": SchemaField(
            field_type="string",
            required=False,
            description="日期（YYYY-MM-DD，默认今天）",
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """获取行情数据"""
        symbol = args["symbol"]
        fields = args.get("fields", ["open", "high", "low", "close", "volume", "amount"])
        date = args.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        self._log_audit(context, "market_data_query", {
            "symbol": symbol,
            "date": date,
        })
        
        await asyncio.sleep(0.1)
        
        # 模拟行情数据
        result = {
            "symbol": symbol,
            "date": date,
            "data": {
                "open": 1800.00,
                "high": 1820.00,
                "low": 1795.00,
                "close": 1815.00,
                "volume": 1234567,
                "amount": 2234567890.00,
                "change": 15.00,
                "change_percent": 0.0083,
                "pre_close": 1800.00,
            },
            "timestamp": datetime.now().isoformat(),
        }
        
        # 过滤字段
        if fields:
            filtered_data = {k: v for k, v in result["data"].items() if k in fields}
            result["data"] = filtered_data
        
        return ToolResult(data=result)
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def is_concurrency_safe(self, input_data: Dict[str, Any]) -> bool:
        return True


class GetRealTimeDataTool(Tool):
    """实时行情工具
    
    获取实时行情数据（tick 级）。
    """
    
    name = "get_realtime_data"
    description_text = "获取实时行情数据（买一卖一、最新价等）"
    search_hint = "realtime, tick, bid, ask, live"
    max_result_size_chars = 10000
    aliases = ["get_tick", "get_realtime_quote"]
    
    input_schema = to_json_schema({
        "symbols": SchemaField(
            field_type="array",
            required=True,
            description="股票代码列表",
            items=SchemaField(field_type="string"),
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """获取实时行情"""
        symbols = args["symbols"]
        
        await asyncio.sleep(0.05)
        
        # 模拟实时数据
        data = {}
        for symbol in symbols:
            data[symbol] = {
                "last_price": 1815.00,
                "open": 1800.00,
                "high": 1820.00,
                "low": 1795.00,
                "bid_price": 1814.50,
                "bid_volume": 100,
                "ask_price": 1815.50,
                "ask_volume": 150,
                "volume": 1234567,
                "amount": 2234567890.00,
                "timestamp": datetime.now().isoformat(),
            }
        
        return ToolResult(data={
            "data": data,
            "count": len(symbols),
        })
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def is_concurrency_safe(self, input_data: Dict[str, Any]) -> bool:
        return True
