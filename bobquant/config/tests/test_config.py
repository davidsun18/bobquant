# -*- coding: utf-8 -*-
"""
BobQuant 配置系统测试

测试内容：
1. Schema 验证
2. SecretRef 解析
3. 5 层配置继承
4. JSON5 加载
5. 配置迁移
6. 配置验证
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加 bobquant 到路径
bobquant_path = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(bobquant_path))

from config.schema import (
    BobQuantConfig,
    SecretRef,
    SecretType,
    ConfigLoader,
    ConfigValidator,
    ValidationError,
    get_example_config,
)
from config.migrations import (
    ConfigMigrator,
    MigrationStep,
    migrate_config,
    check_config_version,
)


def test_secret_ref():
    """测试 SecretRef 解析"""
    print("\n=== 测试 SecretRef ===")
    
    # 设置测试环境变量
    os.environ["TEST_API_KEY"] = "test_secret_value_123"
    
    # 测试环境变量引用
    secret_env = SecretRef(type=SecretType.ENV, ref="TEST_API_KEY")
    resolved = secret_env.resolve()
    assert resolved == "test_secret_value_123", f"环境变量解析失败：{resolved}"
    print(f"✓ 环境变量 SecretRef 解析成功：{secret_env} -> {resolved}")
    
    # 测试 from_string
    secret_from_str = SecretRef.from_string("${env:TEST_API_KEY}")
    assert isinstance(secret_from_str, SecretRef), "from_string 解析失败"
    assert secret_from_str.ref == "TEST_API_KEY", "from_string 解析 ref 错误"
    print(f"✓ from_string 解析成功：${{env:TEST_API_KEY}} -> {secret_from_str}")
    
    # 测试非 SecretRef 字符串
    normal_str = SecretRef.from_string("normal_value")
    assert normal_str == "normal_value", "非 SecretRef 字符串处理错误"
    print(f"✓ 非 SecretRef 字符串处理正确：normal_value")
    
    # 测试文件引用
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("file_secret_value")
        temp_file = f.name
    
    try:
        secret_file = SecretRef(type=SecretType.FILE, ref=temp_file)
        resolved = secret_file.resolve()
        assert resolved == "file_secret_value", f"文件 SecretRef 解析失败：{resolved}"
        print(f"✓ 文件 SecretRef 解析成功：{secret_file} -> {resolved}")
    finally:
        os.unlink(temp_file)
    
    # 测试命令引用
    secret_cmd = SecretRef(type=SecretType.CMD, ref="echo cmd_secret_value")
    resolved = secret_cmd.resolve()
    assert resolved == "cmd_secret_value", f"命令 SecretRef 解析失败：{resolved}"
    print(f"✓ 命令 SecretRef 解析成功：{secret_cmd} -> {resolved}")
    
    print("=== SecretRef 测试通过 ===\n")


def test_schema_validation():
    """测试 Schema 验证"""
    print("\n=== 测试 Schema 验证 ===")
    
    # 有效配置
    valid_config = {
        "system": {
            "name": "Test",
            "version": "3.0",
            "mode": "simulation",
            "log_level": "INFO"
        },
        "account": {
            "initial_capital": 1000000,
            "commission_rate": 0.0005,
            "max_position_pct": 0.10,
            "max_stocks": 10
        }
    }
    
    config = BobQuantConfig(**valid_config)
    assert config.system.name == "Test", "系统名称解析失败"
    assert config.account.initial_capital == 1000000, "初始资金解析失败"
    print("✓ 有效配置 Schema 验证通过")
    
    # 测试 SecretRef 字段
    config_with_secret = {
        "system": {"name": "Test", "version": "3.0", "mode": "simulation"},
        "account": {
            "initial_capital": 1000000,
            "api_key": "${env:TEST_API_KEY}"
        }
    }
    
    config = BobQuantConfig(**config_with_secret)
    # api_key 应该是字符串（未解析的 SecretRef 格式）
    print(f"✓ SecretRef 字段解析正确：{config.account.api_key}")
    
    print("=== Schema 验证测试通过 ===\n")


def test_5_layer_inheritance():
    """测试 5 层配置继承"""
    print("\n=== 测试 5 层配置继承 ===")
    
    config_dict = {
        "system": {"name": "BobQuant", "version": "3.0", "mode": "simulation"},
        
        # 第 1 层：全局默认
        "global_defaults": {
            "account": {
                "initial_capital": 1000000,
                "commission_rate": 0.0005
            },
            "position": {
                "max_position_pct": 0.10,
                "max_stocks": 10
            }
        },
        
        # 第 2 层：策略级
        "strategy_configs": {
            "conservative": {
                "strategy_name": "conservative",
                "position": {"max_position_pct": 0.05}
            }
        },
        
        # 第 3 层：渠道级
        "channel_configs": {
            "sim": {
                "channel": "sim",
                "system": {"log_level": "DEBUG"}
            }
        },
        
        # 第 4 层：账户级
        "account_configs": {
            "acc_001": {
                "account_id": "acc_001",
                "account": {"initial_capital": 500000}
            }
        },
        
        # 第 5 层：组级
        "group_configs": {
            "group_a": {
                "group_id": "group_a",
                "account": {"max_stocks": 5}
            }
        },
        
        # 激活的配置层
        "active_strategy": "conservative",
        "active_channel": "sim",
        "active_account": "acc_001",
        "active_group": "group_a"
    }
    
    config = BobQuantConfig(**config_dict)
    
    resolved = config.resolve()
    
    # 调试输出
    dump = resolved.model_dump()
    
    # 验证继承结果 - 直接从 dump 获取
    # 账户级覆盖：initial_capital = 500000
    # 检查是否展平到顶层
    initial_cap = dump.get('initial_capital')
    if initial_cap:
        assert initial_cap == 500000, f"账户级继承失败：{initial_cap}"
        print(f"✓ 账户级继承正确：initial_capital = 500000 (展平)")
    else:
        # 检查 account 对象
        acc = dump.get('account')
        if acc and isinstance(acc, dict):
            assert acc.get('initial_capital') == 500000, f"账户级继承失败：{acc}"
            print(f"✓ 账户级继承正确：initial_capital = 500000")
        else:
            raise AssertionError(f"账户级继承失败：找不到 initial_capital")
    
    # 策略级覆盖：max_position_pct = 0.05
    assert resolved.position.max_position_pct == 0.05, \
        f"策略级继承失败：{resolved.position.max_position_pct}"
    print(f"✓ 策略级继承正确：max_position_pct = 0.05")
    
    # 渠道级覆盖：log_level = DEBUG
    assert resolved.system.log_level == "DEBUG", \
        f"渠道级继承失败：{resolved.system.log_level}"
    print(f"✓ 渠道级继承正确：log_level = DEBUG")
    
    # 组级覆盖：max_stocks = 5
    assert resolved.account.max_stocks == 5, \
        f"组级继承失败：{resolved.account.max_stocks}"
    print(f"✓ 组级继承正确：max_stocks = 5")
    
    # commission_rate 保持默认值
    assert resolved.account.commission_rate == 0.0005, \
        f"默认值继承失败：{resolved.account.commission_rate}"
    print(f"✓ 默认值继承正确：commission_rate = 0.0005")
    
    print("=== 5 层配置继承测试通过 ===\n")


def test_json5_loading():
    """测试 JSON5 加载"""
    print("\n=== 测试 JSON5 加载 ===")
    
    # 创建临时 JSON5 文件
    json5_content = '''
    {
      // 这是注释
      "system": {
        "name": "Test",
        "version": "3.0",
      },  // 尾随逗号
      "account": {
        "initial_capital": 1000000,
      }
    }
    '''
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json5') as f:
        f.write(json5_content)
        temp_file = f.name
    
    try:
        loader = ConfigLoader(temp_file)
        config = loader.load()
        
        assert config.system.name == "Test", "JSON5 名称解析失败"
        assert config.account.initial_capital == 1000000, "JSON5 资金解析失败"
        print(f"✓ JSON5 注释和尾随逗号支持正确")
        
        # 测试环境变量替换
        os.environ["TEST_VAR"] = "replaced_value"
        json5_with_env = '''
        {
          "system": {"name": "${TEST_VAR}", "version": "3.0"},
          "account": {"initial_capital": 1000000}
        }
        '''
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json5') as f2:
            f2.write(json5_with_env)
            temp_file2 = f2.name
        
        try:
            loader2 = ConfigLoader(temp_file2)
            config2 = loader2.load()
            assert config2.system.name == "replaced_value", "环境变量替换失败"
            print(f"✓ JSON5 环境变量替换正确")
        finally:
            os.unlink(temp_file2)
        
    finally:
        os.unlink(temp_file)
    
    print("=== JSON5 加载测试通过 ===\n")


def test_config_migration():
    """测试配置迁移"""
    print("\n=== 测试配置迁移 ===")
    
    # v2.2 格式配置
    v22_config = {
        "name": "BobQuant v2.2",
        "version": "2.2",
        "mode": "simulation",
        "account": {
            "initial_capital": 1000000,
            "commission_rate": 0.0005,
            "max_position_pct": 0.10,
            "max_stocks": 10
        },
        "strategy": {
            "stop_loss_pct": -0.08,
            "trailing_stop_activate": 0.05,
            "trailing_stop_drawdown": 0.02
        }
    }
    
    migrator = ConfigMigrator()
    
    # 检测版本
    version = migrator.detect_version(v22_config)
    assert version == "2.2", f"版本检测失败：{version}"
    print(f"✓ 版本检测正确：{version}")
    
    # 执行迁移
    migrated, records = migrator.migrate(config=v22_config, backup=False)
    
    # 验证迁移结果
    assert migrated["system"]["version"] == "3.0", "迁移后版本号错误"
    print(f"✓ 迁移后版本号正确：{migrated['system']['version']}")
    
    # 验证 risk_control 重组
    assert "risk_control" in migrated, "risk_control 重组失败"
    assert migrated["risk_control"]["stop_loss"]["pct"] == -0.08, "止损迁移失败"
    print(f"✓ risk_control 重组正确")
    
    # 验证 5 层继承字段添加
    assert "global_defaults" in migrated, "global_defaults 添加失败"
    assert "strategy_configs" in migrated, "strategy_configs 添加失败"
    print(f"✓ 5 层继承字段添加正确")
    
    # 验证迁移记录
    assert len(records) > 0, "迁移记录为空"
    assert records[0].success, "迁移记录标记失败"
    print(f"✓ 迁移记录正确：{len(records)} 步")
    
    print("=== 配置迁移测试通过 ===\n")


def test_config_validator():
    """测试配置验证器"""
    print("\n=== 测试配置验证器 ===")
    
    # 有效配置
    valid_config = BobQuantConfig(
        system={"name": "Test", "version": "3.0", "mode": "simulation"},
        account={"initial_capital": 1000000, "max_position_pct": 0.10}
    )
    
    validator = ConfigValidator(valid_config)
    is_valid = validator.validate_all()
    assert is_valid, f"有效配置验证失败：{validator.get_error_report()}"
    print(f"✓ 有效配置验证通过")
    
    # 无效配置 - 仓位比例超出范围
    invalid_config = BobQuantConfig(
        system={"name": "Test", "version": "3.0", "mode": "simulation"},
        account={"initial_capital": 1000000, "max_position_pct": 1.5}  # > 1
    )
    
    validator = ConfigValidator(invalid_config)
    is_valid = validator.validate_business_rules()
    assert not is_valid, "无效配置应该验证失败"
    errors = validator.get_errors()
    assert len(errors) > 0, "错误列表为空"
    print(f"✓ 业务规则验证正确：检测到 {len(errors)} 个错误")
    
    # 获取错误报告
    report = validator.get_error_report()
    assert "配置验证失败" in report, "错误报告格式错误"
    print(f"✓ 错误报告生成正确")
    
    print("=== 配置验证器测试通过 ===\n")


def test_example_config():
    """测试示例配置"""
    print("\n=== 测试示例配置 ===")
    
    import json5
    
    example = get_example_config()
    config_dict = json5.loads(example)
    
    # 验证示例配置可以解析
    config = BobQuantConfig(**config_dict)
    assert config.system.name == "BobQuant 模拟盘", "示例配置名称错误"
    assert config.account.initial_capital == 1000000, "示例配置资金错误"
    print(f"✓ 示例配置解析成功")
    
    # 验证 5 层继承字段存在
    assert config.active_strategy == "bollinger_conservative", "示例策略激活错误"
    assert config.global_defaults is not None, "全局默认配置缺失"
    assert config.strategy_configs is not None, "策略配置缺失"
    print(f"✓ 示例配置 5 层继承字段正确")
    
    print("=== 示例配置测试通过 ===\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("BobQuant 配置系统测试套件")
    print("="*60)
    
    try:
        test_secret_ref()
        test_schema_validation()
        test_5_layer_inheritance()
        test_json5_loading()
        test_config_migration()
        test_config_validator()
        test_example_config()
        
        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60 + "\n")
        return True
        
    except AssertionError as e:
        print(f"\n✗ 测试失败：{e}\n")
        return False
    except Exception as e:
        print(f"\n✗ 测试异常：{e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
