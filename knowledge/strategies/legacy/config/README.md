# BobQuant 配置系统 v3.0

BobQuant 配置系统升级，借鉴 Claude Code 的配置设计模式，提供强大的配置管理能力。

## 特性

### 1. Pydantic Schema 定义

使用 Pydantic v2 定义类型安全的配置 schema，支持：
- 自动类型验证
- 字段默认值
- 嵌套配置结构
- 自定义验证规则

### 2. 5 层配置继承

支持 5 层配置叠加，优先级从低到高：
1. **Global Defaults** - 全局默认配置
2. **Per-Strategy** - 策略级配置
3. **Per-Channel** - 渠道级配置
4. **Per-Account** - 账户级配置
5. **Per-Group** - 组级配置

**优先级**: Per-Group > Per-Account > Per-Channel > Per-Strategy > Global Defaults

### 3. SecretRef 支持

支持三种 Secret 引用方式：

```python
# 环境变量
SecretRef(type="env", ref="API_KEY")
# 或使用字符串格式
"${env:API_KEY}"

# 文件
SecretRef(type="file", ref="~/.bobquant/secret.txt")
# 或
"${file:~/.bobquant/secret.txt}"

# 命令
SecretRef(type="cmd", ref="vault read secret/api_key")
# 或
"${cmd:vault read secret/api_key}"
```

### 4. JSON5 支持

配置文件使用 JSON5 格式，支持：
- 注释（`//` 和 `/* */`）
- 尾随逗号
- 环境变量替换 `${VAR_NAME}`

### 5. 配置迁移系统

自动检测配置版本并迁移到最新版本：
- v2.2 → v3.0
- v2.4 → v3.0

支持迁移回滚和备份。

### 6. 配置验证

提供完整的配置验证：
- Schema 验证
- 业务规则验证
- SecretRef 可解析性验证
- 详细错误报告

## 快速开始

### 安装依赖

```bash
pip install pydantic pydantic-settings json5
```

### 加载配置

```python
from bobquant.config import ConfigLoader, ConfigValidator

# 加载配置
loader = ConfigLoader("config/settings.json5")
config = loader.load(
    strategy="bollinger_conservative",
    channel="sim_channel",
    account="account_001",
    group="group_a"
)

# 验证配置
validator = ConfigValidator(config)
if not validator.validate_all():
    print(validator.get_error_report())
    exit(1)

# 解析 SecretRef
config = config.resolve_secrets()

# 使用配置
print(f"初始资金：{config.account.initial_capital}")
print(f"最大仓位：{config.position.max_position_pct}")
```

### 配置示例

```json5
{
  // 系统配置
  "system": {
    "name": "BobQuant 模拟盘",
    "version": "3.0",
    "mode": "simulation",
    "log_level": "INFO"
  },
  
  // 账户配置
  "account": {
    "initial_capital": 1000000,
    "commission_rate": 0.0005,
    "api_key": "${env:BOBQUANT_API_KEY}"  // SecretRef
  },
  
  // 5 层配置继承
  "global_defaults": {
    "account": {
      "initial_capital": 1000000,
      "max_position_pct": 0.10
    }
  },
  
  "strategy_configs": {
    "conservative": {
      "strategy_name": "conservative",
      "position": {"max_position_pct": 0.05}
    }
  },
  
  "account_configs": {
    "account_001": {
      "account_id": "account_001",
      "account": {"initial_capital": 500000}
    }
  },
  
  // 当前激活的配置层
  "active_strategy": "conservative",
  "active_account": "account_001"
}
```

## API 参考

### ConfigLoader

```python
class ConfigLoader:
    def load(config_path, strategy, channel, account, group) -> BobQuantConfig
    def load_json5(filepath) -> Dict
    def load_with_secrets(config_path, **kwargs) -> BobQuantConfig
```

### ConfigValidator

```python
class ConfigValidator:
    def validate_schema() -> bool
    def validate_business_rules() -> bool
    def validate_secrets() -> bool
    def validate_all() -> bool
    def get_errors() -> List[ValidationError]
    def get_error_report() -> str
```

### ConfigMigrator

```python
class ConfigMigrator:
    def detect_version(config) -> str
    def needs_migration(config) -> bool
    def migrate(config, backup) -> Tuple[Dict, List[MigrationRecord]]
    def migrate_file(source_path, target_path, backup) -> Tuple[Path, List[MigrationRecord]]
    def rollback(config, to_version) -> Tuple[Dict, List[MigrationRecord]]
```

### BobQuantConfig

```python
class BobQuantConfig:
    def resolve() -> BobQuantConfig  # 解析 5 层继承
    def resolve_secrets() -> BobQuantConfig  # 解析 SecretRef
```

## 配置迁移

### 检查版本

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant/config
python3 -c "from migrations import check_config_version; print(check_config_version('settings.yaml'))"
```

### 执行迁移

```python
from migrations import migrate_config

target, records = migrate_config(
    Path("config/settings_v2.2.json5"),
    backup=True
)
```

## 测试

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant/config
python3 tests/test_config.py
```

## 文件结构

```
config/
├── __init__.py              # 模块导出
├── schema.py                # Pydantic schema 定义
├── migrations.py            # 配置迁移系统
├── config_example.json5     # 配置示例
└── tests/
    ├── __init__.py
    └── test_config.py       # 单元测试
```

## 升级指南

### 从 v2.2 升级

1. 备份原配置
2. 运行迁移脚本
3. 检查迁移后的配置
4. 更新代码使用新 API

```python
# 旧代码
from config import settings
capital = settings.initial_capital

# 新代码
from config import ConfigLoader
loader = ConfigLoader("config/settings.json5")
config = loader.load()
capital = config.account.initial_capital
```

## 最佳实践

1. **使用 SecretRef 管理敏感信息**
   - 不要在配置文件中硬编码 API 密钥
   - 使用环境变量或加密文件存储

2. **合理使用 5 层继承**
   - Global Defaults: 放全局默认值
   - Per-Strategy: 不同策略的不同参数
   - Per-Account: 不同账户的资金规模
   - Per-Group: 不同组的风控规则

3. **定期验证配置**
   - 启动时运行 `validate_all()`
   - 记录验证错误报告

4. **使用 JSON5 格式**
   - 添加注释说明配置用途
   - 使用尾随逗号方便 diff

## 故障排查

### 配置验证失败

```python
validator = ConfigValidator(config)
if not validator.validate_all():
    print(validator.get_error_report())
```

### SecretRef 解析失败

检查环境变量/文件路径/命令是否正确：

```bash
# 检查环境变量
echo $BOBQUANT_API_KEY

# 检查文件
cat ~/.bobquant/secret.txt

# 测试命令
vault read secret/api_key
```

### 迁移失败

查看迁移记录：

```python
migrator = ConfigMigrator()
config, records = migrator.migrate(config=my_config)
for record in records:
    print(f"{record.source_version} -> {record.target_version}: {'✓' if record.success else '✗'}")
```

## 版本历史

- **v3.0** (2026-04-11): 初始版本，支持 5 层继承、SecretRef、JSON5、迁移系统
- **v2.4** (2026-04-10): 激进配置版本
- **v2.2** (2026-03-27): 30 只龙头股版本

## 许可证

MIT License
