"""
工具系统初始化

注册所有可用的工具到注册表。
"""

import logging
import sys
from pathlib import Path

# 支持直接运行和模块导入
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.registry import get_registry
from tools.audit import get_audit_logger

logger = logging.getLogger("bobquant.init")


def init_all_tools(audit_log_file: str = None):
    """初始化所有工具
    
    Args:
        audit_log_file: 审计日志文件路径（可选）
    """
    registry = get_registry()
    
    # 配置审计日志
    audit_logger = get_audit_logger()
    if audit_log_file:
        audit_logger.configure(log_file=audit_log_file)
        logger.info(f"审计日志配置：{audit_log_file}")
    
    # 注册交易工具
    try:
        from tools.trading import (
            PlaceOrderTool,
            CancelOrderTool,
            GetPositionTool,
            GetOrderTool,
            GetOrdersTool,
        )
        
        registry.register(PlaceOrderTool, category="trading")
        registry.register(CancelOrderTool, category="trading")
        registry.register(GetPositionTool, category="trading")
        registry.register(GetOrderTool, category="trading")
        registry.register(GetOrdersTool, category="trading")
        
        logger.info("已注册交易工具：5 个")
    except ImportError as e:
        logger.warning(f"交易工具导入失败：{e}")
    
    # 注册数据工具
    try:
        from tools.data import (
            GetMarketDataTool,
            GetRealTimeDataTool,
            GetHistoryDataTool,
            GetFinancialDataTool,
        )
        
        registry.register(GetMarketDataTool, category="data")
        registry.register(GetRealTimeDataTool, category="data")
        registry.register(GetHistoryDataTool, category="data")
        registry.register(GetFinancialDataTool, category="data")
        
        logger.info("已注册数据工具：4 个")
    except ImportError as e:
        logger.warning(f"数据工具导入失败：{e}")
    
    # 注册风控工具
    try:
        from tools.risk import (
            RiskCheckTool,
            PositionLimitTool,
            SetStopLossTool,
            GetStopLossTool,
            GetRiskMetricsTool,
        )
        
        registry.register(RiskCheckTool, category="risk")
        registry.register(PositionLimitTool, category="risk")
        registry.register(SetStopLossTool, category="risk")
        registry.register(GetStopLossTool, category="risk")
        registry.register(GetRiskMetricsTool, category="risk")
        
        logger.info("已注册风控工具：5 个")
    except ImportError as e:
        logger.warning(f"风控工具导入失败：{e}")
    
    # 输出注册表状态
    tools = registry.list_tools()
    logger.info(f"工具系统初始化完成，共注册 {len(tools)} 个工具")
    
    return registry


def get_tool_summary():
    """获取工具摘要信息"""
    registry = get_registry()
    
    summary = {
        "total": 0,
        "by_category": {},
        "tools": [],
    }
    
    for tool_reg in registry.list_tools():
        summary["total"] += 1
        
        category = tool_reg.category
        if category not in summary["by_category"]:
            summary["by_category"][category] = 0
        summary["by_category"][category] += 1
        
        summary["tools"].append({
            "name": tool_reg.name,
            "description": tool_reg.description,
            "category": category,
            "aliases": tool_reg.tool_class.aliases if hasattr(tool_reg.tool_class, 'aliases') else [],
        })
    
    return summary


def print_tool_catalog():
    """打印工具目录"""
    summary = get_tool_summary()
    
    print("\n" + "=" * 60)
    print("BobQuant 工具目录")
    print("=" * 60)
    print(f"总计：{summary['total']} 个工具\n")
    
    # 按类别分组
    by_category = {}
    for tool in summary["tools"]:
        cat = tool["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(tool)
    
    for category, tools in sorted(by_category.items()):
        print(f"\n【{category.upper()}】 - {len(tools)} 个工具")
        print("-" * 40)
        for tool in tools:
            aliases = f" (别名：{', '.join(tool['aliases'])})" if tool["aliases"] else ""
            print(f"  • {tool['name']}{aliases}")
            print(f"    {tool['description']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 初始化工具
    registry = init_all_tools()
    
    # 打印目录
    print_tool_catalog()
    
    # 导出注册表
    import json
    with open("/tmp/bobquant_tools.json", "w", encoding="utf-8") as f:
        json.dump(registry.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"\n注册表已导出到：/tmp/bobquant_tools.json")
