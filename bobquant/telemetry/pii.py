"""
PII Masker - 个人敏感信息脱敏模块

设计目标：
1. 保护用户隐私（账号、手机号、身份证等）
2. 保护交易敏感信息（具体金额、持仓等）
3. 可配置的脱敏规则
4. 支持部分脱敏（保留部分信息用于调试）

脱敏规则：
- 手机号：138****1234
- 身份证：110101********1234
- 银行卡：6222 **** **** 1234
- 邮箱：a***@example.com
- 账号：user***@domain

架构参考：
- GDPR 数据保护规范
- 金融行业数据脱敏标准
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Pattern, Callable, Union
from enum import Enum


class MaskingLevel(Enum):
    """脱敏级别"""
    NONE = "none"  # 不脱敏
    PARTIAL = "partial"  # 部分脱敏（保留首尾）
    FULL = "full"  # 完全脱敏
    HASH = "hash"  # 哈希处理（可关联分析）


@dataclass
class MaskingRule:
    """
    脱敏规则
    
    Attributes:
        field_name: 字段名称（支持通配符）
        field_pattern: 字段正则匹配
        value_pattern: 值正则匹配
        masking_level: 脱敏级别
        mask_char: 掩码字符
        preserve_prefix: 保留前缀长度
        preserve_suffix: 保留后缀长度
        hash_salt: 哈希盐值（用于 HASH 级别）
        enabled: 是否启用
    """
    field_name: Optional[str] = None
    field_pattern: Optional[str] = None
    value_pattern: Optional[str] = None
    masking_level: MaskingLevel = MaskingLevel.PARTIAL
    mask_char: str = "*"
    preserve_prefix: int = 3
    preserve_suffix: int = 4
    hash_salt: str = "bobquant_default_salt"
    enabled: bool = True
    
    _field_regex: Optional[Pattern] = field(default=None, repr=False)
    _value_regex: Optional[Pattern] = field(default=None, repr=False)
    
    def __post_init__(self):
        """编译正则表达式"""
        if self.field_pattern:
            self._field_regex = re.compile(self.field_pattern)
        if self.value_pattern:
            self._value_regex = re.compile(self.value_pattern)
    
    def matches_field(self, field_name: str) -> bool:
        """检查字段名是否匹配"""
        if self.field_name and self.field_name == field_name:
            return True
        if self._field_regex and self._field_regex.match(field_name):
            return True
        return False
    
    def matches_value(self, value: str) -> bool:
        """检查值是否匹配"""
        if self._value_regex:
            return bool(self._value_regex.match(value))
        return True


class PIIMasker:
    """
    PII 脱敏处理器
    
    预定义规则：
    1. 手机号脱敏
    2. 邮箱脱敏
    3. 身份证号脱敏
    4. 银行卡号脱敏
    5. 交易金额脱敏（可选）
    6. 账号脱敏
    
    使用示例：
    ```python
    masker = PIIMasker()
    
    # 脱敏单个值
    masked_phone = masker.mask_value("13812345678", "phone")
    # 输出：138****5678
    
    # 脱敏事件属性
    event = TelemetryEvent(...)
    masked_event = masker.mask_event(event)
    
    # 脱敏批量事件
    masked_events = masker.mask_batch(events)
    ```
    """
    
    def __init__(self, rules: Optional[List[MaskingRule]] = None):
        """
        初始化脱敏器
        
        Args:
            rules: 自定义脱敏规则列表
        """
        self._rules: List[MaskingRule] = []
        
        # 添加预定义规则
        self._add_default_rules()
        
        # 添加自定义规则
        if rules:
            self._rules.extend(rules)
    
    def _add_default_rules(self):
        """添加预定义脱敏规则"""
        
        # 手机号规则
        self._rules.append(MaskingRule(
            field_name="phone",
            value_pattern=r"^1[3-9]\d{9}$",
            masking_level=MaskingLevel.PARTIAL,
            preserve_prefix=3,
            preserve_suffix=4,
        ))
        
        # 手机号（字段模式匹配）
        self._rules.append(MaskingRule(
            field_pattern=r".*phone.*",
            masking_level=MaskingLevel.PARTIAL,
            preserve_prefix=3,
            preserve_suffix=4,
        ))
        
        # 邮箱规则
        self._rules.append(MaskingRule(
            field_name="email",
            masking_level=MaskingLevel.PARTIAL,
            preserve_prefix=1,
            preserve_suffix=12,  # 保留域名
        ))
        
        self._rules.append(MaskingRule(
            field_pattern=r".*email.*",
            masking_level=MaskingLevel.PARTIAL,
            preserve_prefix=1,
            preserve_suffix=12,
        ))
        
        # 银行卡号规则（必须在 id_card 之前，因为 bank_card 包含"id"）
        self._rules.append(MaskingRule(
            field_name="bank_card",
            value_pattern=r"^\d{16,19}$",
            masking_level=MaskingLevel.PARTIAL,
            preserve_prefix=4,
            preserve_suffix=4,
        ))
        
        # 银行卡/账号通用规则（在 id_card 之前）
        self._rules.append(MaskingRule(
            field_pattern=r".*(bank|card|account).*",
            masking_level=MaskingLevel.PARTIAL,
            preserve_prefix=4,
            preserve_suffix=4,
        ))
        
        # 身份证号规则
        self._rules.append(MaskingRule(
            field_name="id_card",
            value_pattern=r"^\d{17}[\dXx]$",
            masking_level=MaskingLevel.PARTIAL,
            preserve_prefix=6,
            preserve_suffix=4,
        ))
        
        # 身份证通用规则（更严格的模式，避免误匹配）
        self._rules.append(MaskingRule(
            field_pattern=r".*\b(id|identity)\b.*",
            masking_level=MaskingLevel.PARTIAL,
            preserve_prefix=6,
            preserve_suffix=4,
        ))
        
        # 交易金额（可选脱敏）
        self._rules.append(MaskingRule(
            field_pattern=r".*(amount|price|value).*",
            masking_level=MaskingLevel.NONE,  # 默认不脱敏金额
            enabled=False,  # 默认禁用
        ))
        
        # 用户 ID/账号（使用 HASH 脱敏）
        self._rules.append(MaskingRule(
            field_name="user_id",
            masking_level=MaskingLevel.HASH,
        ))
        
        self._rules.append(MaskingRule(
            field_pattern=r".*\b(username|account)\b.*",
            masking_level=MaskingLevel.HASH,
        ))
        
        # 地址信息
        self._rules.append(MaskingRule(
            field_pattern=r".*(address|location).*",
            masking_level=MaskingLevel.PARTIAL,
            preserve_prefix=2,
        ))
    
    def add_rule(self, rule: MaskingRule):
        """添加自定义规则"""
        self._rules.append(rule)
    
    def mask_value(
        self,
        value: Any,
        field_name: Optional[str] = None
    ) -> Any:
        """
        脱敏单个值
        
        匹配优先级：
        1. field_name 完全匹配（最高优先级）
        2. field_pattern 匹配
        3. value_pattern 匹配（最低优先级）
        
        Args:
            value: 要脱敏的值
            field_name: 字段名称（用于匹配规则）
            
        Returns:
            脱敏后的值
        """
        if value is None:
            return None
        
        # 非字符串不处理
        if not isinstance(value, str):
            return value
        
        field_name = field_name or ""
        
        # 第一遍：查找 field_name 完全匹配的规则
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.field_name and rule.field_name == field_name:
                return self._apply_masking(value, rule)
        
        # 第二遍：查找 field_pattern 匹配的规则
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule._field_regex and rule._field_regex.match(field_name):
                return self._apply_masking(value, rule)
        
        # 第三遍：查找 value_pattern 匹配的规则
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule._value_regex and rule._value_regex.match(value):
                return self._apply_masking(value, rule)
        
        return value
    
    def _apply_masking(self, value: str, rule: MaskingRule) -> str:
        """应用脱敏规则"""
        if rule.masking_level == MaskingLevel.NONE:
            return value
        
        elif rule.masking_level == MaskingLevel.PARTIAL:
            return self._partial_mask(value, rule)
        
        elif rule.masking_level == MaskingLevel.FULL:
            return rule.mask_char * len(value)
        
        elif rule.masking_level == MaskingLevel.HASH:
            return self._hash_value(value, rule)
        
        return value
    
    def _partial_mask(self, value: str, rule: MaskingRule) -> str:
        """部分脱敏（保留首尾）"""
        if len(value) <= rule.preserve_prefix + rule.preserve_suffix:
            # 值太短，完全脱敏
            return rule.mask_char * len(value)
        
        prefix = value[:rule.preserve_prefix]
        suffix = value[-rule.preserve_suffix:] if rule.preserve_suffix > 0 else ""
        middle_length = len(value) - len(prefix) - len(suffix)
        
        return prefix + (rule.mask_char * middle_length) + suffix
    
    def _hash_value(self, value: str, rule: MaskingRule) -> str:
        """哈希处理（保留可关联性）"""
        salted_value = f"{rule.hash_salt}{value}"
        hash_value = hashlib.sha256(salted_value.encode()).hexdigest()
        return f"hash_{hash_value[:16]}"
    
    def mask_dict(
        self,
        data: Dict[str, Any],
        recursive: bool = True
    ) -> Dict[str, Any]:
        """
        脱敏字典数据
        
        Args:
            data: 字典数据
            recursive: 是否递归处理嵌套字典
            
        Returns:
            脱敏后的字典
        """
        result = {}
        
        for key, value in data.items():
            if isinstance(value, dict) and recursive:
                result[key] = self.mask_dict(value, recursive)
            elif isinstance(value, list) and recursive:
                result[key] = self.mask_list(value)
            else:
                result[key] = self.mask_value(value, field_name=key)
        
        return result
    
    def mask_list(self, items: List[Any]) -> List[Any]:
        """脱敏列表"""
        return [
            self.mask_dict(item) if isinstance(item, dict)
            else self.mask_value(item)
            for item in items
        ]
    
    def mask_event(self, event) -> Any:
        """
        脱敏遥测事件
        
        Args:
            event: TelemetryEvent 对象
            
        Returns:
            脱敏后的事件（新对象）
        """
        # 延迟导入避免循环依赖
        from .sink import TelemetryEvent
        
        if not isinstance(event, TelemetryEvent):
            return event
        
        # 创建新事件（脱敏属性）
        masked_attributes = self.mask_dict(event.attributes)
        
        return TelemetryEvent(
            event_type=event.event_type,
            event_name=event.event_name,
            timestamp=event.timestamp,
            sequence=event.sequence,
            attributes=masked_attributes,
            event_id=event.event_id,
            session_id=event.session_id,
            correlation_id=event.correlation_id,
        )
    
    def mask_batch(self, events: List[Any]) -> List[Any]:
        """批量脱敏事件"""
        return [self.mask_event(event) for event in events]
    
    def get_masking_stats(self, data: Dict[str, Any]) -> Dict[str, int]:
        """
        统计脱敏情况
        
        Args:
            data: 原始字典数据
            
        Returns:
            脱敏统计信息
        """
        stats = {
            "total_fields": 0,
            "masked_fields": 0,
            "by_rule": {},
        }
        
        def count_fields(d: Dict, prefix: str = ""):
            for key, value in d.items():
                stats["total_fields"] += 1
                
                if isinstance(value, dict):
                    count_fields(value, f"{prefix}{key}.")
                else:
                    masked_value = self.mask_value(value, field_name=key)
                    if masked_value != value:
                        stats["masked_fields"] += 1
                        
                        # 统计匹配的规则
                        for i, rule in enumerate(self._rules):
                            if rule.enabled and (
                                rule.matches_field(key) or
                                (isinstance(value, str) and rule.matches_value(value))
                            ):
                                rule_name = rule.field_name or rule.field_pattern or f"rule_{i}"
                                stats["by_rule"][rule_name] = stats["by_rule"].get(rule_name, 0) + 1
                                break
        
        count_fields(data)
        return stats


# 预配置的脱敏器实例
DEFAULT_MASKER = PIIMasker()

# 严格模式（更多字段脱敏）
STRICT_MASKER = PIIMasker(rules=[
    MaskingRule(
        field_pattern=r".*(amount|price|value|profit|loss).*",
        masking_level=MaskingLevel.PARTIAL,
        preserve_prefix=1,
        enabled=True,
    ),
])
