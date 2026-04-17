"""
Schema 验证模块 - 借鉴 Zod

提供类似 Zod 的 Schema 验证功能，用于工具输入/输出验证。
"""

from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SchemaField:
    """Schema 字段定义"""
    field_type: str  # string, number, boolean, array, object
    required: bool = True
    description: str = ""
    default: Any = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum: Optional[List[Any]] = None
    items: Optional["SchemaField"] = None  # 数组项类型
    properties: Optional[Dict[str, "SchemaField"]] = None  # 对象属性


@dataclass
class SchemaValidationError:
    """Schema 验证错误"""
    field: str
    message: str
    expected: Any = None
    actual: Any = None


class SchemaValidator:
    """Schema 验证器
    
    类似 Zod 的链式验证器
    """
    
    def __init__(self, schema: Dict[str, SchemaField]):
        self.schema = schema
        self.errors: List[SchemaValidationError] = []
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """验证数据
        
        Args:
            data: 待验证的数据
            
        Returns:
            bool: 是否验证通过
        """
        self.errors = []
        
        # 检查必填字段
        for field_name, field_def in self.schema.items():
            if field_name not in data:
                if field_def.required:
                    self.errors.append(SchemaValidationError(
                        field=field_name,
                        message=f"缺少必填字段：{field_name}",
                        expected="present",
                        actual="missing"
                    ))
                continue
            
            value = data[field_name]
            self._validate_field(field_name, field_def, value)
        
        return len(self.errors) == 0
    
    def _validate_field(
        self,
        field_name: str,
        field_def: SchemaField,
        value: Any,
    ) -> None:
        """验证单个字段"""
        # 类型检查
        if not self._check_type(value, field_def.field_type):
            self.errors.append(SchemaValidationError(
                field=field_name,
                message=f"类型错误，期望 {field_def.field_type}",
                expected=field_def.field_type,
                actual=type(value).__name__
            ))
            return
        
        # 字符串验证
        if field_def.field_type == "string" and isinstance(value, str):
            if field_def.min_length and len(value) < field_def.min_length:
                self.errors.append(SchemaValidationError(
                    field=field_name,
                    message=f"字符串长度不能小于 {field_def.min_length}",
                    expected=f">= {field_def.min_length}",
                    actual=len(value)
                ))
            if field_def.max_length and len(value) > field_def.max_length:
                self.errors.append(SchemaValidationError(
                    field=field_name,
                    message=f"字符串长度不能大于 {field_def.max_length}",
                    expected=f"<= {field_def.max_length}",
                    actual=len(value)
                ))
            if field_def.pattern:
                import re
                if not re.match(field_def.pattern, value):
                    self.errors.append(SchemaValidationError(
                        field=field_name,
                        message=f"字符串不匹配模式：{field_def.pattern}",
                        expected=field_def.pattern,
                        actual=value
                    ))
        
        # 数字验证
        if field_def.field_type in ("number", "integer") and isinstance(value, (int, float)):
            if field_def.min_value is not None and value < field_def.min_value:
                self.errors.append(SchemaValidationError(
                    field=field_name,
                    message=f"值不能小于 {field_def.min_value}",
                    expected=f">= {field_def.min_value}",
                    actual=value
                ))
            if field_def.max_value is not None and value > field_def.max_value:
                self.errors.append(SchemaValidationError(
                    field=field_name,
                    message=f"值不能大于 {field_def.max_value}",
                    expected=f"<= {field_def.max_value}",
                    actual=value
                ))
        
        # 枚举验证
        if field_def.enum and value not in field_def.enum:
            self.errors.append(SchemaValidationError(
                field=field_name,
                message=f"值必须在枚举列表中",
                expected=field_def.enum,
                actual=value
            ))
        
        # 数组验证
        if field_def.field_type == "array" and isinstance(value, list):
            if field_def.items:
                for i, item in enumerate(value):
                    self._validate_field(f"{field_name}[{i}]", field_def.items, item)
        
        # 对象验证
        if field_def.field_type == "object" and isinstance(value, dict):
            if field_def.properties:
                nested_validator = SchemaValidator(field_def.properties)
                if not nested_validator.validate(value):
                    self.errors.extend(nested_validator.errors)
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查类型"""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        
        expected = type_map.get(expected_type)
        if expected is None:
            return True
        
        return isinstance(value, expected)
    
    def get_errors(self) -> List[SchemaValidationError]:
        """获取所有错误"""
        return self.errors
    
    def get_error_messages(self) -> List[str]:
        """获取错误消息列表"""
        return [f"{e.field}: {e.message}" for e in self.errors]


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """验证 Schema 的便捷函数
    
    Args:
        data: 待验证的数据
        schema: Schema 定义（简化格式）
        
    Returns:
        Dict: 验证后的数据（带默认值）
        
    Raises:
        ValueError: 验证失败
    """
    # 将简化格式转换为 SchemaField 对象
    fields = {}
    for field_name, field_def in schema.items():
        if isinstance(field_def, SchemaField):
            fields[field_name] = field_def
        elif isinstance(field_def, dict):
            fields[field_name] = SchemaField(
                field_type=field_def.get("type", "string"),
                required=field_def.get("required", True),
                description=field_def.get("description", ""),
                default=field_def.get("default"),
                min_value=field_def.get("min"),
                max_value=field_def.get("max"),
                min_length=field_def.get("min_length"),
                max_length=field_def.get("max_length"),
                pattern=field_def.get("pattern"),
                enum=field_def.get("enum"),
            )
        else:
            raise ValueError(f"Invalid schema definition for field: {field_name}")
    
    validator = SchemaValidator(fields)
    
    # 应用默认值
    validated_data = dict(data)
    for field_name, field_def in fields.items():
        if field_name not in validated_data and field_def.default is not None:
            validated_data[field_name] = field_def.default
    
    if not validator.validate(validated_data):
        error_msgs = validator.get_error_messages()
        raise ValueError(f"Schema 验证失败：{'; '.join(error_msgs)}")
    
    return validated_data


def to_json_schema(schema: Dict[str, SchemaField]) -> Dict[str, Any]:
    """将 Schema 转换为 JSON Schema 格式
    
    Args:
        schema: SchemaField 字典
        
    Returns:
        Dict: JSON Schema 格式
    """
    properties = {}
    required = []
    
    for field_name, field_def in schema.items():
        if field_def.required:
            required.append(field_name)
        
        properties[field_name] = _field_to_json_schema(field_def)
    
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _field_to_json_schema(field: SchemaField) -> Dict[str, Any]:
    """将 SchemaField 转换为 JSON Schema"""
    result: Dict[str, Any] = {"type": field.field_type}
    
    if field.description:
        result["description"] = field.description
    
    if field.enum:
        result["enum"] = field.enum
    
    if field.field_type == "string":
        if field.min_length:
            result["minLength"] = field.min_length
        if field.max_length:
            result["maxLength"] = field.max_length
        if field.pattern:
            result["pattern"] = field.pattern
    
    if field.field_type in ("number", "integer"):
        if field.min_value is not None:
            result["minimum"] = field.min_value
        if field.max_value is not None:
            result["maximum"] = field.max_value
    
    if field.field_type == "array" and field.items:
        result["items"] = _field_to_json_schema(field.items)
    
    if field.field_type == "object" and field.properties:
        result["properties"] = {
            name: _field_to_json_schema(prop)
            for name, prop in field.properties.items()
        }
    
    return result


# 便捷的 Schema 构建器
class SchemaBuilder:
    """Schema 构建器 - 类似 Zod 的链式 API"""
    
    def __init__(self):
        self.fields: Dict[str, SchemaField] = {}
        self._current_field: Optional[str] = None
    
    def string(self, name: str) -> "SchemaBuilder":
        """定义字符串字段"""
        self.fields[name] = SchemaField(field_type="string")
        self._current_field = name
        return self
    
    def number(self, name: str) -> "SchemaBuilder":
        """定义数字字段"""
        self.fields[name] = SchemaField(field_type="number")
        self._current_field = name
        return self
    
    def integer(self, name: str) -> "SchemaBuilder":
        """定义整数字段"""
        self.fields[name] = SchemaField(field_type="integer")
        self._current_field = name
        return self
    
    def boolean(self, name: str) -> "SchemaBuilder":
        """定义布尔字段"""
        self.fields[name] = SchemaField(field_type="boolean")
        self._current_field = name
        return self
    
    def array(self, name: str, items: Optional[SchemaField] = None) -> "SchemaBuilder":
        """定义数组字段"""
        self.fields[name] = SchemaField(field_type="array", items=items)
        self._current_field = name
        return self
    
    def object(self, name: str, properties: Optional[Dict[str, SchemaField]] = None) -> "SchemaBuilder":
        """定义对象字段"""
        self.fields[name] = SchemaField(field_type="object", properties=properties)
        self._current_field = name
        return self
    
    # 修饰器方法
    def required(self) -> "SchemaBuilder":
        """标记为必填"""
        if self._current_field:
            self.fields[self._current_field].required = True
        return self
    
    def optional(self) -> "SchemaBuilder":
        """标记为可选"""
        if self._current_field:
            self.fields[self._current_field].required = False
        return self
    
    def default(self, value: Any) -> "SchemaBuilder":
        """设置默认值"""
        if self._current_field:
            self.fields[self._current_field].default = value
        return self
    
    def min(self, value: Union[int, float]) -> "SchemaBuilder":
        """设置最小值"""
        if self._current_field:
            self.fields[self._current_field].min_value = value
        return self
    
    def max(self, value: Union[int, float]) -> "SchemaBuilder":
        """设置最大值"""
        if self._current_field:
            self.fields[self._current_field].max_value = value
        return self
    
    def min_length(self, length: int) -> "SchemaBuilder":
        """设置最小长度"""
        if self._current_field:
            self.fields[self._current_field].min_length = length
        return self
    
    def max_length(self, length: int) -> "SchemaBuilder":
        """设置最大长度"""
        if self._current_field:
            self.fields[self._current_field].max_length = length
        return self
    
    def pattern(self, regex: str) -> "SchemaBuilder":
        """设置正则模式"""
        if self._current_field:
            self.fields[self._current_field].pattern = regex
        return self
    
    def enum(self, values: List[Any]) -> "SchemaBuilder":
        """设置枚举值"""
        if self._current_field:
            self.fields[self._current_field].enum = values
        return self
    
    def description(self, text: str) -> "SchemaBuilder":
        """设置描述"""
        if self._current_field:
            self.fields[self._current_field].description = text
        return self
    
    def build(self) -> Dict[str, SchemaField]:
        """构建 Schema"""
        return self.fields
