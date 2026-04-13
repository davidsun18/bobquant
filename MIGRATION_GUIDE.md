# BobQuant 重构迁移指南

**版本**: v1.0  
**创建时间**: 2026-04-11  
**适用版本**: BobQuant v1.x → v2.x  
**状态**: ✅ 完成

---

## 📋 目录

1. [迁移总览](#1-迁移总览)
2. [旧版 vs 新版对比](#2-旧版-vs-新版对比)
3. [逐步迁移指南](#3-逐步迁移指南)
4. [常见问题解答 (FAQ)](#4-常见问题解答-faq)
5. [代码迁移示例](#5-代码迁移示例)
6. [兼容性说明](#6-兼容性说明)
7. [回滚方案](#7-回滚方案)

---

## 1. 迁移总览

### 1.1 为什么需要迁移？

BobQuant v2.x 是经过全面重构的现代化量化交易系统，相比 v1.x 版本有以下核心改进：

- 🏗️ **模块化架构**: 清晰的目录结构和职责分离
- 🛡️ **增强的风险管理**: 8 项风控检查 + 大盘风控系统
- 📊 **先进的技术指标**: 双 MACD 过滤 + 动态布林带
- 🚀 **智能执行系统**: TWAP/VWAP 订单执行器
- 🧠 **机器学习集成**: 三重障碍法标签生成
- 📱 **现代化 UI**: Streamlit 多页面可视化看板

### 1.2 迁移时间估算

| 任务 | 预计时间 | 难度 |
|------|---------|------|
| 环境准备 | 15 分钟 | ⭐ |
| 配置文件迁移 | 30 分钟 | ⭐⭐ |
| 策略代码迁移 | 60 分钟 | ⭐⭐⭐ |
| 数据迁移 | 30 分钟 | ⭐⭐ |
| 测试验证 | 60 分钟 | ⭐⭐⭐ |
| **总计** | **约 3-4 小时** | **中等** |

### 1.3 迁移前准备

#### 检查清单
- [ ] 备份当前 v1.x 代码和数据
- [ ] 确认 Python 版本 ≥ 3.8
- [ ] 检查依赖包版本
- [ ] 准备测试环境
- [ ] 阅读本迁移指南

#### 备份命令
```bash
# 备份整个项目
cd /home/openclaw/.openclaw/workspace/quant_strategies
cp -r bobquant bobquant_backup_$(date +%Y%m%d)

# 备份配置文件
cp config/settings.yaml config/settings_backup.yaml
cp config/stock_pool.yaml config/stock_pool_backup.yaml

# 备份交易记录
cp -r logs/ logs_backup_$(date +%Y%m%d)
cp -r reports/ reports_backup_$(date +%Y%m%d)
```

---

## 2. 旧版 vs 新版对比

### 2.1 架构对比

| 特性 | v1.x (旧版) | v2.x (新版) |
|------|------------|------------|
| 架构风格 | 单体式 | 模块化 |
| 代码组织 | 扁平结构 | 分层架构 |
| 配置管理 | 硬编码 | YAML 配置驱动 |
| 日志系统 | print + 简单日志 | 结构化日志 |
| 错误处理 | 基础 try-catch | 统一异常管理 |
| 测试覆盖 | 无/少 | 单元测试 + 集成测试 |

### 2.2 目录结构对比

#### v1.x 结构
```
bobquant/
├── main.py              # 所有逻辑在一个文件
├── config.py            # 配置
├── strategy.py          # 策略
├── indicator.py         # 指标
├── backtest.py          # 回测
└── utils.py             # 工具函数
```

#### v2.x 结构
```
bobquant/
├── main.py              # 入口文件
├── config/
│   ├── settings.yaml    # 系统配置
│   └── stock_pool.yaml  # 股票池配置
├── core/
│   ├── account.py       # 账户管理
│   ├── executor.py      # 订单执行
│   ├── risk_filters.py  # 风险过滤
│   └── market_risk.py   # 大盘风控
├── strategy/
│   ├── engine.py        # 策略引擎
│   ├── multi_factor.py  # 多因子策略
│   ├── rebalance.py     # 调仓策略
│   └── high_frequency.py# 高频策略
├── indicator/
│   └── technical.py     # 技术指标
├── data/
│   ├── provider.py      # 数据接口
│   ├── tushare_provider.py
│   └── akshare_provider.py
├── ml/
│   ├── features.py      # 特征工程
│   └── predictor.py     # 预测模型
├── backtest/
│   ├── engine.py        # 回测引擎
│   └── config.yaml      # 回测配置
├── order_execution/
│   └── twap_executor.py # TWAP/VWAP 执行
├── risk_management/
│   └── risk_manager.py  # 风险管理器
├── web/
│   ├── streamlit_app.py # Streamlit UI
│   └── dash_app.py      # Dash UI
└── tools/               # 工具集
```

### 2.3 功能对比

| 功能模块 | v1.x | v2.x | 改进说明 |
|---------|------|------|---------|
| MACD 指标 | ✅ 单周期 | ✅ 双周期 | 短周期 (6,13,5) + 长周期 (24,52,18) |
| 布林带 | ✅ 固定参数 | ✅ 动态参数 | 根据波动率自适应调整 |
| 风险控制 | ⚠️ 基础 | ✅ 增强 | 8 项检查 + 大盘风控 |
| 订单执行 | ✅ 市价单 | ✅ TWAP/VWAP | 大单拆分，降低冲击 |
| ML 标签 | ⚠️ 简单涨跌 | ✅ 三重障碍法 | 止盈/止损/时间三维 |
| 数据源 | ✅ 腾讯财经 | ✅ 多源 | 腾讯 + Tushare + Akshare |
| UI 界面 | ⚠️ 单页面 | ✅ 多页面 | 5 个功能页面 + 导航 |
| 回测系统 | ⚠️ 基础 | ✅ 专业 | 完整牛熊周期验证 |

### 2.4 API 变更

#### 策略引擎 API

**v1.x**:
```python
# 旧版调用方式
signal = generate_signal(code, data)
if signal == 'buy':
    buy(code, price, shares)
```

**v2.x**:
```python
# 新版调用方式
from bobquant.strategy.engine import StrategyEngine

engine = StrategyEngine(config_path='config/settings.yaml')
signal = engine.generate_signal(code, data)
if signal.action == 'buy':
    engine.execute_order(signal)
```

#### 风险管理 API

**v1.x**:
```python
# 简单止盈止损
if current_price < avg_price * 0.95:
    sell(code)
```

**v2.x**:
```python
# 综合风控检查
from bobquant.risk_management.risk_manager import RiskManager

risk_mgr = RiskManager(limits, initial_capital=1000000)
allowed, reason = risk_mgr.check_order(code, 'buy', quantity, price)
if allowed:
    execute_order(code, 'buy', quantity, price)
```

#### 数据获取 API

**v1.x**:
```python
# 单一数据源
df = get_data(code, days=60)
```

**v2.x**:
```python
# 多数据源支持
from bobquant.data.provider import DataProvider

provider = DataProvider(source='tushare')  # 或 'akshare', 'yfinance'
df = provider.get_history_data(code, days=60)
```

---

## 3. 逐步迁移指南

### 3.1 环境准备 (15 分钟)

#### 步骤 1: 检查 Python 版本
```bash
python3 --version
# 要求：Python 3.8+
```

#### 步骤 2: 安装依赖
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
pip3 install -r requirements.txt
```

#### 步骤 3: 验证安装
```bash
# 测试核心模块
python3 -c "from bobquant.core import account; print('✅ Core OK')"
python3 -c "from bobquant.strategy import engine; print('✅ Strategy OK')"
python3 -c "from bobquant.data import provider; print('✅ Data OK')"
```

### 3.2 配置文件迁移 (30 分钟)

#### 步骤 1: 创建新配置目录
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
mkdir -p config
```

#### 步骤 2: 迁移系统配置

**创建 `config/settings.yaml`**:
```yaml
# BobQuant v2.x 系统配置

# 策略配置
strategy:
  name: "dual_macd"  # 策略名称：dual_macd, bollinger, ml
  signal:
    use_dual_macd: true
    dual_macd_short: [6, 13, 5]
    dual_macd_long: [24, 52, 18]
    use_dynamic_bollinger: true
    bollinger_std_high: 2.5
    bollinger_std_low: 1.8

# 风险管理
risk_management:
  filters:
    enabled: true
    min_turnover: 50000000  # 5000 万
    check_st: true
  market_risk:
    enabled: true
    ma20_line: 20
    max_position_bear: 0.5
    crash_threshold: -0.03
  limits:
    max_position_value: 500000
    max_portfolio_exposure: 2000000
    max_drawdown: 0.10
    max_daily_loss: 50000

# 订单执行
execution:
  use_twap: true
  twap_threshold: 10000  # 大于 10000 股使用 TWAP
  twap_duration_minutes: 10
  twap_slices: 5

# 数据源
data:
  primary_source: "tencent"  # tencent, tushare, akshare
  cache_enabled: true
  cache_ttl_hours: 24

# 日志
logging:
  level: "INFO"
  file: "logs/bobquant.log"
  max_size_mb: 100
  backup_count: 5
```

#### 步骤 3: 迁移股票池配置

**创建 `config/stock_pool.yaml`**:
```yaml
# BobQuant v2.x 股票池配置

stock_pool:
  name: "优化版股票池 v2.0"
  total_stocks: 50
  
  # 行业配比
  sectors:
    bank_finance:
      name: "银行金融"
      weight: 0.15
      stocks:
        - {code: "601398", name: "工商银行", strategy: "bollinger"}
        - {code: "601288", name: "农业银行", strategy: "bollinger"}
        # ... 更多股票
    
    tech_semiconductor:
      name: "科技/半导体"
      weight: 0.20
      stocks:
        - {code: "688981", name: "中芯国际", strategy: "dual_macd"}
        - {code: "002371", name: "北方华创", strategy: "dual_macd"}
        # ... 更多股票
    
    # ... 其他行业
```

### 3.3 策略代码迁移 (60 分钟)

#### 步骤 1: 迁移 MACD 策略

**旧代码位置**: `strategy.py`  
**新代码位置**: `strategy/engine.py`

```python
# 旧代码 (v1.x)
def macd_strategy(df):
    dif = EMA(df['close'], 12) - EMA(df['close'], 26)
    dea = EMA(dif, 9)
    macd = 2 * (dif - dea)
    
    if macd > 0:
        return 'buy'
    elif macd < 0:
        return 'sell'
    return 'hold'

# 新代码 (v2.x) - 在 strategy/engine.py 中
from bobquant.indicator.technical import calculate_dual_macd

class DualMACDStrategy:
    def generate_signal(self, df):
        # 双 MACD 过滤
        short_macd, long_macd = calculate_dual_macd(df)
        
        # 双确认机制
        if (short_macd['macd'] > short_macd['signal'] and 
            long_macd['macd'] > long_macd['signal']):
            return {'action': 'buy', 'confidence': 0.8}
        elif (short_macd['macd'] < short_macd['signal'] and 
              long_macd['macd'] < long_macd['signal']):
            return {'action': 'sell', 'confidence': 0.8}
        return {'action': 'hold', 'confidence': 0.5}
```

#### 步骤 2: 迁移布林带策略

```python
# 旧代码 (v1.x)
def bollinger_strategy(df):
    mid = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    
    if df['close'][-1] < lower:
        return 'buy'
    elif df['close'][-1] > upper:
        return 'sell'
    return 'hold'

# 新代码 (v2.x) - 支持动态参数
from bobquant.indicator.technical import calculate_dynamic_bollinger

class BollingerStrategy:
    def generate_signal(self, df):
        # 动态布林带（根据波动率调整）
        bollinger = calculate_dynamic_bollinger(df)
        
        if df['close'][-1] < bollinger['lower']:
            return {'action': 'buy', 'confidence': 0.7}
        elif df['close'][-1] > bollinger['upper']:
            return {'action': 'sell', 'confidence': 0.7}
        return {'action': 'hold', 'confidence': 0.5}
```

#### 步骤 3: 集成风险管理

```python
# 在 strategy/engine.py 中添加风控检查
from bobquant.risk_management.risk_manager import RiskManager, RiskLimits

class StrategyEngine:
    def __init__(self, config):
        # 初始化风控管理器
        limits = RiskLimits(
            max_position_value=config['risk_management']['limits']['max_position_value'],
            max_portfolio_exposure=config['risk_management']['limits']['max_portfolio_exposure'],
            max_drawdown=config['risk_management']['limits']['max_drawdown'],
            max_daily_loss=config['risk_management']['limits']['max_daily_loss']
        )
        self.risk_mgr = RiskManager(limits, initial_capital=1000000)
    
    def execute_order(self, signal):
        # 风控检查
        allowed, reason = self.risk_mgr.check_order(
            signal.code, 
            signal.action, 
            signal.quantity, 
            signal.price
        )
        
        if not allowed:
            logger.warning(f"订单被风控拦截：{reason}")
            return False
        
        # 执行订单
        return self.executor.execute(signal)
```

### 3.4 数据迁移 (30 分钟)

#### 步骤 1: 迁移历史数据
```bash
# 备份旧数据
cp -r data/ data_backup

# 新数据目录结构
mkdir -p data/daily
mkdir -p data/minute
mkdir -p data/cache
```

#### 步骤 2: 更新数据接口
```python
# 旧代码
def get_data(code, days=60):
    url = f"http://data.gtimg.cn/flashdata/hushen/minute/{code}.js"
    # ... 解析数据

# 新代码 - 使用统一接口
from bobquant.data.provider import DataProvider

provider = DataProvider(source='tencent')
df = provider.get_history_data(code, days=60, frequency='daily')
```

### 3.5 测试验证 (60 分钟)

#### 步骤 1: 单元测试
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant

# 测试技术指标
python3 -m pytest tests/test_indicator.py -v

# 测试策略引擎
python3 -m pytest tests/test_strategy.py -v

# 测试风控模块
python3 -m pytest tests/test_risk.py -v
```

#### 步骤 2: 回测验证
```bash
# 运行回测
python3 backtest/run_backtest.py dual_macd 2024-01-01 2024-12-31

# 查看回测报告
cat backtest_results/dual_macd_2024_report.json
```

#### 步骤 3: 模拟盘测试
```bash
# 启动模拟盘
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
./start_sim_v2_2.sh

# 查看日志
tail -f sim_trading/模拟盘日志.log
```

---

## 4. 常见问题解答 (FAQ)

### Q1: 迁移后策略信号不准确怎么办？

**A**: 检查以下配置：
1. 确认 `config/settings.yaml` 中策略参数正确
2. 验证数据源是否正常（测试数据接口）
3. 检查技术指标计算是否正确
4. 对比 v1.x 和 v2.x 的信号差异

```bash
# 测试数据接口
python3 data/test_akshare.py
python3 data/test_tushare.py
```

### Q2: 风控系统频繁拦截订单怎么办？

**A**: 调整风控参数：
```yaml
# config/settings.yaml
risk_management:
  limits:
    max_position_value: 500000  # 提高单笔限额
    max_daily_loss: 50000       # 提高日亏损限额
```

### Q3: TWAP 执行效果不佳怎么办？

**A**: 优化 TWAP 参数：
```yaml
# config/settings.yaml
execution:
  twap_threshold: 10000      # 调整触发阈值
  twap_duration_minutes: 15  # 延长执行时间
  twap_slices: 10            # 增加拆分份数
```

### Q4: Streamlit 看板无法访问怎么办？

**A**: 检查服务状态：
```bash
# 检查进程
ps aux | grep streamlit

# 检查端口
netstat -tlnp | grep 8501

# 重启服务
pkill -f "streamlit run"
./start_streamlit.sh
```

### Q5: 回测结果与实盘差异大怎么办？

**A**: 考虑以下因素：
1. 滑点成本（设置合理的滑点参数）
2. 交易手续费（确认费率设置）
3. 数据质量（使用复权数据）
4. 市场冲击（大单使用 TWAP）

```yaml
# backtest/config.yaml
backtest:
  commission_rate: 0.0003    # 万三手续费
  slippage: 0.002            # 0.2% 滑点
  use_adjusted_price: true   # 使用复权价格
```

### Q6: 如何迁移自定义策略？

**A**: 遵循以下步骤：
1. 在 `strategy/` 目录创建新策略文件
2. 继承 `BaseStrategy` 基类
3. 实现 `generate_signal()` 方法
4. 在 `config/settings.yaml` 中注册策略

```python
# strategy/my_custom_strategy.py
from bobquant.strategy.base import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def generate_signal(self, df):
        # 你的策略逻辑
        return {'action': 'buy', 'confidence': 0.8}
```

### Q7: 数据源切换后数据不一致怎么办？

**A**: 检查数据源配置：
```yaml
# config/settings.yaml
data:
  primary_source: "tushare"  # 切换数据源
  cache_enabled: false       # 禁用缓存测试
```

### Q8: 如何备份和恢复配置？

**A**: 使用备份脚本：
```bash
# 备份配置
cp config/settings.yaml config/settings_backup_$(date +%Y%m%d).yaml

# 恢复配置
cp config/settings_backup_20260411.yaml config/settings.yaml
```

---

## 5. 代码迁移示例

### 5.1 主程序迁移

#### Before (v1.x)
```python
# main.py - 旧版主程序
import pandas as pd
from strategy import macd_strategy
from utils import get_data, buy, sell

def main():
    stocks = ['601398', '601288', '000001']
    
    for code in stocks:
        df = get_data(code, days=60)
        signal = macd_strategy(df)
        
        if signal == 'buy':
            buy(code, df['close'][-1], 1000)
        elif signal == 'sell':
            sell(code, df['close'][-1], 1000)

if __name__ == '__main__':
    main()
```

#### After (v2.x)
```python
# main.py - 新版主程序
from bobquant.core.executor import OrderExecutor
from bobquant.strategy.engine import StrategyEngine
from bobquant.data.provider import DataProvider
from bobquant.config.loader import load_config

def main():
    # 加载配置
    config = load_config('config/settings.yaml')
    
    # 初始化组件
    data_provider = DataProvider(source=config['data']['primary_source'])
    strategy_engine = StrategyEngine(config)
    executor = OrderExecutor(config)
    
    # 获取股票池
    stocks = config['stock_pool']['stocks']
    
    for stock in stocks:
        # 获取数据
        df = data_provider.get_history_data(stock['code'], days=60)
        
        # 生成信号
        signal = strategy_engine.generate_signal(stock['code'], df)
        
        # 执行订单（包含风控检查）
        if signal['action'] != 'hold':
            executor.execute_order(signal)

if __name__ == '__main__':
    main()
```

### 5.2 技术指标迁移

#### Before (v1.x)
```python
# indicator.py - 旧版指标计算
def calculate_macd(df):
    dif = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
    dea = dif.ewm(span=9).mean()
    macd = 2 * (dif - dea)
    return dif, dea, macd

def calculate_bollinger(df):
    mid = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    return upper, mid, lower
```

#### After (v2.x)
```python
# indicator/technical.py - 新版指标计算
import pandas as pd
import numpy as np

def calculate_dual_macd(df, short_params=(6,13,5), long_params=(24,52,18)):
    """
    双 MACD 计算
    
    Parameters:
    - df: DataFrame with OHLCV data
    - short_params: 短周期参数 (fast, slow, signal)
    - long_params: 长周期参数 (fast, slow, signal)
    
    Returns:
    - short_macd: 短周期 MACD 字典
    - long_macd: 长周期 MACD 字典
    """
    # 短周期 MACD
    short_dif = df['close'].ewm(span=short_params[0]).mean() - \
                df['close'].ewm(span=short_params[1]).mean()
    short_dea = short_dif.ewm(span=short_params[2]).mean()
    short_macd = 2 * (short_dif - short_dea)
    
    # 长周期 MACD
    long_dif = df['close'].ewm(span=long_params[0]).mean() - \
               df['close'].ewm(span=long_params[1]).mean()
    long_dea = long_dif.ewm(span=long_params[2]).mean()
    long_macd = 2 * (long_dif - long_dea)
    
    return {
        'macd': short_macd.iloc[-1],
        'signal': short_dea.iloc[-1],
        'histogram': (short_macd - short_dea).iloc[-1]
    }, {
        'macd': long_macd.iloc[-1],
        'signal': long_dea.iloc[-1],
        'histogram': (long_macd - long_dea).iloc[-1]
    }

def calculate_dynamic_bollinger(df, period=20):
    """
    动态布林带（根据波动率调整标准差倍数）
    
    Parameters:
    - df: DataFrame with OHLCV data
    - period: 均线周期
    
    Returns:
    - bollinger: 布林带字典 (upper, mid, lower, std_multiplier)
    """
    mid = df['close'].rolling(period).mean()
    
    # 计算波动率
    returns = df['close'].pct_change()
    volatility = returns.rolling(period).std() * np.sqrt(252)
    
    # 根据波动率分位数调整标准差倍数
    vol_percentile = volatility.iloc[-1] / volatility.rolling(252).max().iloc[-1]
    
    if vol_percentile > 0.75:
        num_std = 2.5  # 高波动
    elif vol_percentile < 0.25:
        num_std = 1.8  # 低波动
    else:
        num_std = 2.0  # 中等波动
    
    std = df['close'].rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    
    return {
        'upper': upper.iloc[-1],
        'mid': mid.iloc[-1],
        'lower': lower.iloc[-1],
        'std_multiplier': num_std
    }
```

### 5.3 风险管理迁移

#### Before (v1.x)
```python
# risk.py - 旧版风控
def check_risk(position, current_price):
    avg_price = position['avg_price']
    
    # 简单止盈止损
    if current_price < avg_price * 0.95:
        return False, '止损'
    if current_price > avg_price * 1.20:
        return False, '止盈'
    
    return True, '通过'
```

#### After (v2.x)
```python
# risk_management/risk_manager.py - 新版风控
from dataclasses import dataclass
from typing import Tuple

@dataclass
class RiskLimits:
    max_position_value: float = 500000
    max_portfolio_exposure: float = 2000000
    max_drawdown: float = 0.10
    max_daily_loss: float = 50000
    max_position_pct: float = 0.20
    max_sector_pct: float = 0.40
    min_turnover: float = 50000000
    max_positions: int = 20

class RiskManager:
    def __init__(self, limits: RiskLimits, initial_capital: float):
        self.limits = limits
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        self.daily_start_capital = initial_capital
    
    def check_order(self, code: str, side: str, quantity: float, 
                    price: float) -> Tuple[bool, str]:
        """
        订单风控检查
        
        Returns:
        - allowed: 是否允许
        - reason: 原因
        """
        order_value = quantity * price
        
        # 1. 单笔订单金额检查
        if order_value > self.limits.max_position_value:
            return False, f"单笔订单金额超限 ({order_value:.2f} > {self.limits.max_position_value:.2f})"
        
        # 2. 组合总敞口检查
        total_exposure = self.calculate_total_exposure()
        if side == 'buy' and total_exposure + order_value > self.limits.max_portfolio_exposure:
            return False, f"组合总敞口超限"
        
        # 3. 回撤检查
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if current_drawdown > self.limits.max_drawdown:
            return False, f"回撤超限 ({current_drawdown:.2%} > {self.limits.max_drawdown:.2%})"
        
        # 4. 单日亏损检查
        daily_loss = self.daily_start_capital - self.current_capital
        if daily_loss > self.limits.max_daily_loss:
            return False, f"单日亏损超限 ({daily_loss:.2f} > {self.limits.max_daily_loss:.2f})"
        
        # 5. 持仓集中度检查
        position_pct = self.calculate_position_pct(code)
        if side == 'buy' and position_pct + order_value/self.current_capital > self.limits.max_position_pct:
            return False, f"持仓集中度超限"
        
        # 6. 行业集中度检查
        sector_pct = self.calculate_sector_pct(code)
        if side == 'buy' and sector_pct + order_value/self.current_capital > self.limits.max_sector_pct:
            return False, f"行业集中度超限"
        
        # 7. 流动性检查
        turnover = self.get_stock_turnover(code)
        if turnover < self.limits.min_turnover:
            return False, f"流动性不足 (成交额 {turnover:.2f} < {self.limits.min_turnover:.2f})"
        
        # 8. 持仓数量检查
        if side == 'buy' and self.count_positions() >= self.limits.max_positions:
            return False, f"持仓数量超限"
        
        return True, "通过风控检查"
    
    def update_capital(self, new_capital: float):
        """更新资金状态"""
        self.current_capital = new_capital
        if new_capital > self.peak_capital:
            self.peak_capital = new_capital
    
    def reset_daily(self):
        """重置每日状态"""
        self.daily_start_capital = self.current_capital
    
    # ... 辅助方法实现略
```

---

## 6. 兼容性说明

### 6.1 Python 版本兼容性

| Python 版本 | v1.x | v2.x | 说明 |
|-----------|------|------|------|
| 3.6 | ✅ | ❌ | v2.x 不再支持 |
| 3.7 | ✅ | ⚠️ | 部分功能受限 |
| 3.8+ | ✅ | ✅ | 推荐版本 |
| 3.9+ | ✅ | ✅ | 最佳性能 |
| 3.10+ | ⚠️ | ✅ | 完全支持 |

### 6.2 依赖包兼容性

| 包名 | v1.x 版本 | v2.x 版本 | 变更说明 |
|------|----------|----------|---------|
| pandas | ≥1.0 | ≥1.3 | 需要新版本 API |
| numpy | ≥1.18 | ≥1.20 | 性能优化 |
| ta-lib | 可选 | 推荐 | 技术指标加速 |
| streamlit | - | ≥1.0 | 新增 UI 框架 |
| plotly | ≥4.0 | ≥5.0 | 图表库升级 |

### 6.3 数据格式兼容性

**v1.x 数据格式**:
```csv
date,open,high,low,close,volume
2024-01-01,10.5,10.8,10.3,10.7,1000000
```

**v2.x 数据格式** (向后兼容):
```csv
trade_date,open,high,low,close,vol,amount
2024-01-01,10.5,10.8,10.3,10.7,1000000,10700000
```

v2.x 自动适配两种格式，无需手动转换。

### 6.4 配置文件兼容性

**v1.x 配置** (Python 字典):
```python
# config.py
CONFIG = {
    'macd_short': 12,
    'macd_long': 26,
    'stop_loss': 0.05
}
```

**v2.x 配置** (YAML):
```yaml
# config/settings.yaml
strategy:
  macd:
    short: 12
    long: 26
risk_management:
  stop_loss: 0.05
```

### 6.5 API 向后兼容性

v2.x 提供兼容层，支持 v1.x 的 API 调用：

```python
# v2.x 兼容 v1.x 调用
from bobquant.compat.v1 import get_data, buy, sell

# 旧代码无需修改即可运行
df = get_data('601398', days=60)
buy('601398', df['close'][-1], 1000)
```

**注意**: 兼容层将在 v3.0 中移除，建议尽快迁移到新 API。

---

## 7. 回滚方案

### 7.1 回滚场景

以下情况建议回滚到 v1.x：
- v2.x 出现严重 Bug 影响交易
- 性能不满足要求
- 关键功能缺失
- 数据兼容性问题

### 7.2 回滚步骤

#### 步骤 1: 停止 v2.x 服务
```bash
# 停止所有 v2.x 进程
pkill -f "streamlit run"
pkill -f "python3.*main.py"
pkill -f "bobquant"
```

#### 步骤 2: 恢复备份
```bash
# 恢复代码
cd /home/openclaw/.openclaw/workspace/quant_strategies
rm -rf bobquant
mv bobquant_backup_20260411 bobquant

# 恢复配置
cp config/settings_backup.yaml config/settings.yaml
cp config/stock_pool_backup.yaml config/stock_pool.yaml

# 恢复数据
rm -rf data/
mv data_backup data
```

#### 步骤 3: 重启 v1.x 服务
```bash
cd /home/openclaw/.openclaw/workspace/quant_strategies/bobquant
./start_v1.sh
```

#### 步骤 4: 验证回滚
```bash
# 检查进程
ps aux | grep "python3.*main.py"

# 查看日志
tail -f logs/bobquant.log

# 测试交易
curl http://localhost:8050/api/health
```

### 7.3 回滚检查清单

- [ ] v2.x 服务已完全停止
- [ ] 备份文件完整
- [ ] 代码已恢复
- [ ] 配置已恢复
- [ ] 数据已恢复
- [ ] v1.x 服务已启动
- [ ] 日志正常
- [ ] 交易功能正常

### 7.4 回滚后注意事项

1. **数据同步**: 回滚期间产生的交易记录需要手动同步
2. **配置差异**: v1.x 可能不支持 v2.x 的新配置项
3. **功能限制**: v1.x 缺少 v2.x 的新功能（双 MACD、TWAP 等）

### 7.5 快速回滚脚本

创建 `rollback_v1.sh`:
```bash
#!/bin/bash

echo "🔄 开始回滚到 v1.x..."

# 1. 停止 v2.x 服务
echo "⏹️  停止 v2.x 服务..."
pkill -f "streamlit run"
pkill -f "python3.*main.py"
sleep 2

# 2. 恢复备份
echo "📦 恢复备份..."
cd /home/openclaw/.openclaw/workspace/quant_strategies

if [ -d "bobquant_backup_$(date +%Y%m%d)" ]; then
    rm -rf bobquant
    mv bobquant_backup_$(date +%Y%m%d) bobquant
    echo "✅ 代码已恢复"
else
    echo "❌ 备份文件不存在"
    exit 1
fi

# 3. 重启 v1.x 服务
echo "▶️  启动 v1.x 服务..."
cd bobquant
./start_v1.sh

# 4. 验证
sleep 5
if ps aux | grep -q "[p]ython3.*main.py"; then
    echo "✅ 回滚成功！v1.x 已运行"
else
    echo "❌ 回滚失败，请检查日志"
    exit 1
fi

echo "🎉 回滚完成"
```

使用：
```bash
chmod +x rollback_v1.sh
./rollback_v1.sh
```

---

## 📞 技术支持

### 文档资源
- **QUICKSTART.md**: 快速开始指南
- **STREAMLIT_README.md**: Streamlit 使用文档
- **UPGRADE_v2.md**: v2.0 升级说明
- **集成完成报告.md**: 集成详情

### 日志位置
- 系统日志：`logs/bobquant.log`
- 交易日志：`sim_trading/模拟盘日志.log`
- Streamlit 日志：`/tmp/streamlit.log`

### 常见问题
详见第 4 节 FAQ

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team  
**版本**: v1.0
