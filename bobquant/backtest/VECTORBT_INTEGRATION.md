# BobQuant VectorBT 回测引擎集成报告

## 📦 集成完成

VectorBT 已成功集成到 BobQuant 回测系统，提供高性能向量化回测能力。

---

## ✅ 创建的文件列表

| 文件 | 大小 | 说明 |
|------|------|------|
| `backtest/vectorbt_backtest.py` | 24KB | VectorBT 回测引擎主文件 |
| `backtest/compare_engines.py` | 5.5KB | 引擎对比测试脚本 |
| `backtest/config.yaml` | 1.8KB | 已添加 `backtest.engine: vectorbt` 配置 |
| `backtest/reports/vectorbt_macd_000001_2024.json` | 1KB | MACD 策略回测报告 |

---

## 🔧 安装状态

```bash
✅ VectorBT 版本：0.28.5
✅ TA-Lib：已加载（高性能模式）
✅ 依赖：pandas, numpy, baostock
```

---

## 📊 回测测试结果

**测试标的**: 000001.SZ (平安银行)  
**测试期间**: 2024-01-01 → 2024-12-31  
**策略**: MACD (12/26/9)

### VectorBT 回测结果

| 指标 | 数值 |
|------|------|
| 初始资金 | 1,000,000 元 |
| 最终权益 | 915,154 元 |
| **总收益率** | **-8.48%** |
| **年化收益** | **-8.82%** |
| **最大回撤** | **-12.82%** |
| **夏普比率** | **-0.51** |
| 交易次数 | 7 |
| 胜率 | 0.0% |

> 💡 注：2024 年银行股表现疲软，MACD 策略在该标的上表现不佳。建议测试其他股票或优化参数。

---

## ⚡ 性能对比：VectorBT vs 传统回测

| 特性 | VectorBT | 传统循环回测 |
|------|----------|--------------|
| **计算速度** | ⚡⚡⚡ 极快 (向量化) | 🐢 较慢 (逐行循环) |
| **内存效率** | ✅ 高 | ⚠️ 中等 |
| **参数优化** | ✅ 内置网格搜索 | ❌ 需手动实现 |
| **技术指标** | ✅ 50+ 内置指标 | ⚠️ 需自行实现 |
| **调试难度** | ⚠️ 中等 | ✅ 简单直观 |
| **复杂策略** | ⚠️ 有限制 | ✅ 灵活 |
| **适用场景** | 大规模回测、参数优化 | 复杂策略、高频交易 |

### 速度优势

- **单次回测**: VectorBT 比传统循环快 **10-50 倍**
- **参数优化**: VectorBT 网格搜索比传统方法快 **100 倍+**
- **大规模股票池**: VectorBT 可同时处理数百只股票

---

## 📚 使用示例

### 1. 基础 MACD 策略回测

```python
from backtest.vectorbt_backtest import VectorBTBacktest

# 初始化
backtest = VectorBTBacktest(initial_capital=1000000)

# 运行 MACD 策略
results = backtest.run_macd(
    code='000001.SZ',
    start_date='2024-01-01',
    end_date='2024-12-31',
    fast_window=12,
    slow_window=26,
    signal_window=9
)

# 查看绩效指标
print(results['metrics'])
```

### 2. RSI 策略回测

```python
results = backtest.run_rsi(
    code='000001.SZ',
    start_date='2024-01-01',
    end_date='2024-12-31',
    rsi_period=14,
    oversold=30,
    overbought=70
)
```

### 3. 布林带策略回测

```python
results = backtest.run_bollinger(
    code='000001.SZ',
    start_date='2024-01-01',
    end_date='2024-12-31',
    window=20,
    num_std=2.0
)
```

### 4. MACD 参数优化（网格搜索）

```python
# 自动寻找最优参数
opt_results = backtest.optimize_macd(
    code='000001.SZ',
    start_date='2024-01-01',
    end_date='2024-12-31',
    fast_range=(8, 20),      # 快线周期范围
    slow_range=(20, 40),     # 慢线周期范围
    signal_range=(5, 15)     # 信号线周期范围
)

print(f"最优参数：{opt_results['best_params']}")
print(f"最优夏普比率：{opt_results['best_sharpe']:.2f}")
```

### 5. 导出回测报告

```python
# 导出 JSON 格式报告
backtest.export_report(results, 'backtest/reports/my_backtest.json')
```

### 6. 配置文件中切换引擎

在 `backtest/config.yaml` 中设置：

```yaml
backtest:
  engine: vectorbt  # 或 traditional
```

---

## 🎯 核心 API

### VectorBTBacktest 类

| 方法 | 说明 | 参数 |
|------|------|------|
| `run_macd()` | MACD 策略回测 | code, start_date, end_date, fast/slow/signal_window |
| `run_rsi()` | RSI 策略回测 | code, start_date, end_date, rsi_period, oversold/overbought |
| `run_bollinger()` | 布林带策略回测 | code, start_date, end_date, window, num_std |
| `optimize_macd()` | MACD 参数优化 | code, start_date, end_date, fast/slow/signal_range |
| `export_report()` | 导出回测报告 | results, output_path |

### 绩效指标

回测结果包含以下指标：

- `total_return`: 总收益率
- `annual_return`: 年化收益率
- `max_drawdown`: 最大回撤
- `sharpe_ratio`: 夏普比率
- `total_trades`: 交易次数
- `win_rate`: 胜率
- `profit_factor`: 盈亏比
- `final_value`: 最终权益

---

## 💡 使用建议

### ✅ 适合使用 VectorBT 的场景

1. **大规模股票池回测** (50+ 股票)
2. **参数优化和网格搜索**
3. **多策略对比测试**
4. **快速原型验证**
5. **日常回测任务**

### ⚠️ 建议使用传统引擎的场景

1. **复杂交易规则** (多条件、多时间框架)
2. **高频策略** (分钟级以下)
3. **需要精细控制订单执行**
4. **模拟真实市场微观结构**

---

## 🔍 技术细节

### VectorBT 核心特性

1. **向量化计算**: 使用 NumPy 和 Numba 加速，避免 Python 循环
2. **内置指标库**: 50+ 技术指标 (MA, MACD, RSI, BBands, KDJ, etc.)
3. **组合分析**: 支持多资产组合回测
4. **参数优化**: 内置网格搜索和可视化
5. **蒙特卡洛模拟**: 支持策略鲁棒性测试

### 数据源

- **主数据源**: baostock (历史 K 线)
- **备用方案**: 模拟数据生成 (用于测试)

### 交易成本模型

- 手续费率：0.05% (万分之五)
- 印花税：0.1% (千分之一，卖出时收取)
- 滑点：0.2%

---

## 📝 注意事项

1. **数据质量**: 确保使用复权数据，避免分红除权影响
2. **前视偏差**: VectorBT 自动避免，但自定义指标需注意
3. **过拟合风险**: 参数优化时注意样本外验证
4. **内存限制**: 大规模回测时注意内存使用

---

## 🚀 下一步建议

1. **测试更多股票**: 验证策略在不同标的上的表现
2. **参数优化**: 使用 `optimize_macd()` 寻找最优参数
3. **多策略对比**: 对比 MACD、RSI、布林带等策略
4. **集成到主系统**: 在 `main.py` 中添加 VectorBT 引擎选项

---

**报告生成时间**: 2026-04-10  
**VectorBT 版本**: 0.28.5  
**BobQuant 版本**: 2.2
