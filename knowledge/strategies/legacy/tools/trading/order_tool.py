"""
交易订单工具

实现下单和撤单功能，借鉴 Claude Code 的工具设计模式。
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import logging

from ..base import (
    Tool,
    ToolContext,
    ToolResult,
    ToolProgress,
    ValidationResult,
    PermissionResult,
    ValidationError,
    ExecutionError,
)
from ..schema import SchemaBuilder, validate_schema, to_json_schema, SchemaField


# ==================== 下单工具 ====================

class PlaceOrderTool(Tool):
    """下单工具
    
    用于执行股票/期货下单操作。
    
    权限要求：
    - 需要交易权限
    - 大额订单需要额外确认
    """
    
    name = "place_order"
    description_text = "执行交易订单（买入/卖出股票或期货）"
    search_hint = "trading, order, buy, sell, stock"
    max_result_size_chars = 10000
    aliases = ["submit_order", "execute_order"]
    
    # 定义输入 Schema
    input_schema = to_json_schema({
        "symbol": SchemaField(
            field_type="string",
            required=True,
            description="股票代码",
            min_length=4,
            max_length=10,
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
            description="数量（股/手）",
            min_value=1,
        ),
        "price": SchemaField(
            field_type="number",
            required=False,
            description="限价（可选，市价单不填）",
            min_value=0,
        ),
        "order_type": SchemaField(
            field_type="string",
            required=True,
            description="订单类型",
            enum=["market", "limit", "stop_loss", "stop_profit"],
            default="market",
        ),
        "strategy_id": SchemaField(
            field_type="string",
            required=False,
            description="策略 ID（可选）",
        ),
    })
    
    output_schema = to_json_schema({
        "order_id": SchemaField(field_type="string", description="订单 ID"),
        "status": SchemaField(field_type="string", description="订单状态"),
        "message": SchemaField(field_type="string", description="执行消息"),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """执行下单
        
        Args:
            args: 订单参数
            context: 工具上下文
            on_progress: 进度回调
            
        Returns:
            ToolResult: 订单结果
        """
        symbol = args["symbol"]
        side = args["side"]
        quantity = args["quantity"]
        price = args.get("price")
        order_type = args.get("order_type", "market")
        strategy_id = args.get("strategy_id")
        
        self._log_audit(context, "order_start", {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "order_type": order_type,
        })
        
        try:
            # 进度更新
            self._emit_progress(ToolProgress(
                tool_use_id=context.tool_use_id or "unknown",
                data={
                    "stage": "validating",
                    "message": f"验证订单：{symbol} {side} {quantity}",
                }
            ), on_progress)
            
            # 模拟订单执行（实际应调用交易接口）
            await asyncio.sleep(0.1)  # 模拟网络延迟
            
            order_id = f"ORD_{datetime.now().strftime('%Y%m%d%H%M%S')}_{symbol}"
            
            # 进度更新
            self._emit_progress(ToolProgress(
                tool_use_id=context.tool_use_id or "unknown",
                data={
                    "stage": "executing",
                    "message": f"执行订单：{order_id}",
                }
            ), on_progress)
            
            await asyncio.sleep(0.2)  # 模拟执行
            
            result = {
                "order_id": order_id,
                "status": "submitted",
                "message": f"订单已提交：{symbol} {side} {quantity} @ {price or '市价'}",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "order_type": order_type,
                "timestamp": datetime.now().isoformat(),
            }
            
            self._log_audit(context, "order_completed", {
                "order_id": order_id,
                "status": "submitted",
            })
            
            return ToolResult(data=result)
            
        except Exception as e:
            self._log_audit(context, "order_failed", {
                "symbol": symbol,
                "error": str(e),
            })
            raise ExecutionError(f"下单失败：{str(e)}", original_error=e)
    
    async def validate_input(
        self,
        input_data: Dict[str, Any],
        context: ToolContext,
    ) -> ValidationResult:
        """验证订单输入"""
        # 基础验证
        base_result = await super().validate_input(input_data, context)
        if not base_result.result:
            return base_result
        
        # 自定义验证
        quantity = input_data.get("quantity", 0)
        if quantity > 100000:
            return ValidationResult(
                result=False,
                message="订单数量过大，请分拆订单",
                error_code=101
            )
        
        price = input_data.get("price")
        if price and price <= 0:
            return ValidationResult(
                result=False,
                message="价格必须大于 0",
                error_code=102
            )
        
        return ValidationResult(result=True)
    
    async def check_permissions(
        self,
        input_data: Dict[str, Any],
        context: ToolContext,
    ) -> PermissionResult:
        """检查交易权限"""
        quantity = input_data.get("quantity", 0)
        price = input_data.get("price", 0)
        estimated_value = quantity * (price or 10)  # 估算金额
        
        # 大额订单需要确认
        if estimated_value > 100000:
            return PermissionResult(
                behavior="ask",
                message=f"大额订单（约{estimated_value:,.0f}元），请确认是否继续",
            )
        
        return PermissionResult(
            behavior="allow",
            updated_input=input_data,
        )
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return False
    
    def is_destructive(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def get_activity_description(
        self,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        if input_data:
            return f"下单：{input_data.get('symbol')} {input_data.get('side')} {input_data.get('quantity')}股"
        return None


# ==================== 撤单工具 ====================

class CancelOrderTool(Tool):
    """撤单工具
    
    用于取消未成交的订单。
    """
    
    name = "cancel_order"
    description_text = "取消未成交的交易订单"
    search_hint = "trading, cancel, order, withdraw"
    max_result_size_chars = 5000
    aliases = ["withdraw_order"]
    
    input_schema = to_json_schema({
        "order_id": SchemaField(
            field_type="string",
            required=True,
            description="订单 ID",
        ),
        "reason": SchemaField(
            field_type="string",
            required=False,
            description="撤单原因（可选）",
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """执行撤单"""
        order_id = args["order_id"]
        reason = args.get("reason", "用户主动撤单")
        
        self._log_audit(context, "cancel_start", {
            "order_id": order_id,
            "reason": reason,
        })
        
        try:
            # 模拟撤单
            await asyncio.sleep(0.1)
            
            result = {
                "order_id": order_id,
                "status": "cancelled",
                "message": f"订单已取消：{order_id}",
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
            }
            
            self._log_audit(context, "cancel_completed", {
                "order_id": order_id,
            })
            
            return ToolResult(data=result)
            
        except Exception as e:
            self._log_audit(context, "cancel_failed", {
                "order_id": order_id,
                "error": str(e),
            })
            raise ExecutionError(f"撤单失败：{str(e)}", original_error=e)
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return False
    
    def is_destructive(self, input_data: Dict[str, Any]) -> bool:
        return True
