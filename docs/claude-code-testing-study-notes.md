# Claude Code 测试与最佳实践 - 详细学习笔记

> 📚 学习时间：2026-04-11  
> 📝 整理人：Bob  
> 🎯 目标：建立 BobQuant 测试体系

---

## 一、测试金字塔架构 (Test Pyramid)

### 1.1 什么是测试金字塔

测试金字塔是由 Mike Cohn 在《Succeeding with Agile》中提出的概念，是一个视觉化的测试分层模型，告诉我们：

- **应该有哪些类型的测试**
- **每种测试应该写多少**

```
           ┌─────────────┐
           │   E2E 测试   │  ← 最少 (10-20%)
           │  (UI 测试)   │
          ─┴─────────────┴─
         ┌─────────────────┐
         │   集成测试      │  ← 中等 (30-40%)
         │  (Service 测试) │
        ─┴─────────────────┴─
       ┌─────────────────────┐
       │     单元测试        │  ← 最多 (50-70%)
       │   (Unit Tests)      │
      ─┴─────────────────────┴─
```

### 1.2 三层测试详解

#### 🔹 底层：单元测试 (Unit Tests)

**定义**：测试最小的代码单元（函数、方法、类）

**特点**：
- ✅ 运行速度快（毫秒级）
- ✅ 易于编写和维护
- ✅ 定位问题精确
- ✅ 不依赖外部系统
- ❌ 覆盖范围有限

**适合测试**：
- 纯函数逻辑
- 算法实现
- 数据处理函数
- 工具类方法

**示例（Python）**：
```python
# test_calculator.py
def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_divide_by_zero():
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)
```

#### 🔹 中层：集成测试 (Integration Tests)

**定义**：测试多个模块/组件之间的交互

**特点**：
- ✅ 验证组件间协作
- ✅ 发现接口问题
- ⚠️ 运行速度中等
- ⚠️ 需要部分外部依赖

**适合测试**：
- API 接口调用
- 数据库交互
- 服务间通信
- 模块集成

**示例（Python）**：
```python
# test_api_integration.py
def test_user_api_integration():
    # 测试数据库 + API 层的集成
    user = create_user_in_db("test@example.com")
    response = api_client.get_user(user.id)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
```

#### 🔹 顶层：E2E 测试 (End-to-End Tests)

**定义**：从用户角度测试完整流程

**特点**：
- ✅ 最接近真实用户场景
- ✅ 验证完整业务流程
- ❌ 运行速度慢（秒级甚至分钟级）
- ❌ 难以调试和维护
- ❌ 容易脆弱（flaky）

**适合测试**：
- 关键用户流程
- 核心业务场景
- 发布前验收测试

**示例（Python + Selenium/Playwright）**：
```python
# test_e2e_login.py
def test_user_login_flow():
    browser.goto("https://app.example.com/login")
    browser.fill("email", "user@example.com")
    browser.fill("password", "secret123")
    browser.click("Submit")
    assert browser.has_text("Welcome back!")
```

### 1.3 为什么需要金字塔结构

| 测试类型 | 数量比例 | 运行速度 | 维护成本 | 可信度 |
|---------|---------|---------|---------|--------|
| 单元测试 | 70% | ⚡ 极快 | 💚 低 | 中 |
| 集成测试 | 20% | 🚀 快 | 💛 中 | 高 |
| E2E 测试 | 10% | 🐌 慢 | ❤️ 高 | 极高 |

**核心原则**：
> "金字塔告诉我们要有大量的小型单元测试，而不是依赖少量的端到端测试"

**反模式：冰淇淋筒架构** 🍦
```
       ┌─────────────┐
       │   E2E 测试   │  ← 太多！
      ─┴─────────────┴─
     ┌─────────────────┐
     │   集成测试      │  ← 太少
    ─┴─────────────────┴─
   ┌─────────────────────┐
   │     单元测试        │  ← 太少！
  ─┴─────────────────────┴─
```

问题：
- 测试运行极慢
- 问题难以定位
- 维护成本极高
- 反馈周期长

---

## 二、测试框架与架构

### 2.1 Python 测试生态系统

#### 主流测试框架

| 框架 | 特点 | 适用场景 |
|-----|------|---------|
| **pytest** | 简洁、强大、插件丰富 | 首选推荐 ⭐ |
| **unittest** | 标准库、xUnit 风格 | 遗留项目 |
| **nose2** | unittest 扩展 | 较少使用 |

#### pytest 核心特性

```python
# 1. 简单的测试函数
def test_something():
    assert 1 + 1 == 2

# 2. 参数化测试
@pytest.mark.parametrize("input,expected", [
    (2, 4),
    (3, 9),
    (4, 16),
])
def test_square(input, expected):
    assert square(input) == expected

# 3. Fixtures - 测试依赖注入
@pytest.fixture
def database():
    db = create_test_database()
    yield db
    cleanup_database(db)

def test_with_db(database):
    database.insert("test")
    assert database.count() == 1

# 4. Mocking
def test_with_mock(mocker):
    mock_api = mocker.patch("module.api_call")
    mock_api.return_value = {"status": "ok"}
    result = process_data()
    assert result == "success"
```

### 2.2 测试目录结构

推荐的 BobQuant 项目结构：

```
bobquant/
├── src/
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── strategy.py
│   │   ├── executor.py
│   │   └── risk_manager.py
│   ├── data/
│   │   ├── __init__.py
│   │   ├── fetcher.py
│   │   └── processor.py
│   └── utils/
│       └── helpers.py
│
├── tests/
│   ├── __init__.py
│   ├── unit/              # 单元测试
│   │   ├── test_strategy.py
│   │   ├── test_executor.py
│   │   ├── test_fetcher.py
│   │   └── test_helpers.py
│   ├── integration/       # 集成测试
│   │   ├── test_data_pipeline.py
│   │   ├── test_trading_flow.py
│   │   └── test_api_integration.py
│   └── e2e/              # E2E 测试
│       ├── test_full_trading_day.py
│       └── test_strategy_lifecycle.py
│
├── conftest.py           # pytest 配置和共享 fixtures
├── pytest.ini            # pytest 配置
└── requirements-dev.txt  # 开发依赖
```

### 2.3 测试配置文件

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --cov=src
    --cov-report=html
    --cov-report=term-missing
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
    data_source: 数据源相关测试
```

---

## 三、Mock 和 Stub 模式详解

### 3.1 核心概念对比

| 概念 | 定义 | 用途 | 验证重点 |
|-----|------|------|---------|
| **Mock** | 模拟对象，记录调用行为 | 验证"如何被调用" | 调用次数、参数、顺序 |
| **Stub** | 提供预定义响应的桩 | 提供测试数据 | 返回结果 |
| **Fake** | 真实实现的简化版 | 替代重型依赖 | 功能正确性 |
| **Spy** | 包装真实对象的间谍 | 部分模拟 + 部分真实 | 调用验证 + 真实行为 |

### 3.2 Mock 模式详解

#### 什么时候用 Mock

- 验证函数被正确调用
- 验证调用参数
- 验证调用顺序
- 隔离外部依赖（API、数据库）

#### pytest-mock 示例

```python
# test_trading_mock.py

def test_strategy_calls_api(mocker):
    # 创建 mock 对象
    mock_api = mocker.patch("trading.strategy.price_api")
    mock_api.get_price.return_value = 100.50
    
    # 执行测试
    strategy = TradingStrategy()
    price = strategy.get_current_price("AAPL")
    
    # 验证返回值
    assert price == 100.50
    
    # 验证调用行为
    mock_api.get_price.assert_called_once_with("AAPL")
    mock_api.get_price.assert_called_with("AAPL")

def test_multiple_calls(mocker):
    mock_logger = mocker.patch("trading.executor.logger")
    
    executor = TradingExecutor()
    executor.execute("BUY", "AAPL", 100)
    executor.execute("SELL", "GOOGL", 50)
    
    # 验证调用次数
    assert mock_logger.info.call_count == 2
    
    # 验证具体调用
    mock_logger.info.assert_any_call("Executing BUY for AAPL")
    mock_logger.info.assert_any_call("Executing SELL for GOOGL")

def test_mock_return_value_sequence(mocker):
    mock_db = mocker.patch("trading.data.database")
    
    # 设置多次调用的不同返回值
    mock_db.query.side_effect = [
        {"price": 100},
        {"price": 105},
        {"price": 102},
    ]
    
    assert get_price() == 100
    assert get_price() == 105
    assert get_price() == 102
```

### 3.3 Stub 模式详解

#### 什么时候用 Stub

- 需要固定返回值
- 模拟各种场景（成功、失败、异常）
- 提供测试数据

```python
# test_with_stubs.py

# Stub: 简单的数据提供者
class PriceDataStub:
    def get_price(self, symbol):
        return {"AAPL": 150, "GOOGL": 2800}[symbol]
    
    def get_history(self, symbol, days):
        return [150, 152, 148, 155][:days]

def test_strategy_with_stub():
    stub = PriceDataStub()
    strategy = TradingStrategy(data_source=stub)
    
    assert strategy.calculate_signal("AAPL") == "BUY"

# 使用 pytest fixture 创建 stub
@pytest.fixture
def successful_api_stub():
    class APIStub:
        def fetch(self, url):
            return {"status": "success", "data": []}
        def is_available(self):
            return True
    return APIStub()

@pytest.fixture
def failed_api_stub():
    class APIStub:
        def fetch(self, url):
            raise ConnectionError("Network error")
        def is_available(self):
            return False
    return APIStub()

def test_error_handling(failed_api_stub):
    processor = DataProcessor(api=failed_api_stub)
    with pytest.raises(DataFetchError):
        processor.fetch_data()
```

### 3.4 Fake 模式详解

#### 什么时候用 Fake

- 真实实现太重（数据库、文件系统）
- 需要接近真实的行为
- 单元测试需要快速执行

```python
# Fakes - 轻量级真实实现

class InMemoryDatabase:
    """Fake database for testing"""
    def __init__(self):
        self._data = {}
    
    def insert(self, table, record):
        if table not in self._data:
            self._data[table] = []
        self._data[table].append(record)
    
    def query(self, table, condition=None):
        records = self._data.get(table, [])
        if condition:
            return [r for r in records if condition(r)]
        return records
    
    def clear(self):
        self._data = {}

def test_with_fake_db():
    db = InMemoryDatabase()
    service = UserService(db)
    
    service.create_user("test@example.com")
    users = db.query("users")
    
    assert len(users) == 1
    assert users[0]["email"] == "test@example.com"
```

### 3.5 Mock 最佳实践

```python
# ✅ 好的 Mock 实践

# 1. 只 mock 外部依赖，不 mock 被测代码
def test_good_mocking(mocker):
    mock_external = mocker.patch("external.api.call")
    # 测试自己的代码
    result = my_function()
    assert result == expected

# 2. 使用具体的 mock 验证
def test_specific_verification(mocker):
    mock_send = mocker.patch("module.send_email")
    send_email(to="user@example.com", subject="Test")
    mock_send.assert_called_once_with(
        to="user@example.com",
        subject="Test"
    )

# 3. 清理 mock 状态
def test_with_cleanup(mocker):
    mock = mocker.patch("module.func")
    # 测试...
    mock.reset_mock()  # 重置状态
    # 继续测试...

# ❌ 不好的 Mock 实践

# 1. 过度 mock - mock 了太多东西
def test_bad_over_mocking(mocker):
    mocker.patch("module.func1")
    mocker.patch("module.func2")
    mocker.patch("module.func3")
    # 这样测试的意义是什么？

# 2. Mock 内部实现细节
def test_implementation_details(mocker):
    # 不要测试内部实现，测试行为
    mock_internal = mocker.patch("module._internal_helper")
    # ❌ 这会让重构变得困难

# 3. 没有验证的 mock
def test_unverified_mock(mocker):
    mock_api = mocker.patch("module.api")
    result = process()
    # ❌ 没有验证 mock 是否被调用
```

---

## 四、测试覆盖率要求

### 4.1 覆盖率指标

| 指标 | 说明 | 推荐值 |
|-----|------|--------|
| **语句覆盖率** (Statement) | 执行的语句比例 | 80%+ |
| **分支覆盖率** (Branch) | 执行的分支比例 | 70%+ |
| **函数覆盖率** (Function) | 执行的函数比例 | 90%+ |
| **行覆盖率** (Line) | 执行的行比例 | 80%+ |

### 4.2 覆盖率目标建议

```
┌─────────────────────────────────────────────────────┐
│  测试覆盖率目标 (BobQuant 建议)                       │
├─────────────────────────────────────────────────────┤
│  核心交易逻辑    ████████████████████  90%+         │
│  数据处理模块    ██████████████████░░  85%+         │
│  API 集成层       ████████████████░░░░  80%+         │
│  工具函数       ██████████████████░░  85%+         │
│  配置/常量      ████████░░░░░░░░░░░░  40%+         │
│  E2E 测试覆盖    ████████████░░░░░░░░  60%+         │
└─────────────────────────────────────────────────────┘
```

### 4.3 覆盖率配置

```ini
# .coveragerc 或 pytest.ini
[run]
source = src
branch = True
omit = 
    */tests/*
    */__pycache__/*
    */migrations/*
    */venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:

show_missing = True
fail_under = 80
```

### 4.4 覆盖率陷阱

> ⚠️ **重要**：100% 覆盖率 ≠ 没有 bug

**覆盖率高但测试质量差的情况**：

```python
# ❌ 有覆盖率但没有测试价值
def test_with_coverage():
    result = complex_function()
    assert result is not None  # 只验证不为空，没验证正确性

# ✅ 有意义的测试
def test_with_assertion():
    result = complex_function(input_data)
    assert result.expected_value == 42
    assert result.status == "success"
    assert len(result.items) == 5
```

### 4.5 不追求 100% 覆盖的代码

```python
# 以下代码可以豁免覆盖率要求：

# 1. 简单的 getter/setter
@property
def name(self):
    return self._name

# 2. 日志和调试代码
def debug_log(msg):
    if DEBUG:
        print(f"DEBUG: {msg}")

# 3. 类型检查导入
if TYPE_CHECKING:
    from typing import List

# 4. 异常处理的边缘情况
try:
    risky_operation()
except VerySpecificRareError:
    log_error()  # 很难触发
```

---

## 五、CI/CD 流程和质量门禁

### 5.1 GitHub Actions CI 配置

```yaml
# .github/workflows/ci.yml
name: BobQuant CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Lint with flake8
        run: |
          flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 src --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

      - name: Type check with mypy
        run: |
          mypy src --ignore-missing-imports

      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=src --cov-report=xml

      - name: Run integration tests
        run: |
          pytest tests/integration -v --cov=src --cov-report=xml --cov-append
        env:
          TEST_DATABASE_URL: sqlite:///test.db
          API_KEY: ${{ secrets.TEST_API_KEY }}

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=80

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run security scan
        run: |
          pip install bandit
          bandit -r src -f json -o bandit-report.json

      - name: Check dependencies
        run: |
          pip install safety
          safety check --json > safety-report.json

  build:
    needs: [test, security]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Build package
        run: |
          pip install build
          python -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
```

### 5.2 质量门禁 (Quality Gates)

```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate

on:
  pull_request:
    branches: [main]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      
      # 代码格式检查
      - name: Check code format (Black)
        run: |
          black src tests --check
      
      # 代码风格检查
      - name: Lint (flake8)
        run: |
          flake8 src tests --max-line-length=127
      
      # 类型检查
      - name: Type check (mypy)
        run: |
          mypy src --ignore-missing-imports
      
      # 测试运行
      - name: Run tests
        run: |
          pytest tests/ -v --tb=short
      
      # 覆盖率检查
      - name: Check coverage
        run: |
          pytest tests/ --cov=src --cov-report=term-missing
          coverage report --fail-under=80
      
      # 安全扫描
      - name: Security scan
        run: |
          bandit -r src -ll
      
      # 依赖检查
      - name: Check vulnerabilities
        run: |
          safety check
```

### 5.3 预提交钩子 (Pre-commit Hooks)

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=127]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests, types-PyYAML]
```

### 5.4 CI/CD 流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    开发者提交代码                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Pre-commit Hooks                          │
│  • 格式检查 (Black)  • 风格检查 (flake8)  • 类型检查 (mypy)   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   GitHub Actions CI                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Lint      │  │    Test     │  │   Security  │         │
│  │  代码检查   │  │   单元测试   │  │   安全扫描   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
┌─────────────────────┐       ┌─────────────────────┐
│     ✅ 全部通过      │       │     ❌ 检查失败      │
│                     │       │                     │
│  • 允许合并          │       │  • 阻止合并          │
│  • 触发部署          │       │  • 通知开发者        │
│  • 更新覆盖率报告    │       │  • 显示错误信息      │
└─────────────────────┘       └─────────────────────┘
```

---

## 六、测试最佳实践清单

### 6.1 测试编写原则 (FIRST)

| 原则 | 说明 |
|-----|------|
| **F**ast | 测试要快，快速反馈 |
| **I**ndependent | 测试独立，不互相依赖 |
| **R**epeatable | 可重复，环境一致 |
| **S**elf-validating | 自动验证，无需人工检查 |
| **T**imely | 及时编写，最好 TDD |

### 6.2 单元测试最佳实践

```python
# ✅ 好的单元测试

# 1. 测试命名清晰
def test_calculate_profit_with_positive_return():
    pass

def test_calculate_profit_with_negative_return():
    pass

def test_calculate_profit_with_zero_investment():
    pass

# 2. Arrange-Act-Assert 模式
def test_user_registration():
    # Arrange - 准备数据
    user_data = {"email": "test@example.com", "password": "secret"}
    
    # Act - 执行操作
    result = register_user(user_data)
    
    # Assert - 验证结果
    assert result.success is True
    assert result.user.email == "test@example.com"

# 3. 一个测试一个概念
def test_email_validation():
    # 只测试邮箱验证
    pass

def test_password_strength():
    # 只测试密码强度
    pass

# 4. 测试边界条件
def test_boundary_conditions():
    assert process(0) == expected_zero
    assert process(1) == expected_one
    assert process(-1) == expected_negative
    assert process(MAX_VALUE) == expected_max
    assert process(MAX_VALUE + 1) == expected_overflow
```

### 6.3 测试数据管理

```python
# conftest.py - 共享测试 fixtures

import pytest
from datetime import datetime

@pytest.fixture
def sample_stock_data():
    return {
        "symbol": "AAPL",
        "price": 150.00,
        "volume": 1000000,
        "timestamp": datetime(2024, 1, 1, 9, 30)
    }

@pytest.fixture
def mock_trading_session():
    class MockSession:
        def __init__(self):
            self.is_open = True
            self.orders = []
        
        def place_order(self, symbol, quantity, side):
            order = {"symbol": symbol, "quantity": quantity, "side": side}
            self.orders.append(order)
            return order
        
        def cancel_order(self, order_id):
            pass
    
    return MockSession()

@pytest.fixture
def temp_database(tmp_path):
    db_path = tmp_path / "test.db"
    db = create_database(db_path)
    yield db
    cleanup_database(db)
```

### 6.4 测试反模式（避免这些）

```python
# ❌ 避免的测试反模式

# 1. 测试依赖顺序
def test_first():
    global_state = setup()  # 影响下一个测试

def test_second():
    # 依赖 test_first 的状态
    assert global_state == expected

# 2. 测试中有睡眠
def test_with_sleep():
    result = async_function()
    time.sleep(5)  # ❌ 应该用等待条件
    assert result.is_ready()

# 3. 测试生产环境
def test_production():
    # ❌ 永远不要测试生产环境
    result = call_production_api()

# 4. 过度复杂的测试
def test_everything():
    # ❌ 测试太多东西
    setup_database()
    create_user()
    place_order()
    check_inventory()
    send_notification()
    verify_payment()
    # ... 100 行测试代码

# 5. 断言模糊
def test_vague():
    result = process()
    assert result  # ❌ 验证什么？
    assert result is not None  # ❌ 太弱
```

### 6.5 BobQuant 测试规范

```markdown
## BobQuant 测试规范

### 文件命名
- 单元测试：`test_<module>.py`
- 集成测试：`test_<feature>_integration.py`
- E2E 测试：`test_<workflow>_e2e.py`

### 标记使用
- `@pytest.mark.unit` - 单元测试
- `@pytest.mark.integration` - 集成测试
- `@pytest.mark.e2e` - E2E 测试
- `@pytest.mark.slow` - 慢速测试
- `@pytest.mark.data_source` - 数据源相关

### 覆盖率要求
- 核心交易逻辑：≥90%
- 数据处理模块：≥85%
- API 层：≥80%
- 总体覆盖率：≥80%

### CI 检查
- 所有 PR 必须通过单元测试
- 覆盖率不得低于 80%
- 无安全漏洞
- 代码格式符合规范
```

---

## 七、可借鉴到 BobQuant 的测试体系

### 7.1 BobQuant 测试架构设计

```
bobquant/tests/
├── unit/
│   ├── strategy/
│   │   ├── test_ma_strategy.py
│   │   ├── test_rsi_strategy.py
│   │   └── test_macd_strategy.py
│   ├── data/
│   │   ├── test_tencent_fetcher.py
│   │   ├── test_baostock_fetcher.py
│   │   └── test_data_processor.py
│   ├── trading/
│   │   ├── test_order_executor.py
│   │   ├── test_position_manager.py
│   │   └── test_risk_controller.py
│   └── utils/
│       ├── test_logger.py
│       └── test_helpers.py
│
├── integration/
│   ├── test_data_pipeline.py        # 数据获取→处理→存储
│   ├── test_signal_generation.py    # 数据→信号生成
│   ├── test_order_lifecycle.py      # 信号→下单→成交
│   └── test_api_integrations.py     # 外部 API 集成
│
└── e2e/
    ├── test_full_trading_day.py     # 完整交易日流程
    ├── test_strategy_backtest.py    # 策略回测流程
    └── test_sim_trading_session.py  # 模拟盘会话
```

### 7.2 BobQuant 专用 Test Fixtures

```python
# tests/conftest.py

import pytest
from datetime import datetime, time

@pytest.fixture
def trading_hours():
    """交易时段配置"""
    return {
        "morning_start": time(9, 25),
        "morning_end": time(11, 30),
        "afternoon_start": time(13, 0),
        "afternoon_end": time(15, 0),
    }

@pytest.fixture
def sample_stock_prices():
    """示例股票价格数据"""
    return {
        "AAPL": [150.0, 152.0, 148.0, 155.0, 153.0],
        "GOOGL": [2800.0, 2820.0, 2780.0, 2850.0, 2830.0],
        "TSLA": [200.0, 205.0, 198.0, 210.0, 207.0],
    }

@pytest.fixture
def mock_tencent_api(mocker):
    """Mock 腾讯财经 API"""
    mock_api = mocker.patch("bobquant.data.tencent.fetcher")
    mock_api.get_realtime.return_value = {
        "symbol": "sh600000",
        "price": 10.50,
        "change": 0.05,
        "volume": 1000000,
    }
    return mock_api

@pytest.fixture
def mock_baostock(mocker):
    """Mock Baostock 历史数据"""
    mock_bs = mocker.patch("bobquant.data.baostock.fetcher")
    mock_bs.get_history.return_value = [
        {"date": "2024-01-01", "open": 10.0, "close": 10.5},
        {"date": "2024-01-02", "open": 10.5, "close": 10.8},
        {"date": "2024-01-03", "open": 10.8, "close": 10.6},
    ]
    return mock_bs

@pytest.fixture
def sim_trading_config():
    """模拟盘配置"""
    return {
        "initial_capital": 1000000,
        "max_position": 0.3,
        "stop_loss": 0.05,
        "take_profit": 0.10,
    }
```

### 7.3 BobQuant 核心模块测试示例

```python
# tests/unit/strategy/test_ma_strategy.py

import pytest
from bobquant.strategy.ma_strategy import MAStrategy

class TestMAStrategy:
    
    def test_calculate_ma(self):
        """测试移动平均计算"""
        prices = [10, 12, 11, 13, 14]
        strategy = MAStrategy(period=3)
        
        ma = strategy.calculate_ma(prices)
        assert ma == pytest.approx(12.67, rel=0.01)
    
    def test_generate_buy_signal(self):
        """测试买入信号生成"""
        strategy = MAStrategy(period=5)
        prices = [10, 11, 12, 13, 14]  # 上涨趋势
        
        signal = strategy.generate_signal(prices)
        assert signal.action == "BUY"
        assert signal.confidence > 0.7
    
    def test_generate_sell_signal(self):
        """测试卖出信号生成"""
        strategy = MAStrategy(period=5)
        prices = [14, 13, 12, 11, 10]  # 下跌趋势
        
        signal = strategy.generate_signal(prices)
        assert signal.action == "SELL"
        assert signal.confidence > 0.7
    
    def test_no_signal_in_sideways(self):
        """测试震荡市无信号"""
        strategy = MAStrategy(period=5)
        prices = [10, 10.1, 9.9, 10.05, 9.95]  # 震荡
        
        signal = strategy.generate_signal(prices)
        assert signal.action == "HOLD"

# tests/integration/test_data_pipeline.py

import pytest
from bobquant.data.pipeline import DataPipeline

class TestDataPipeline:
    
    def test_full_pipeline(self, mock_tencent_api):
        """测试完整数据流程"""
        pipeline = DataPipeline()
        
        # 获取→处理→存储
        result = pipeline.process("sh600000")
        
        assert result.success is True
        assert result.data is not None
        assert len(result.data) > 0
    
    def test_pipeline_error_handling(self, mocker):
        """测试错误处理"""
        mock_tencent_api = mocker.patch("bobquant.data.tencent.fetcher")
        mock_tencent_api.get_realtime.side_effect = ConnectionError("Network error")
        
        pipeline = DataPipeline()
        result = pipeline.process("sh600000")
        
        assert result.success is False
        assert result.error is not None

# tests/e2e/test_sim_trading_session.py

import pytest
from bobquant.sim_trading.session import SimTradingSession

@pytest.mark.e2e
@pytest.mark.slow
class TestSimTradingSession:
    
    def test_full_trading_day(self, sim_trading_config):
        """测试完整交易日"""
        session = SimTradingSession(**sim_trading_config)
        
        # 开盘
        session.market_open()
        assert session.is_trading is True
        
        # 执行若干交易
        session.place_order("sh600000", 1000, "BUY")
        session.place_order("sh600000", 500, "SELL")
        
        # 收盘
        session.market_close()
        assert session.is_trading is False
        
        # 验证结果
        report = session.generate_report()
        assert report.total_trades == 2
        assert report.final_capital > 0
```

### 7.4 BobQuant CI/CD 配置

```yaml
# .github/workflows/bobquant-ci.yml

name: BobQuant CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    # 每个交易日 9:00 运行
    - cron: '0 1 * * 1-5'

jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r requirements-dev.txt
      - name: Run unit tests
        run: pytest tests/unit -v --cov=bobquant --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  test-integration:
    runs-on: ubuntu-latest
    needs: test-unit
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r requirements-dev.txt
      - name: Run integration tests
        run: pytest tests/integration -v
        env:
          TENCENT_API_KEY: ${{ secrets.TENCENT_API_KEY }}
          BAOSTOCK_ENABLED: true

  test-e2e:
    runs-on: ubuntu-latest
    needs: test-integration
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r requirements-dev.txt
      - name: Run E2E tests
        run: pytest tests/e2e -v -m e2e

  deploy:
    runs-on: ubuntu-latest
    needs: [test-unit, test-integration, test-e2e]
    if: github.ref == 'refs/heads/main' && success()
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        run: |
          echo "Deploying BobQuant..."
          # 部署逻辑
```

---

## 八、总结与行动清单

### 8.1 核心要点总结

1. **测试金字塔**：大量单元测试 + 适量集成测试 + 少量 E2E 测试
2. **Mock/Stub**：隔离依赖，提高测试速度和可靠性
3. **覆盖率**：追求有意义的覆盖，而非数字游戏
4. **CI/CD**：自动化测试是质量保障的核心
5. **最佳实践**：FIRST 原则，AAA 模式，清晰的测试命名

### 8.2 BobQuant 测试体系建设步骤

```
Step 1: 搭建测试框架
├── 安装 pytest, pytest-cov, pytest-mock
├── 创建 tests/ 目录结构
├── 配置 pytest.ini 和 conftest.py
└── 设置 .coveragerc

Step 2: 编写单元测试
├── 为核心模块编写单元测试
├── 覆盖率目标：80%+
└── 使用 Mock 隔离外部依赖

Step 3: 编写集成测试
├── 测试数据流程
├── 测试 API 集成
└── 测试模块间交互

Step 4: 编写 E2E 测试
├── 测试完整交易流程
├── 测试模拟盘会话
└── 标记为 slow，CI 中可选运行

Step 5: 配置 CI/CD
├── 设置 GitHub Actions
├── 配置质量门禁
├── 设置预提交钩子
└── 集成覆盖率报告

Step 6: 持续改进
├── 定期审查测试质量
├── 补充边缘情况测试
├── 优化测试速度
└── 更新文档
```

### 8.3 推荐资源

- 📚 《Python Testing with pytest》- Brian Okken
- 📚 《Test-Driven Development with Python》- Harry J.W. Percival
- 🌐 https://docs.pytest.org/
- 🌐 https://martinfowler.com/articles/practical-test-pyramid.html
- 🌐 https://www.guru99.com/software-testing.html

---

> 💡 **最后提醒**：测试的目的是建立信心，不是追求数字。好的测试让你敢于重构，坏的测试让你寸步难行。
