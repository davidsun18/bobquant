"""
风险检查工具

执行交易前的风险检查，确保符合风控规则。
"""

from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import asyncio

from ..base import (
    Tool,
    ToolContext,
    ToolResult,
    ToolProgress,
    PermissionResult,
)
from ..schema import to_json_schema, SchemaField


class RiskCheckTool(Tool):
    """风险检查工具
    
    在交易执行前进行风险检查，包括：
    - 仓位限制
    - 单日交易次数
    - 风险敞口
    - 黑名单检查
    """
    
    name = "risk_check"
    description_text = "执行交易前风险检查（仓位、次数、敞口等）"
    search_hint = "risk, check, compliance, limit, validation"
    max_result_size_chars = 10000
    aliases = ["check_risk", "validate_risk"]
    
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=True,
            description="股票代码",
        ),
        "side": SchemaField(
            field_type="string",
            required=True,
            description="买卖方向",
            enum=["buy", "sell"],
        ),
        "quantity": SchemaField(
            field_type="integer",
            required=True,
            description="数量",
            min_value=1,
        ),
        "price": SchemaField(
            field_type="number",
            required=False,
            description="价格",
            min_value=0,
        ),
        "check_level": SchemaField(
            field_type="string",
            required=False,
            description="检查级别",
            enum=["basic", "strict", "full"],
            default="full",
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """执行风险检查"""
        symbol = args["symbol"]
        side = args["side"]
        quantity = args["quantity"]
        price = args.get("price", 0)
        check_level = args.get("check_level", "full")
        
        estimated_value = quantity * (price or 10)
        
        self._log_audit(context, "risk_check", {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "estimated_value": estimated_value,
            "check_level": check_level,
        })
        
        # 进度更新
        self._emit_progress(ToolProgress(
            tool_use_id=context.tool_use_id or "unknown",
            data={
                "stage": "checking",
                "message": f"风险检查：{symbol}",
            }
        ), on_progress)
        
        await asyncio.sleep(0.1)
        
        # 模拟风险检查
        checks = {
            "position_limit": {"passed": True, "message": "未超过仓位限制"},
            "daily_trade_limit": {"passed": True, "message": "未超过单日交易次数"},
            "risk_exposure": {"passed": True, "message": "风险敞口在可控范围"},
            "blacklist": {"passed": True, "message": "股票不在黑名单"},
            "liquidity": {"passed": True, "message": "流动性充足"},
        }
        
        all_passed = all(check["passed"] for check in checks.values())
        
        result = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "estimated_value": estimated_value,
            "check_level": check_level,
            "passed": all_passed,
            "checks": checks,
            "timestamp": datetime.now().isoformat(),
        }
        
        if not all_passed:
            failed_checks = [k for k, v in checks.items() if not v["passed"]]
            result["failed_checks"] = failed_checks
        
        return ToolResult(data=result)
    
    async def check_permissions(
        self,
        input_data: Dict[str, Any],
        context: ToolContext,
    ) -> PermissionResult:
        """风险检查工具本身不需要特殊权限"""
        return PermissionResult(
            behavior="allow",
            updated_input=input_data,
        )
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True


class PositionLimitTool(Tool):
    """仓位限制检查工具
    
    检查当前仓位是否超过限制。
    """
    
    name = "position_limit"
    description_text = "检查仓位限制（单只股票、行业、总仓位）"
    search_hint = "position, limit, exposure, allocation"
    max_result_size_chars = 5000
    
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=False,
            description="股票代码（可选，不填检查总体）",
        ),
        "check_type": SchemaField(
            field_type="string",
            required=True,
            description="检查类型",
            enum=["single", "industry", "total"],
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """检查仓位限制"""
        symbol = args.get("symbol")
        check_type = args["check_type"]
        
        await asyncio.sleep(0.1)
        
        # 模拟仓位限制数据
        result = {
            "check_type": check_type,
            "symbol": symbol,
            "limits": {
                "single_stock_max": 0.20,  # 单只股票最大 20%
                "industry_max": 0.40,      # 单行业最大 40%
                "total_position": 0.95,    # 总仓位最大 95%
            },
            "current": {
                "single_stock": 0.15 if symbol else 0,
                "industry": 0.30,
                "total": 0.75,
            },
            "within_limit": True,
            "available_space": {
                "single_stock": 0.05 if symbol else 0.20,
                "industry": 0.10,
                "total": 0.20,
            },
            "timestamp": datetime.now().isoformat(),
        }
        
        return ToolResult(data=result)
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True
