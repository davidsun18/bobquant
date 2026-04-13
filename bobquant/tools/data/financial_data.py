"""
财务数据工具

获取股票财务数据、基本面信息。
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


class GetFinancialDataTool(Tool):
    """财务数据工具
    
    获取股票财务数据，包括：
    - 利润表
    - 资产负债表
    - 现金流量表
    - 财务指标
    """
    
    name = "get_financial_data"
    description_text = "获取股票财务数据（报表、指标、基本面）"
    search_hint = "financial, fundamental, earnings, revenue, pe"
    max_result_size_chars = 100000
    aliases = ["get_fundamental", "get_financials"]
    
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=True,
            description="股票代码",
        ),
        "report_type": SchemaField(
            field_type="string",
            required=False,
            description="报表类型",
            enum=["income", "balance", "cashflow", "all"],
            default="all",
        ),
        "period": SchemaField(
            field_type="string",
            required=False,
            description="报告期",
            enum=["annual", "quarterly"],
            default="annual",
        ),
        "years": SchemaField(
            field_type="integer",
            required=False,
            description="年数（最近 N 年）",
            default=3,
            min_value=1,
            max_value=10,
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """获取财务数据"""
        symbol = args["symbol"]
        report_type = args.get("report_type", "all")
        period = args.get("period", "annual")
        years = args.get("years", 3)
        
        self._log_audit(context, "financial_data_query", {
            "symbol": symbol,
            "report_type": report_type,
        })
        
        await asyncio.sleep(0.2)
        
        # 模拟财务数据
        result = {
            "symbol": symbol,
            "company_name": "示例公司",
            "report_type": report_type,
            "period": period,
            "data": {
                "income": {
                    "years": [2023, 2022, 2021],
                    "revenue": [10000000000, 9000000000, 8000000000],
                    "net_profit": [2000000000, 1800000000, 1500000000],
                    "gross_margin": [0.45, 0.43, 0.42],
                    "net_margin": [0.20, 0.19, 0.18],
                },
                "balance": {
                    "total_assets": [50000000000, 45000000000, 40000000000],
                    "total_liabilities": [20000000000, 18000000000, 16000000000],
                    "equity": [30000000000, 27000000000, 24000000000],
                },
                "cashflow": {
                    "operating_cashflow": [2500000000, 2200000000, 2000000000],
                    "investing_cashflow": [-1000000000, -800000000, -600000000],
                    "financing_cashflow": [-500000000, -400000000, -300000000],
                },
                "indicators": {
                    "pe_ratio": 15.5,
                    "pb_ratio": 2.3,
                    "ps_ratio": 3.1,
                    "roe": 0.15,
                    "roa": 0.08,
                    "debt_to_equity": 0.67,
                    "current_ratio": 1.5,
                    "quick_ratio": 1.2,
                },
            },
            "timestamp": datetime.now().isoformat(),
        }
        
        return ToolResult(data=result)
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def is_concurrency_safe(self, input_data: Dict[str, Any]) -> bool:
        return True
