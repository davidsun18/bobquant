"""
历史数据工具

获取历史行情数据，支持多种时间周期。
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


class GetHistoryDataTool(Tool):
    """历史数据工具
    
    获取历史 K 线数据，支持：
    - 多种周期（1m, 5m, 15m, 30m, 60m, daily, weekly, monthly）
    - 复权处理
    - 时间范围查询
    """
    
    name = "get_history_data"
    description_text = "获取历史 K 线数据（支持多周期、复权）"
    search_hint = "history, kline, candlestick, bar, backtest"
    max_result_size_chars = 500000
    aliases = ["get_kline", "get_bars"]
    
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=True,
            description="股票代码",
        ),
        "period": SchemaField(
            field_type="string",
            required=True,
            description="K 线周期",
            enum=["1m", "5m", "15m", "30m", "60m", "daily", "weekly", "monthly"],
            default="daily",
        ),
        "start_date": SchemaField(
            field_type="string",
            required=True,
            description="开始日期（YYYY-MM-DD）",
        ),
        "end_date": SchemaField(
            field_type="string",
            required=True,
            description="结束日期（YYYY-MM-DD）",
        ),
        "adjust": SchemaField(
            field_type="string",
            required=False,
            description="复权类型",
            enum=["none", "front", "back"],
            default="front",
        ),
        "fields": SchemaField(
            field_type="array",
            required=False,
            description="需要的字段",
            default=["open", "high", "low", "close", "volume"],
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """获取历史数据"""
        symbol = args["symbol"]
        period = args["period"]
        start_date = args["start_date"]
        end_date = args["end_date"]
        adjust = args.get("adjust", "front")
        fields = args.get("fields", ["open", "high", "low", "close", "volume"])
        
        self._log_audit(context, "history_data_query", {
            "symbol": symbol,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
        })
        
        # 进度更新
        self._emit_progress(ToolProgress(
            tool_use_id=context.tool_use_id or "unknown",
            data={
                "stage": "fetching",
                "message": f"获取 {symbol} 历史数据 ({period})",
            }
        ), on_progress)
        
        await asyncio.sleep(0.3)
        
        # 模拟历史数据
        bars = []
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        base_price = 1800.00
        while current_date <= end and len(bars) < 1000:
            # 模拟 K 线数据
            import random
            change = random.uniform(-20, 20)
            base_price += change
            
            bar = {
                "date": current_date.strftime("%Y-%m-%d"),
                "open": round(base_price + random.uniform(-5, 5), 2),
                "high": round(base_price + random.uniform(0, 15), 2),
                "low": round(base_price + random.uniform(-15, 0), 2),
                "close": round(base_price, 2),
                "volume": random.randint(100000, 2000000),
                "amount": round(base_price * random.randint(100000, 2000000), 2),
            }
            
            # 过滤字段
            if fields:
                bar = {k: v for k, v in bar.items() if k in fields or k == "date"}
            
            bars.append(bar)
            current_date += timedelta(days=1)
        
        result = {
            "symbol": symbol,
            "period": period,
            "adjust": adjust,
            "bars": bars,
            "count": len(bars),
            "start_date": start_date,
            "end_date": end_date,
            "timestamp": datetime.now().isoformat(),
        }
        
        return ToolResult(data=result)
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def is_concurrency_safe(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def get_activity_description(
        self,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if input_data:
            return f"获取历史数据：{input_data.get('symbol')} ({input_data.get('period')})"
        return None
