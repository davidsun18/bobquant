"""
工具系统使用示例

演示如何使用新的 BobQuant 工具系统。
"""

import asyncio
from datetime import datetime
from bobquant.tools import (
    Tool,
    ToolContext,
    ToolResult,
    ToolProgress,
    get_registry,
    get_audit_logger,
    to_json_schema,
    SchemaField,
    PermissionResult,
)


# ==================== 示例 1: 创建自定义工具 ====================

class SimpleQueryTool(Tool):
    """简单查询工具示例"""
    
    name = "simple_query"
    description_text = "简单查询工具示例"
    search_hint = "example, query, demo"
    
    input_schema = to_json_schema({
        "query": SchemaField(
            field_type="string",
            required=True,
            description="查询内容",
            min_length=1,
        ),
        "limit": SchemaField(
            field_type="integer",
            required=False,
            description="返回数量限制",
            default=10,
            min_value=1,
            max_value=100,
        ),
    })
    
    async def call(
        self,
        args: dict,
        context: ToolContext,
        on_progress=None,
    ) -> ToolResult:
        """执行查询"""
        query = args["query"]
        limit = args.get("limit", 10)
        
        # 记录审计
        self._log_audit(context, "query_start", {
            "query": query,
            "limit": limit,
        })
        
        # 进度更新
        self._emit_progress(ToolProgress(
            tool_use_id=context.tool_use_id or "unknown",
            data={"stage": "searching", "message": f"查询：{query}"}
        ), on_progress)
        
        # 模拟查询
        await asyncio.sleep(0.1)
        
        results = [
            {"id": i, "content": f"结果 {i} for {query}"}
            for i in range(1, limit + 1)
        ]
        
        return ToolResult(data={
            "query": query,
            "results": results,
            "count": len(results),
            "timestamp": datetime.now().isoformat(),
        })


# ==================== 示例 2: 带权限检查的工具 ====================

class ProtectedActionTool(Tool):
    """带权限检查的工具示例"""
    
    name = "protected_action"
    description_text = "需要权限检查的操作"
    
    input_schema = to_json_schema({
        "action": SchemaField(
            field_type="string",
            required=True,
            enum=["read", "write", "delete"],
        ),
        "resource": SchemaField(
            field_type="string",
            required=True,
        ),
    })
    
    async def call(self, args, context, on_progress=None) -> ToolResult:
        action = args["action"]
        resource = args["resource"]
        
        self._log_audit(context, "protected_action", {
            "action": action,
            "resource": resource,
        })
        
        # 模拟执行
        return ToolResult(data={
            "action": action,
            "resource": resource,
            "status": "completed",
        })
    
    async def check_permissions(self, input_data, context) -> PermissionResult:
        """权限检查"""
        action = input_data.get("action")
        
        # 删除操作需要确认
        if action == "delete":
            return PermissionResult(
                behavior="ask",
                message="删除操作不可逆，请确认是否继续",
            )
        
        return PermissionResult(behavior="allow")


# ==================== 示例 3: 使用工具注册表 ====================

async def example_registry_usage():
    """演示工具注册表的使用"""
    print("=" * 50)
    print("示例 3: 工具注册表使用")
    print("=" * 50)
    
    # 获取注册表
    registry = get_registry()
    
    # 注册工具
    registry.register(SimpleQueryTool, category="example")
    registry.register(ProtectedActionTool, category="example")
    
    # 列出所有工具
    print("\n已注册的工具:")
    for tool_reg in registry.list_tools(category="example"):
        print(f"  - {tool_reg.name}: {tool_reg.description}")
    
    # 获取工具
    tool = registry.get("simple_query")
    if tool:
        print(f"\n获取工具：{tool.name}")
    
    # 搜索工具
    print("\n搜索 'query':")
    results = registry.search("query")
    for r in results:
        print(f"  - {r.name}")
    
    # 导出注册表
    print("\n注册表导出:")
    print(registry.to_dict())


# ==================== 示例 4: 调用工具 ====================

async def example_tool_call():
    """演示工具调用"""
    print("\n" + "=" * 50)
    print("示例 4: 工具调用")
    print("=" * 50)
    
    registry = get_registry()
    tool = registry.get("simple_query")
    
    if not tool:
        print("工具未找到")
        return
    
    # 创建上下文
    context = ToolContext(
        options={"mode": "test"},
        tool_use_id="example_001",
    )
    
    # 准备参数
    args = {
        "query": "测试查询",
        "limit": 5,
    }
    
    # 进度回调
    def on_progress(progress: ToolProgress):
        print(f"  进度：{progress.data['stage']} - {progress.data['message']}")
    
    # 调用工具
    print(f"\n调用工具：{tool.name}")
    result = await tool.call(args, context, on_progress)
    
    print(f"\n结果:")
    print(f"  查询：{result.data['query']}")
    print(f"  数量：{result.data['count']}")
    for item in result.data["results"]:
        print(f"    - {item['content']}")


# ==================== 示例 5: 审计日志 ====================

async def example_audit_log():
    """演示审计日志"""
    print("\n" + "=" * 50)
    print("示例 5: 审计日志")
    print("=" * 50)
    
    # 配置审计日志
    logger = get_audit_logger()
    logger.configure(log_file="/tmp/bobquant_audit.log")
    
    # 记录日志
    logger.log(
        action="example_action",
        tool_name="example_tool",
        tool_use_id="audit_001",
        input_data={"test": "data"},
        output_data={"result": "success"},
        status="success",
        duration_ms=50.5,
    )
    
    # 查询日志
    print("\n查询最近的日志:")
    logs = logger.query(limit=5)
    for log in logs:
        print(f"  [{log.timestamp}] {log.action} - {log.status}")
    
    # 获取统计
    print("\n统计信息:")
    stats = logger.get_stats()
    print(f"  总数：{stats['total']}")
    print(f"  成功率：{stats['success_rate']:.2%}")
    print(f"  平均耗时：{stats['avg_duration_ms']:.2f}ms")
    
    # 导出日志
    print("\n导出日志:")
    json_output = logger.export(format="json", limit=10)
    print(f"  JSON 长度：{len(json_output)} 字符")


# ==================== 示例 6: Schema 验证 ====================

async def example_schema_validation():
    """演示 Schema 验证"""
    print("\n" + "=" * 50)
    print("示例 6: Schema 验证")
    print("=" * 50)
    
    from bobquant.tools import validate_schema, SchemaBuilder
    
    # 方式 1: 声明式
    schema1 = to_json_schema({
        "name": SchemaField(field_type="string", required=True),
        "age": SchemaField(field_type="integer", min_value=0, max_value=150),
    })
    
    # 方式 2: 链式
    schema2 = (SchemaBuilder()
        .string("username").required().min_length(3).max_length(20)
        .email("email").required()
        .number("score").min(0).max(100).default(0)
        .build())
    
    # 验证有效数据
    print("\n验证有效数据:")
    try:
        data = {"name": "张三", "age": 25}
        validated = validate_schema(data, schema1)
        print(f"  通过：{validated}")
    except ValueError as e:
        print(f"  失败：{e}")
    
    # 验证无效数据
    print("\n验证无效数据:")
    try:
        data = {"name": "", "age": -1}
        validated = validate_schema(data, schema1)
        print(f"  通过：{validated}")
    except ValueError as e:
        print(f"  失败：{e}")


# ==================== 主函数 ====================

async def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("BobQuant 工具系统使用示例")
    print("=" * 60)
    
    await example_registry_usage()
    await example_tool_call()
    await example_audit_log()
    await example_schema_validation()
    
    print("\n" + "=" * 60)
    print("示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
