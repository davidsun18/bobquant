# QuantStats + Dual Thrust 集成说明

**日期**: 2026-04-08  
**执行状态**: ✅ 已完成

---

## 📦 已安装组件

### 1. QuantStats 绩效分析库
- **版本**: 0.0.81
- **位置**: `/home/openclaw/.local/lib/python3.10/site-packages/quantstats`
- **功能**: 50+ 风险指标、HTML 报告、蒙特卡洛模拟

### 2. 新增模块

#### `performance_analyzer.py`
**位置**: `quant_strategies/performance_analyzer.py`

**核心类**:
- `PerformanceAnalyzer`: 绩效分析器
  - 计算夏普比率、Sortino、最大回撤等
  - 生成 HTML 报告
  - 蒙特卡洛模拟
  - 支持从 JSON 加载交易记录

- `DualThrustStrategy`: Dual Thrust 策略实现
  - Range 计算
  - 信号生成
  - 简单回测

#### `strategies/dual_thrust.py`
**位置**: `quant_strategies/strategies/dual_thrust.py`

**核心类**:
- `DualThrustSignal`: 信号生成器
  - 时间过滤（避免尾盘假突破）
  - 成交量确认
  - 可调参数（lookback, k1, k2）

- `DualThrustBacktester`: 回测器
  - 考虑手续费和滑点
  - 输出权益曲线
  - 绩效统计

---

## 🚀 使用方法

### 1. 分析现有交易记录

```python
from performance_analyzer import PerformanceAnalyzer

# 创建分析器
analyzer = PerformanceAnalyzer(initial_capital=100000.0)

# 加载交易记录
analyzer.load_trades_from_json('sim_trading/交易记录.json')

# 获取绩效指标
metrics = analyzer.get_metrics()
print(f"夏普比率：{metrics['夏普比率']:.2f}")
print(f"最大回撤：{metrics['最大回撤']*100:.2f}%")
print(f"胜率：{metrics['胜率']*100:.1f}%")

# 生成 HTML 报告
report_path = analyzer.generate_html_report(
    output_path='backtest_results/performance_report_20260408.html',
    title='模拟盘绩效报告 2026-04'
)
```

### 2. 使用 Dual Thrust 策略

```python
from strategies.dual_thrust import DualThrustSignal, DualThrustBacktester
import pandas as pd

# 创建策略
strategy = DualThrustSignal(
    lookback=4,      # 4 日回看
    k1=0.5,          # 上轨系数
    k2=0.5,          # 下轨系数
    volume_confirm=True,    # 启用成交量确认
    time_filter=True        # 启用时间过滤
)

# 生成信号
signal = strategy.generate_signal(
    df=kline_data,          # K 线 DataFrame
    current_price=1500.0,   # 当前价格
    current_time=datetime.now(),
    volume=current_volume,
    avg_volume=avg_20_volume,
    code='sh.600519'
)

if signal['action'] == 'buy' and signal['strength'] >= 0.5:
    print(f"买入信号！强度：{signal['strength']:.2f}")
    print(f"原因：{signal['reason']}")
```

### 3. 回测 Dual Thrust 策略

```python
# 创建回测器
backtester = DualThrustBacktester(
    initial_capital=100000.0,
    position_size=0.2,
    commission=0.0003,  # 万三手续费
    slippage=0.001      # 千一滑点
)

# 运行回测
results = backtester.run_backtest(kline_df, strategy)

# 获取绩效
performance = backtester.get_performance()
print(performance)
```

---

## 📊 绩效指标说明

### 收益指标
- **总收益率**: 累计收益率
- **年化收益率**: 年化复利收益率
- **夏普比率**: 风险调整后收益（>1 为优）
- **Sortino 比率**: 只考虑下行波动的夏普比率

### 风险指标
- **最大回撤**: 最大峰值到谷底的跌幅
- **波动率**: 收益率标准差（年化）
- **VaR 95%**: 95% 置信度下的最大日损失
- **CVaR 95%**: 超过 VaR 的平均损失

### 交易统计
- **胜率**: 盈利交易占比
- **收益风险比**: 年化收益/波动率
- **Calmar 比率**: 年化收益/最大回撤

---

## 🎯 Dual Thrust 策略参数优化建议

### 默认参数（适合 A 股）
```python
lookback = 4      # 4 日回看
k1 = 0.5          # 上轨系数
k2 = 0.5          # 下轨系数
```

### 激进型（更多信号）
```python
lookback = 3
k1 = 0.3
k2 = 0.3
```

### 保守型（更少但更准）
```python
lookback = 5
k1 = 0.7
k2 = 0.7
```

### 时间过滤（避免假突破）
- 早盘：09:45 - 11:20（避开开盘 15 分钟和午盘前 10 分钟）
- 午盘：13:00 - 14:45（避开尾盘 15 分钟）

---

## 📁 文件结构

```
quant_strategies/
├── performance_analyzer.py       # QuantStats 集成模块
├── strategies/
│   └── dual_thrust.py            # Dual Thrust 策略实现
├── backtest_results/             # 回测报告和 HTML
├── sim_trading/
│   └── 交易记录.json              # 现有交易记录（兼容）
└── research/
    └── 2026-04-08-github-research.md  # GitHub 调研报告
```

---

## 🔄 与现有系统集成

### 1. 添加到交易引擎

在 `medium_frequency/signal_generator.py` 中添加：

```python
from strategies.dual_thrust import DualThrustSignal

class SignalGenerator:
    def __init__(self):
        self.dual_thrust = DualThrustSignal(
            lookback=4,
            k1=0.5,
            k2=0.5,
            volume_confirm=True,
            time_filter=True
        )
    
    def generate_signals(self, code, kline_data):
        # 现有逻辑...
        
        # 添加 Dual Thrust 信号
        dt_signal = self.dual_thrust.generate_signal(
            df=kline_data,
            current_price=current_price,
            current_time=datetime.now(),
            volume=volume,
            avg_volume=avg_volume,
            code=code
        )
        
        if dt_signal['action'] == 'buy' and dt_signal['strength'] >= 0.5:
            signals.append({
                'type': 'dual_thrust',
                'action': 'buy',
                'strength': dt_signal['strength'],
                'reason': dt_signal['reason']
            })
```

### 2. 添加到绩效评估

在每日/每周报告中添加 QuantStats 分析：

```python
from performance_analyzer import PerformanceAnalyzer

def generate_daily_report():
    analyzer = PerformanceAnalyzer(initial_capital=500000.0)
    analyzer.load_trades_from_json('sim_trading/交易记录.json')
    
    metrics = analyzer.get_metrics()
    
    report = f"""
    📊 绩效日报
    - 总收益率：{metrics['总收益率']*100:.2f}%
    - 夏普比率：{metrics['夏普比率']:.2f}
    - 最大回撤：{metrics['最大回撤']*100:.2f}%
    - 胜率：{metrics['胜率']*100:.1f}%
    """
    
    return report
```

---

## ⚠️ 注意事项

1. **QuantStats 依赖**: 需要 `yfinance`，但 A 股数据需用本地数据
2. **数据格式**: 交易记录需包含 `time`, `profit` 字段
3. **回测准确性**: 考虑 A 股 T+1 限制，当日买入不可卖出
4. **参数调优**: 建议先用历史数据回测，再实盘

---

## 📝 后续优化方向

1. **集成到现有三阶段引擎**: 将 Dual Thrust 作为策略信号源之一
2. **参数自动优化**: 使用网格搜索找到最优参数
3. **多策略组合**: 结合现有趋势策略和 Dual Thrust
4. **实时绩效监控**: 在 Web UI 中展示 QuantStats 指标

---

*执行完成时间：2026-04-08 07:30*
