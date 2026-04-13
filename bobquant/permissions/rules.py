# -*- coding: utf-8 -*-
"""
规则匹配引擎
实现通配符规则匹配，支持类似 Trade(000001.*) 和 Risk(*) 的规则
"""

import re
import fnmatch
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Callable
from enum import Enum, auto

logger = logging.getLogger(__name__)


class RuleAction(Enum):
    """规则动作"""
    ALLOW = auto()     # 允许
    DENY = auto()      # 拒绝
    ASK = auto()       # 询问


class RuleType(Enum):
    """规则类型"""
    TRADE = auto()     # 交易规则
    RISK = auto()      # 风控规则
    CANCEL = auto()    # 撤单规则
    MODIFY = auto()    # 修改规则
    ANY = auto()       # 任意类型


@dataclass
class Rule:
    """
    规则定义
    
    示例:
        Rule(pattern="Trade(000001.*)", action=RuleAction.ALLOW)
        Rule(pattern="Risk(*)", action=RuleAction.ASK)
    """
    pattern: str                       # 规则模式
    action: RuleAction                 # 规则动作
    rule_type: RuleType = RuleType.ANY # 规则类型
    priority: int = 0                  # 优先级 (越高越优先)
    description: str = ""              # 规则描述
    enabled: bool = True               # 是否启用
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """解析规则模式"""
        self._parsed = self._parse_pattern(self.pattern)
    
    def _parse_pattern(self, pattern: str) -> Dict[str, Any]:
        """
        解析规则模式
        
        支持格式:
            Trade(000001.*)  -> 交易规则，匹配 000001 开头的股票
            Risk(*)          -> 风控规则，匹配所有
            Cancel(*)        -> 撤单规则，匹配所有
        """
        # 提取类型和模式
        match = re.match(r'(\w+)\((.*)\)', pattern)
        if match:
            type_str = match.group(1).upper()
            inner_pattern = match.group(2)
            
            # 映射类型
            type_mapping = {
                'TRADE': RuleType.TRADE,
                'RISK': RuleType.RISK,
                'CANCEL': RuleType.CANCEL,
                'MODIFY': RuleType.MODIFY,
                'ANY': RuleType.ANY,
            }
            
            rule_type = type_mapping.get(type_str, RuleType.ANY)
            
            return {
                'type': rule_type,
                'pattern': inner_pattern,
                'regex': self._pattern_to_regex(inner_pattern),
            }
        else:
            # 没有类型前缀，默认为 ANY
            return {
                'type': RuleType.ANY,
                'pattern': pattern,
                'regex': self._pattern_to_regex(pattern),
            }
    
    def _pattern_to_regex(self, pattern: str) -> re.Pattern:
        """
        将通配符模式转换为正则表达式
        
        支持:
            *  -> 匹配任意字符
            ?  -> 匹配单个字符
            .  -> 字面量点号
        """
        # 转义特殊字符
        regex = re.escape(pattern)
        # 替换通配符
        regex = regex.replace(r'\*', '.*')
        regex = regex.replace(r'\?', '.')
        # 添加边界 (使用 \b 或 $ 确保完整匹配)
        return re.compile(f'^{regex}$', re.IGNORECASE)
    
    def matches(self, target: str, action_type: str = "trade") -> bool:
        """
        检查是否匹配目标
        
        Args:
            target: 目标字符串 (如股票代码)
            action_type: 动作类型 (trade, risk, cancel, modify)
            
        Returns:
            bool: 是否匹配
        """
        # 检查类型是否匹配
        type_mapping = {
            'trade': RuleType.TRADE,
            'risk': RuleType.RISK,
            'cancel': RuleType.CANCEL,
            'modify': RuleType.MODIFY,
        }
        target_type = type_mapping.get(action_type.lower(), RuleType.ANY)
        
        if self._parsed['type'] != RuleType.ANY and self._parsed['type'] != target_type:
            return False
        
        # 检查模式是否匹配
        return bool(self._parsed['regex'].match(target))
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'pattern': self.pattern,
            'action': self.action.name,
            'rule_type': self.rule_type.name,
            'priority': self.priority,
            'description': self.description,
            'enabled': self.enabled,
        }


class RuleMatcher:
    """
    规则匹配器
    管理规则列表并提供匹配查询功能
    """
    
    def __init__(self):
        """初始化规则匹配器"""
        self._rules: List[Rule] = []
        self._rule_index: Dict[str, List[Rule]] = {}
        logger.info("规则匹配器初始化")
    
    def add_rule(self, rule: Rule):
        """
        添加规则
        
        Args:
            rule: 规则对象
        """
        self._rules.append(rule)
        # 按优先级排序
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"添加规则：{rule.pattern} -> {rule.action.name}")
    
    def add_rules(self, rules: List[Rule]):
        """批量添加规则"""
        for rule in rules:
            self.add_rule(rule)
    
    def remove_rule(self, pattern: str) -> bool:
        """
        移除规则
        
        Args:
            pattern: 规则模式
            
        Returns:
            bool: 是否成功移除
        """
        for i, rule in enumerate(self._rules):
            if rule.pattern == pattern:
                self._rules.pop(i)
                logger.info(f"移除规则：{pattern}")
                return True
        return False
    
    def match(self, target: str, action_type: str = "trade") -> Dict[str, Any]:
        """
        匹配规则
        
        Args:
            target: 目标字符串 (如股票代码)
            action_type: 动作类型
            
        Returns:
            dict: {'action': 'allow'/'deny'/'ask', 'rule': '匹配的规则模式'}
        """
        for rule in self._rules:
            if rule.enabled and rule.matches(target, action_type):
                action_map = {
                    RuleAction.ALLOW: 'allow',
                    RuleAction.DENY: 'deny',
                    RuleAction.ASK: 'ask',
                }
                logger.debug(f"规则匹配：{target} -> {rule.pattern} -> {rule.action.name}")
                return {
                    'action': action_map[rule.action],
                    'rule': rule.pattern,
                    'description': rule.description,
                }
        
        # 没有匹配的规则
        return {
            'action': 'ask',
            'rule': 'default',
            'description': '默认询问',
        }
    
    def match_all(self, target: str, action_type: str = "trade") -> List[Dict[str, Any]]:
        """
        获取所有匹配的规则
        
        Args:
            target: 目标字符串
            action_type: 动作类型
            
        Returns:
            list: 所有匹配的规则信息
        """
        results = []
        for rule in self._rules:
            if rule.enabled and rule.matches(target, action_type):
                results.append({
                    'pattern': rule.pattern,
                    'action': rule.action.name,
                    'priority': rule.priority,
                    'description': rule.description,
                })
        return results
    
    def get_rules(self) -> List[Rule]:
        """获取所有规则"""
        return self._rules.copy()
    
    def enable_rule(self, pattern: str) -> bool:
        """启用规则"""
        for rule in self._rules:
            if rule.pattern == pattern:
                rule.enabled = True
                return True
        return False
    
    def disable_rule(self, pattern: str) -> bool:
        """禁用规则"""
        for rule in self._rules:
            if rule.pattern == pattern:
                rule.enabled = False
                return True
        return False
    
    def clear(self):
        """清空所有规则"""
        self._rules.clear()
        logger.info("清空所有规则")


class DefaultRules:
    """
    默认规则集
    提供常用的预定义规则
    """
    
    @staticmethod
    def get_trade_rules() -> List[Rule]:
        """获取默认交易规则"""
        return [
            # 允许特定股票 (示例：平安银行)
            Rule(
                pattern="Trade(000001)",
                action=RuleAction.ALLOW,
                rule_type=RuleType.TRADE,
                priority=100,
                description="允许交易平安银行",
            ),
            # 允许所有沪深 300 成分股 (示例模式)
            Rule(
                pattern="Trade(600*)",
                action=RuleAction.ALLOW,
                rule_type=RuleType.TRADE,
                priority=90,
                description="允许交易沪市主板股票",
            ),
            Rule(
                pattern="Trade(000*)",
                action=RuleAction.ALLOW,
                rule_type=RuleType.TRADE,
                priority=90,
                description="允许交易深市主板股票",
            ),
            # 创业板需要询问
            Rule(
                pattern="Trade(300*)",
                action=RuleAction.ASK,
                rule_type=RuleType.TRADE,
                priority=80,
                description="创业板交易需要确认",
            ),
            # 科创板需要询问
            Rule(
                pattern="Trade(688*)",
                action=RuleAction.ASK,
                rule_type=RuleType.TRADE,
                priority=80,
                description="科创板交易需要确认",
            ),
        ]
    
    @staticmethod
    def get_risk_rules() -> List[Rule]:
        """获取默认风控规则"""
        return [
            # 允许所有风控检查
            Rule(
                pattern="Risk(*)",
                action=RuleAction.ALLOW,
                rule_type=RuleType.RISK,
                priority=100,
                description="允许所有风控操作",
            ),
        ]
    
    @staticmethod
    def get_default_rules() -> List[Rule]:
        """获取所有默认规则"""
        return DefaultRules.get_trade_rules() + DefaultRules.get_risk_rules()


# 便捷函数
def create_rule(pattern: str, action: str, priority: int = 0, description: str = "") -> Rule:
    """
    创建规则的便捷函数
    
    Args:
        pattern: 规则模式 (如 "Trade(000001.*)")
        action: 动作 ("allow", "deny", "ask")
        priority: 优先级
        description: 描述
        
    Returns:
        Rule: 规则对象
    """
    action_mapping = {
        'allow': RuleAction.ALLOW,
        'deny': RuleAction.DENY,
        'ask': RuleAction.ASK,
    }
    return Rule(
        pattern=pattern,
        action=action_mapping.get(action.lower(), RuleAction.ASK),
        priority=priority,
        description=description,
    )
