"""
工具注册表 - 借鉴 Claude Code Tool.ts

集中式工具注册和管理，提供：
- 工具注册
- 工具查找
- 工具过滤
- 工具池管理
"""

from typing import Any, Dict, List, Optional, Type, Callable
from dataclasses import dataclass, field
import logging
from datetime import datetime

from .base import Tool, ToolContext, ToolResult


@dataclass
class ToolRegistration:
    """工具注册信息"""
    tool_class: Type[Tool]
    name: str
    description: str
    category: str  # trading, data, risk, etc.
    enabled: bool = True
    registered_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    """工具注册表
    
    单例模式，管理所有已注册的工具。
    
    功能：
    - 注册工具
    - 查找工具（按名称、类别）
    - 过滤工具（按权限、状态）
    - 获取工具池
    """
    
    _instance: Optional["ToolRegistry"] = None
    
    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._tools: Dict[str, ToolRegistration] = {}
        self._categories: Dict[str, List[str]] = {}  # category -> tool names
        self._logger = logging.getLogger("bobquant.registry")
        self._initialized = True
    
    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """获取注册表单例"""
        return cls()
    
    def register(
        self,
        tool_class: Type[Tool],
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """注册工具
        
        Args:
            tool_class: 工具类
            category: 工具类别
            metadata: 额外元数据
            
        Raises:
            ValueError: 工具已注册
        """
        # 创建工具实例获取元数据
        tool_instance = tool_class()
        name = tool_instance.name
        
        if name in self._tools:
            self._logger.warning(f"工具 {name} 已注册，将被覆盖")
        
        registration = ToolRegistration(
            tool_class=tool_class,
            name=name,
            description=tool_instance.description_text,
            category=category,
            metadata=metadata or {},
        )
        
        self._tools[name] = registration
        
        # 添加到类别索引
        if category not in self._categories:
            self._categories[category] = []
        if name not in self._categories[category]:
            self._categories[category].append(name)
        
        # 注册别名
        aliases = getattr(tool_instance, 'aliases', [])
        if isinstance(aliases, list):
            for alias in aliases:
                if alias not in self._tools:
                    self._tools[alias] = registration
        
        self._logger.info(f"注册工具：{name} (类别：{category})")
    
    def unregister(self, name: str) -> bool:
        """注销工具
        
        Args:
            name: 工具名称
            
        Returns:
            bool: 是否成功注销
        """
        if name not in self._tools:
            return False
        
        registration = self._tools[name]
        
        # 从类别索引移除
        if registration.category in self._categories:
            if name in self._categories[registration.category]:
                self._categories[registration.category].remove(name)
        
        # 移除别名
        tool_instance = registration.tool_class()
        for alias in tool_instance.aliases:
            if alias in self._tools and self._tools[alias] == registration:
                del self._tools[alias]
        
        del self._tools[name]
        self._logger.info(f"注销工具：{name}")
        return True
    
    def get(self, name: str) -> Optional[Tool]:
        """获取工具实例
        
        Args:
            name: 工具名称
            
        Returns:
            Tool: 工具实例，未找到返回 None
        """
        if name not in self._tools:
            return None
        
        registration = self._tools[name]
        if not registration.enabled:
            return None
        
        return registration.tool_class()
    
    def get_registration(self, name: str) -> Optional[ToolRegistration]:
        """获取工具注册信息
        
        Args:
            name: 工具名称
            
        Returns:
            ToolRegistration: 注册信息
        """
        return self._tools.get(name)
    
    def list_tools(
        self,
        category: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[ToolRegistration]:
        """列出工具
        
        Args:
            category: 类别过滤
            enabled_only: 是否只返回启用的工具
            
        Returns:
            List[ToolRegistration]: 工具列表
        """
        tools = list(self._tools.values())
        
        # 去重（别名会导致重复）
        seen = set()
        unique_tools = []
        for tool in tools:
            if tool.name not in seen:
                seen.add(tool.name)
                unique_tools.append(tool)
        
        # 过滤
        if category:
            unique_tools = [t for t in unique_tools if t.category == category]
        
        if enabled_only:
            unique_tools = [t for t in unique_tools if t.enabled]
        
        return unique_tools
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        seen = set()
        names = []
        for name in self._tools:
            if name not in seen:
                seen.add(name)
                names.append(name)
        return names
    
    def get_categories(self) -> List[str]:
        """获取所有类别"""
        return list(self._categories.keys())
    
    def enable_tool(self, name: str) -> bool:
        """启用工具"""
        if name not in self._tools:
            return False
        self._tools[name].enabled = True
        self._logger.info(f"启用工具：{name}")
        return True
    
    def disable_tool(self, name: str) -> bool:
        """禁用工具"""
        if name not in self._tools:
            return False
        self._tools[name].enabled = False
        self._logger.info(f"禁用工具：{name}")
        return True
    
    def search(self, query: str) -> List[ToolRegistration]:
        """搜索工具
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[ToolRegistration]: 匹配的工具列表
        """
        query_lower = query.lower()
        results = []
        
        seen = set()
        for registration in self._tools.values():
            if registration.name in seen:
                continue
            
            # 搜索名称、描述、类别
            if (
                query_lower in registration.name.lower() or
                query_lower in registration.description.lower() or
                query_lower in registration.category.lower()
            ):
                results.append(registration)
                seen.add(registration.name)
        
        return results
    
    def filter_by_permission(
        self,
        tool_names: List[str],
        permission_context: Any,
    ) -> List[str]:
        """根据权限过滤工具
        
        Args:
            tool_names: 工具名称列表
            permission_context: 权限上下文
            
        Returns:
            List[str]: 允许使用的工具名称
        """
        allowed = []
        
        for name in tool_names:
            registration = self.get_registration(name)
            if not registration or not registration.enabled:
                continue
            
            # 检查权限规则
            if self._check_permission(registration, permission_context):
                allowed.append(name)
        
        return allowed
    
    def _check_permission(
        self,
        registration: ToolRegistration,
        permission_context: Any,
    ) -> bool:
        """检查工具权限"""
        if not permission_context:
            return True
        
        # 检查拒绝规则
        if hasattr(permission_context, "always_deny_rules"):
            for rule in permission_context.always_deny_rules.values():
                if self._match_rule(registration, rule):
                    return False
        
        # 检查允许规则
        if hasattr(permission_context, "always_allow_rules"):
            for rule in permission_context.always_allow_rules.values():
                if self._match_rule(registration, rule):
                    return True
        
        return True
    
    def _match_rule(
        self,
        registration: ToolRegistration,
        rule: Dict[str, Any],
    ) -> bool:
        """匹配规则"""
        # 简单实现：匹配名称或类别
        if "name" in rule:
            if rule["name"] == registration.name:
                return True
        if "category" in rule:
            if rule["category"] == registration.category:
                return True
        if "pattern" in rule:
            import re
            if re.match(rule["pattern"], registration.name):
                return True
        return False
    
    def get_tool_pool(
        self,
        permission_context: Optional[Any] = None,
        categories: Optional[List[str]] = None,
    ) -> List[Tool]:
        """获取工具池
        
        Args:
            permission_context: 权限上下文
            categories: 类别过滤
            
        Returns:
            List[Tool]: 工具实例列表
        """
        registrations = self.list_tools(enabled_only=True)
        
        # 类别过滤
        if categories:
            registrations = [r for r in registrations if r.category in categories]
        
        # 权限过滤
        tool_names = [r.name for r in registrations]
        if permission_context:
            tool_names = self.filter_by_permission(tool_names, permission_context)
        
        # 创建实例
        tools = []
        for name in tool_names:
            tool = self.get(name)
            if tool:
                tools.append(tool)
        
        return tools
    
    def to_dict(self) -> Dict[str, Any]:
        """导出注册表为字典"""
        return {
            "tools": {
                name: {
                    "description": reg.description,
                    "category": reg.category,
                    "enabled": reg.enabled,
                    "registered_at": reg.registered_at.isoformat(),
                    "metadata": reg.metadata,
                }
                for name, reg in self._tools.items()
                if reg.name == name  # 排除别名
            },
            "categories": self._categories,
        }


# 全局注册表实例
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """获取全局注册表"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(
    tool_class: Type[Tool],
    category: str = "general",
    metadata: Optional[Dict[str, Any]] = None,
) -> Type[Tool]:
    """装饰器：注册工具
    
    使用方式:
        @register_tool(category="trading")
        class MyTradingTool(Tool):
            ...
    """
    registry = get_registry()
    registry.register(tool_class, category, metadata)
    return tool_class
