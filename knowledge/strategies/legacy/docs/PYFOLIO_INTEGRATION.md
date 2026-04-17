# PyFolio 绩效分析集成指南

## 概述

BobQuant 已成功集成 PyFolio 绩效分析模块，提供专业级的投资组合绩效分析功能。

## 功能特性

### 1. 风险收益指标
- **总收益率** (Total Return)
- **年化收益** (Annual Return)
- **波动率** (Volatility)
- **Sharpe 比率** - 风险调整收益
- **Sortino 比率** - 下行风险调整收益
- **Calmar 比率** - 回撤调整收益
- **最大回撤** (Max Drawdown)
- **下行风险** (Downside Risk)

### 2. 图表分析
- **收益曲线图** - 累计收益走势
- **回撤分析图** - Underwater Plot
- **月度收益热力图** - 月度收益分布
- **收益分布直方图** - 收益分布特征
- **滚动 Sharpe 比率** - 风险调整收益变化
- **滚动波动率** - 风险变化趋势

### 3. 持仓分析
- 持仓标的数量
- 平均持仓规模
- 最大持仓规模
- 持仓周转率

### 4. HTML 报告
- 专业的 HTML 格式报告
- 包含所有图表和指标
- 可直接在浏览器中查看

## 安装

PyFolio 已通过 pip 安装：

```bash
pip3 install pyfolio
```

依赖项：
- pyfolio 0.9.2
- empyrical 0.5.5
- pandas-datareader 0.10.0

## 使用方法

### 基础用法

```python
from bobquant.analysis.pyfolio_analysis import PyFolioAnalyzer, generate_report, format_report

# 创建分析器
analyzer = PyFolioAnalyzer(initial_capital=500000.0)

# 准备交易数据
# trades_df 需要包含以下列：
# - date: 交易日期
# - code: 股票代码
# - pnl: 盈亏金额
# - amount: 交易金额（可选）
# - direction: 交易方向 1=买入，-1=卖出（可选）

# 生成报告
report = analyzer.generate_report(trades_df)

# 打印文本报告
print(format_report(report))
```

### 便捷函数

```python
from bobquant.analysis.pyfolio_analysis import generate_report, format_report

# 一键生成报告
report = generate_report(trades_df, initial_capital=500000.0)
print(format_report(report))
```

### 访问详细数据

```python
# 获取指标
metrics = report['metrics']
print(f"Sharpe Ratio: {metrics['sharpe']:.3f}")
print(f"Max Drawdown: {metrics['max_drawdown']*100:.2f}%")

# 获取回撤分析
drawdown = report['drawdown']
print(f"Max Drawdown: {drawdown['max_drawdown']*100:.2f}%")

# 获取月度热力图
heatmap = report['monthly_heatmap']

# 获取持仓分析
positions = report['positions']

# 获取 HTML 报告路径
html_path = report['html_report']
```

## 数据格式要求

交易数据 DataFrame 应包含以下列：

| 列名 | 类型 | 必填 | 说明 |
|------|------|------|------|
| date | datetime/date | ✅ | 交易日期 |
| code | str | ✅ | 股票代码 |
| pnl | float | ✅ | 盈亏金额 |
| amount | float | ❌ | 交易金额 |
| shares | int | ❌ | 交易股数 |
| price | float | ❌ | 交易价格 |
| direction | int | ❌ | 交易方向 (1=买入，-1=卖出) |
| action | str | ❌ | 交易动作 (buy/sell) |

## 示例：分析模拟盘数据

```python
import pandas as pd
import json
from bobquant.analysis.pyfolio_analysis import PyFolioAnalyzer

# 加载交易记录
with open('sim_trading/交易记录.json', 'r') as f:
    trades = json.load(f)

# 转换为 DataFrame
df = pd.DataFrame(trades)
df['date'] = pd.to_datetime(df['time']).dt.date
df['pnl'] = df['profit'].fillna(0)
df['code'] = df['code'].apply(lambda x: x.replace('.', ''))

# 运行分析
analyzer = PyFolioAnalyzer(initial_capital=500000.0)
report = analyzer.generate_report(df)

# 输出结果
from bobquant.analysis.pyfolio_analysis import format_report
print(format_report(report))
```

## 输出示例

```
======================================================================
📊 PyFolio 绩效分析报告
======================================================================
交易天数：60
时间范围：2024-01-01 至 2024-02-29

📈 核心风险收益指标:
  总收益率：    +0.35%
  年化收益：    +1.46%
  波动率：      8.65%
  Sharpe 比率：  -0.178
  Sortino 比率： -0.300
  Calmar 比率：  0.265
  最大回撤：    -5.50%
  下行风险：    0.00%

🎯 交易统计:
  胜率：        48.3%
  最佳交易日：  +1.21%
  最差交易日：  -1.08%

📉 回撤分析:
  最大回撤：    -5.50%
  显著回撤次数：8 (>5%)

💼 持仓分析:
  标的数量：    10

📄 HTML 报告：reports/pyfolio/pyfolio_report_20260411_002833.html
======================================================================
```

## 与现有模块集成

PyFolio 分析模块已集成到 `bobquant.analysis` 包中：

```python
from bobquant.analysis import (
    PyFolioAnalyzer,
    pyfolio_generate_report,
    pyfolio_format_report
)
```

## 注意事项

1. **数据量要求**: 建议至少有 30 个交易日的數據以生成有意义的统计指标
2. **HTML 报告**: 需要至少 30 个交易日才会生成 HTML 报告
3. **numpy 兼容性**: 当前版本使用自定义实现避免 numpy 2.0 兼容性问题
4. **初始资金**: 设置合理的 initial_capital 以准确计算收益率

## 报告输出位置

- HTML 报告：`bobquant/reports/pyfolio/`
- PNG 图表：`bobquant/reports/pyfolio/`

## 测试

运行集成测试：

```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies
python3 bobquant/tests/test_pyfolio_integration.py
```

## 文件结构

```
bobquant/
├── analysis/
│   ├── __init__.py              # 模块导出
│   ├── performance.py           # 原有绩效分析（quantstats）
│   └── pyfolio_analysis.py      # PyFolio 绩效分析（新增）
├── tests/
│   └── test_pyfolio_integration.py  # 集成测试（新增）
└── reports/
    └── pyfolio/                 # PyFolio 报告输出目录
        ├── pyfolio_report_*.html
        └── pyfolio_report_*.png
```

## 性能指标说明

### Sharpe 比率
- > 1: 良好
- > 2: 优秀
- > 3: 非常优秀

### Sortino 比率
- 只考虑下行风险，更适合评估风险调整收益

### Calmar 比率
- 年化收益 / 最大回撤
- > 3: 优秀
- > 5: 非常优秀

### 最大回撤
- 投资者应关注是否能承受该回撤幅度
- 一般建议 < 20%

## 更新日志

### v1.0 - 2026-04-11
- ✅ 初始版本发布
- ✅ 集成 PyFolio 0.9.2
- ✅ 实现核心绩效指标计算
- ✅ 实现收益曲线、回撤、热力图等图表
- ✅ 生成 HTML 报告
- ✅ 与现有 analysis 模块集成
- ✅ 添加集成测试
