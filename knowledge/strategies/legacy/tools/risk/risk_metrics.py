"""
风险指标工具

计算和查询各种风险指标。
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


class GetRiskMetricsTool(Tool):
    """风险指标工具
    
    计算投资组合的风险指标，包括：
    - VaR (Value at Risk)
    - Beta
    - Sharpe Ratio
    - Max Drawdown
    - Volatility
    """
    
    name = "get_risk_metrics"
    description_text = "计算风险指标（VaR、Beta、Sharpe、最大回撤等）"
    search_hint = "risk, metrics, var, beta, sharpe, volatility"
    max_result_size_chars = 20000
    aliases = ["calculate_risk", "risk_analysis"]
    
    input_schema = to_json_schema({
        "portfolio_id": SchemaField(
            field_type="string",
            required=False,
            description="投资组合 ID（可选，不填使用当前持仓）",
        ),
        "period": SchemaField(
            field_type="string",
            required=False,
            description="计算周期",
            enum=["1d", "1w", "1m", "3m", "6m", "1y"],
            default="1y",
        ),
        "confidence_level": SchemaField(
            field_type="number",
            required=False,
            description="置信水平（VaR 计算）",
            min_value=0.9,
            max_value=0.99,
            default=0.95,
        ),
        "metrics": SchemaField(
            field_type="array",
            required=False,
            description="需要计算的指标",
            default=["var", "beta", "sharpe", "max_drawdown", "volatility"],
        ),
    })
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolContext,
        on_progress: Optional[Callable[[ToolProgress], None]] = None,
    ) -> ToolResult[Dict[str, Any]]:
        """计算风险指标"""
        portfolio_id = args.get("portfolio_id")
        period = args.get("period", "1y")
        confidence = args.get("confidence_level", 0.95)
        metrics = args.get("metrics", ["var", "beta", "sharpe", "max_drawdown", "volatility"])
        
        self._log_audit(context, "risk_metrics", {
            "portfolio_id": portfolio_id,
            "period": period,
            "confidence": confidence,
        })
        
        # 进度更新
        self._emit_progress(ToolProgress(
            tool_use_id=context.tool_use_id or "unknown",
            data={
                "stage": "calculating",
                "message": f"计算风险指标 ({period})",
            }
        ), on_progress)
        
        await asyncio.sleep(0.3)
        
        # 模拟风险指标
        result = {
            "portfolio_id": portfolio_id or "current",
            "period": period,
            "confidence_level": confidence,
            "metrics": {},
            "timestamp": datetime.now().isoformat(),
        }
        
        # 计算请求的指标
        if "var" in metrics:
            result["metrics"]["var"] = {
                "var_95": -0.025,  # 95% 置信度下的日 VaR
                "var_99": -0.035,
                "cvar_95": -0.032,  # 条件 VaR
                "description": "95% 置信度下，日最大损失不超过 2.5%",
            }
        
        if "beta" in metrics:
            result["metrics"]["beta"] = {
                "beta": 1.15,
                "correlation": 0.85,
                "benchmark": "沪深 300",
                "description": "组合 Beta 为 1.15，波动略大于市场",
            }
        
        if "sharpe" in metrics:
            result["metrics"]["sharpe"] = {
                "sharpe_ratio": 1.25,
                "sortino_ratio": 1.45,
                "calmar_ratio": 1.10,
                "risk_free_rate": 0.03,
                "description": "Sharpe 比率 1.25，风险调整后收益良好",
            }
        
        if "max_drawdown" in metrics:
            result["metrics"]["max_drawdown"] = {
                "max_drawdown": -0.18,
                "max_drawdown_duration": 45,  # 天
                "current_drawdown": -0.05,
                "recovery_progress": 0.72,
                "description": "历史最大回撤 18%，当前回撤 5%",
            }
        
        if "volatility" in metrics:
            result["metrics"]["volatility"] = {
                "annual_volatility": 0.22,
                "daily_volatility": 0.014,
                "downside_volatility": 0.16,
                "description": "年化波动率 22%",
            }
        
        # 综合风险评估
        result["risk_level"] = self._calculate_risk_level(result["metrics"])
        result["recommendations"] = self._generate_recommendations(result["metrics"])
        
        return ToolResult(data=result)
    
    def _calculate_risk_level(self, metrics: Dict[str, Any]) -> str:
        """计算风险等级"""
        score = 0
        
        if "var" in metrics:
            if abs(metrics["var"]["var_95"]) > 0.03:
                score += 2
            elif abs(metrics["var"]["var_95"]) > 0.02:
                score += 1
        
        if "max_drawdown" in metrics:
            if abs(metrics["max_drawdown"]["max_drawdown"]) > 0.25:
                score += 2
            elif abs(metrics["max_drawdown"]["max_drawdown"]) > 0.15:
                score += 1
        
        if "volatility" in metrics:
            if metrics["volatility"]["annual_volatility"] > 0.30:
                score += 2
            elif metrics["volatility"]["annual_volatility"] > 0.20:
                score += 1
        
        if score >= 4:
            return "high"
        elif score >= 2:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """生成风控建议"""
        recommendations = []
        
        if "var" in metrics and abs(metrics["var"]["var_95"]) > 0.025:
            recommendations.append("考虑降低仓位以减少 VaR")
        
        if "max_drawdown" in metrics and abs(metrics["max_drawdown"]["max_drawdown"]) > 0.20:
            recommendations.append("历史回撤较大，建议设置更严格的止损")
        
        if "volatility" in metrics and metrics["volatility"]["annual_volatility"] > 0.25:
            recommendations.append("波动率较高，可考虑增加对冲")
        
        if not recommendations:
            recommendations.append("风险指标正常，维持当前策略")
        
        return recommendations
    
    def is_read_only(self, input_data: Dict[str, Any]) -> bool:
        return True
    
    def is_concurrency_safe(self, input_data: Dict[str, Any]) -> bool:
        return True
