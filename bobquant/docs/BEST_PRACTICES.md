# BobQuant 最佳实践

开发和交易中的最佳实践指南。

---

## 📋 目录

1. [策略开发](#策略开发)
2. [风险管理](#风险管理)
3. [代码规范](#代码规范)
4. [性能优化](#性能优化)
5. [调试技巧](#调试技巧)
6. [部署运维](#部署运维)

---

## 策略开发

### 1. 策略设计原则

#### ✅ 好的策略特征

- **逻辑清晰**: 策略逻辑应该简单明了，易于理解
- **参数合理**: 参数应该有经济意义，避免过度拟合
- **风控完善**: 内置止损、仓位控制等风控措施
- **可回测**: 策略应该能够进行历史回测
- **可执行**: 考虑实际交易的滑点、手续费等

#### ❌ 避免的陷阱

- **过度拟合**: 不要在历史数据上过度优化
- **未来函数**: 避免使用未来数据
- **幸存者偏差**: 考虑退市股票
- **忽略成本**: 考虑手续费、滑点、冲击成本

### 2. 策略开发流程

```
1. 想法 → 2. 实现 → 3. 回测 → 4. 优化 → 5. 模拟 → 6. 实盘
```

#### 步骤 1: 想法

```python
# 明确策略逻辑
# 例：均线交叉策略
# - 当 5 日均线上穿 20 日均线时买入
# - 当 5 日均线下穿 20 日均线时卖出
```

#### 步骤 2: 实现

```python
from bobquant.strategy import Strategy
from bobquant.indicator import MA

class MAStrategy(Strategy):
    def on_init(self):
        self.ma5 = MA(5)
        self.ma20 = MA(20)
        self.last_signal = 0  # 0=无，1=多，-1=空
    
    def on_bar(self, bar):
        self.ma5.update(bar.close)
        self.ma20.update(bar.close)
        
        # 金叉
        if self.ma5.value > self.ma20.value and self.last_signal <= 0:
            self.buy(bar.symbol, 100)
            self.last_signal = 1
        
        # 死叉
        elif self.ma5.value < self.ma20.value and self.last_signal >= 0:
            self.sell(bar.symbol, self.get_position(bar.symbol))
            self.last_signal = -1
```

#### 步骤 3: 回测

```python
from bobquant.backtest import BacktestEngine

engine = BacktestEngine(
    strategy=MAStrategy(),
    start_date="2020-01-01",
    end_date="2023-12-31",
    initial_capital=1000000,
    commission_rate=0.0005,
    slippage=0.001
)

results = engine.run()
print(results.summary())
```

#### 步骤 4: 优化

```python
from bobquant.optimize import OptunaOptimizer

optimizer = OptunaOptimizer(
    strategy_class=MAStrategy,
    start_date="2020-01-01",
    end_date="2022-12-31"  # 使用部分数据优化
)

best_params = optimizer.optimize({
    "ma_fast_period": (3, 10),
    "ma_slow_period": (15, 30)
})

# 在样本外数据验证
engine = BacktestEngine(
    strategy=MAStrategy(**best_params),
    start_date="2023-01-01",
    end_date="2023-12-31"  # 样本外验证
)
```

#### 步骤 5: 模拟

```bash
# 模拟盘运行至少 1 个月
./start_sim_v2_2.sh
```

#### 步骤 6: 实盘

```bash
# 小资金开始
# config/settings.json5:
# {
#   "system": {"mode": "live"},
#   "account": {"initial_capital": 10000}
# }
python3 main.py
```

### 3. 策略模板

```python
"""
策略名称：XXX 策略
作者：XXX
日期：2026-04-11
版本：1.0

策略逻辑:
1. XXX
2. XXX
3. XXX

参数:
- param1: 说明
- param2: 说明

风险:
- XXX 风险
- XXX 风险
"""

from bobquant.strategy import Strategy
from bobquant.indicator import MA, MACD, RSI

class MyStrategy(Strategy):
    name = "my_strategy"
    version = "1.0"
    
    def __init__(self, config=None):
        super().__init__(config)
        # 参数
        self.param1 = config.get("param1", 10) if config else 10
        self.param2 = config.get("param2", 20) if config else 20
        
        # 状态
        self.initialized = False
    
    def on_init(self):
        """初始化"""
        self.logger.info("策略初始化")
        
        # 初始化指标
        self.ma1 = MA(self.param1)
        self.ma2 = MA(self.param2)
        
        # 加载历史数据
        self.load_history()
        
        self.initialized = True
    
    def on_start(self):
        """启动"""
        self.logger.info("策略启动")
        
        # 订阅行情
        self.subscribe(self.universe)
    
    def on_stop(self):
        """停止"""
        self.logger.info("策略停止")
        
        # 保存状态
        self.save_state()
        
        # 平仓 (可选)
        # self.close_all()
    
    def on_bar(self, bar):
        """K 线回调 - 主要策略逻辑"""
        if not self.initialized:
            return
        
        # 更新指标
        self.ma1.update(bar.close)
        self.ma2.update(bar.close)
        
        # 策略逻辑
        if self.should_buy(bar):
            self.buy(bar.symbol, self.calculate_quantity(bar))
        elif self.should_sell(bar):
            self.sell(bar.symbol, self.get_position(bar.symbol))
    
    def should_buy(self, bar) -> bool:
        """买入条件"""
        # 实现买入逻辑
        return (
            self.ma1.value > self.ma2.value and  # 均线金叉
            not self.get_position(bar.symbol)     # 无持仓
        )
    
    def should_sell(self, bar) -> bool:
        """卖出条件"""
        # 实现卖出逻辑
        return (
            self.ma1.value < self.ma2.value and  # 均线死叉
            self.get_position(bar.symbol) > 0     # 有持仓
        )
    
    def calculate_quantity(self, bar) -> int:
        """计算买入数量"""
        # 根据仓位管理计算
        available = self.account.available_cash
        quantity = int(available * 0.1 / bar.close / 100) * 100
        return max(100, quantity)
```

---

## 风险管理

### 1. 仓位管理

#### 单票仓位限制

```python
# config/settings.json5
{
  "position": {
    "max_position_pct": 0.10,  // 单票不超过 10%
    "max_total_position": 0.80, // 总仓位不超过 80%
    "max_positions": 10         // 最多持有 10 只
  }
}
```

#### 动态仓位

```python
def calculate_position_size(self, signal_strength):
    """根据信号强度动态调整仓位"""
    base_size = self.account.total_assets * 0.1
    
    # 信号强 (0.8-1.0): 满仓
    # 信号中 (0.5-0.8): 半仓
    # 信号弱 (0.3-0.5): 1/4 仓
    if signal_strength >= 0.8:
        return base_size
    elif signal_strength >= 0.5:
        return base_size * 0.5
    elif signal_strength >= 0.3:
        return base_size * 0.25
    else:
        return 0
```

### 2. 止损策略

#### 固定止损

```python
# 设置固定止损
self.set_stop_loss(
    symbol="600519",
    stop_loss_price=1700.0,  # 止损价
    stop_profit_price=2000.0  # 止盈价
)
```

#### 移动止损

```python
# 移动止损 (跟踪止损)
self.set_stop_loss(
    symbol="600519",
    trailing_stop=True,       # 启用移动止损
    trailing_percent=0.05,    # 回撤 5% 止损
    initial_stop=1700.0       # 初始止损价
)
```

#### ATR 止损

```python
from bobquant.indicator import ATR

atr = ATR(14)
atr.update(high, low, close)

# ATR 止损 = 入场价 - 2 * ATR
stop_loss = entry_price - 2 * atr.value
```

### 3. 风险指标监控

```python
from bobquant.risk_management import RiskManager

risk_mgr = RiskManager()

# 每日检查
def daily_risk_check():
    metrics = risk_mgr.get_risk_metrics()
    
    # VaR 检查
    if metrics.var_95 > 0.05:
        logger.warning(f"VaR 超标：{metrics.var_95:.2%}")
        reduce_position()
    
    # 回撤检查
    if metrics.max_drawdown > 0.10:
        logger.warning(f"回撤超标：{metrics.max_drawdown:.2%}")
        stop_trading()
    
    # 波动率检查
    if metrics.volatility > 0.03:
        logger.warning(f"波动率过高：{metrics.volatility:.2%}")
        reduce_leverage()
```

### 4. 黑天鹅防护

```python
# 设置最大亏损限制
{
  "risk": {
    "daily_loss_limit": 0.03,    // 单日亏损不超过 3%
    "weekly_loss_limit": 0.08,   // 单周亏损不超过 8%
    "monthly_loss_limit": 0.15,  // 单月亏损不超过 15%
    "max_drawdown": 0.20         // 最大回撤不超过 20%
  }
}

# 熔断机制
def circuit_breaker():
    daily_pnl = get_daily_pnl()
    
    if daily_pnl < -0.03:  # 亏损超过 3%
        logger.error("触发熔断，停止交易")
        close_all_positions()
        stop_trading()
        send_alert("触发熔断")
```

---

## 代码规范

### 1. 命名规范

```python
# 类名：大驼峰
class MyStrategy(Strategy):
    pass

# 函数名：小写 + 下划线
def calculate_position_size():
    pass

# 变量名：小写 + 下划线
position_size = 100

# 常量：大写 + 下划线
MAX_POSITION = 10000

# 私有方法：前缀下划线
def _internal_method():
    pass
```

### 2. 文档字符串

```python
class MyStrategy(Strategy):
    """
    多因子选股策略
    
    基于动量、价值、质量三个因子进行选股。
    
    Attributes:
        factors: 因子列表
        weights: 因子权重
        rebalance_days: 调仓周期
    
    Example:
        >>> strategy = MyStrategy(
        ...     factors=["momentum", "value"],
        ...     weights=[0.6, 0.4]
        ... )
        >>> engine = TradingEngine(strategy=strategy)
        >>> engine.start()
    """
    
    def on_bar(self, bar):
        """
        K 线数据回调
        
        Args:
            bar: K 线数据，包含 open/high/low/close/volume
        
        Returns:
            None
        """
        pass
```

### 3. 错误处理

```python
from bobquant.core import BobQuantError, ValidationError

def place_order(symbol, quantity, price):
    """
    下单函数
    
    Raises:
        ValidationError: 参数验证失败
        ExecutionError: 执行失败
    """
    try:
        # 验证参数
        if quantity <= 0:
            raise ValidationError("数量必须大于 0")
        
        if price <= 0:
            raise ValidationError("价格必须大于 0")
        
        # 执行下单
        result = broker.place_order(symbol, quantity, price)
        return result
        
    except ValidationError as e:
        logger.error(f"验证错误：{e}")
        raise
    except Exception as e:
        logger.error(f"未知错误：{e}")
        raise ExecutionError(f"下单失败：{e}")
```

### 4. 日志记录

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bobquant.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 使用日志
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")

# 带上下文
logger.info(f"买入 {symbol} {quantity}股 @ {price}")
```

---

## 性能优化

### 1. 数据缓存

```python
from functools import lru_cache
import hashlib

class DataProvider:
    @lru_cache(maxsize=1000)
    def get_bar_data(self, symbol, interval, start, end):
        """获取 K 线数据 (带缓存)"""
        # 生成缓存 key
        cache_key = hashlib.md5(
            f"{symbol}_{interval}_{start}_{end}".encode()
        ).hexdigest()
        
        # 检查缓存
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # 获取数据
        data = self._fetch_data(symbol, interval, start, end)
        
        # 存入缓存
        self.cache[cache_key] = data
        
        return data
```

### 2. 向量化计算

```python
import numpy as np
import pandas as pd

# ❌ 慢：循环计算
def calculate_returns_slow(prices):
    returns = []
    for i in range(1, len(prices)):
        returns.append(prices[i] / prices[i-1] - 1)
    return returns

# ✅ 快：向量化计算
def calculate_returns_fast(prices):
    return prices.pct_change().iloc[1:]

# ❌ 慢
def calculate_ma_slow(prices, period):
    ma = []
    for i in range(period, len(prices)):
        ma.append(np.mean(prices[i-period:i]))
    return ma

# ✅ 快
def calculate_ma_fast(prices, period):
    return prices.rolling(window=period).mean()
```

### 3. 并行处理

```python
from concurrent.futures import ProcessPoolExecutor

# 并行回测多只股票
def backtest_universe(stocks):
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(backtest_single, stocks))
    return results

def backtest_single(symbol):
    # 单只股票回测
    engine = BacktestEngine(...)
    return engine.run()
```

### 4. 内存优化

```python
# 使用 generator 而不是 list
def generate_signals(data):
    for bar in data:
        yield calculate_signal(bar)

# 使用 chunk 处理大数据
def process_large_data(file_path):
    for chunk in pd.read_csv(file_path, chunksize=10000):
        process_chunk(chunk)

# 及时删除不用的数据
def optimize_memory():
    data = load_data()
    result = process(data)
    del data  # 释放内存
    return result
```

---

## 调试技巧

### 1. 断点调试

```python
# 使用 pdb
import pdb

def debug_function():
    pdb.set_trace()  # 设置断点
    # 代码执行到这里会暂停
    # 可以使用 n(ext), s(tep), c(ontinue), l(ist) 等命令
```

### 2. 日志调试

```python
# 添加详细日志
logger.debug(f"on_bar 调用：{bar.symbol} {bar.close}")
logger.debug(f"MA5={self.ma5.value}, MA20={self.ma20.value}")
logger.debug(f"持仓：{self.get_position(bar.symbol)}")
```

### 3. 状态检查

```python
def check_state():
    """检查策略状态"""
    logger.info("=== 状态检查 ===")
    logger.info(f"账户资金：{self.account.total_assets}")
    logger.info(f"持仓数量：{len(self.positions)}")
    logger.info(f"今日交易：{self.today_trades}")
    logger.info(f"指标状态：MA5={self.ma5.value}")
```

### 4. 回测调试

```python
# 单步回测
engine = BacktestEngine(...)
engine.set_debug_mode(True)  # 启用调试模式

# 打印每笔交易
for trade in engine.run().trades:
    print(f"{trade.time} {trade.symbol} {trade.side} {trade.price}")
```

---

## 部署运维

### 1. 生产环境配置

```json5
// config/production.json5
{
  "system": {
    "mode": "live",
    "log_level": "WARNING",  // 生产环境减少日志
    "enable_notify": true
  },
  "risk": {
    "max_position_pct": 0.05,  // 生产环境更保守
    "max_drawdown": 0.10
  },
  "notify": {
    "feishu_webhook": "${env:FEISHU_WEBHOOK}",
    "send_on_trade": true,
    "send_on_error": true
  }
}
```

### 2. 进程守护

```bash
# 使用 systemd (推荐)
sudo systemctl start bobquant
sudo systemctl enable bobquant

# 或使用 supervisor
[program:bobquant]
command=/usr/bin/python3 main.py
directory=/home/openclaw/.openclaw/workspace/quant_strategies/bobquant
autostart=true
autorestart=true
```

### 3. 监控告警

```python
# 健康检查
def health_check():
    checks = {
        "process": check_process(),
        "data": check_data_freshness(),
        "account": check_account_status(),
        "risk": check_risk_limits()
    }
    
    if not all(checks.values()):
        send_alert("健康检查失败", checks)
        return False
    return True

# 定时执行
import schedule
schedule.every(5).minutes.do(health_check)
```

### 4. 日志轮转

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'bobquant.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5           # 保留 5 个备份
)
```

### 5. 备份策略

```bash
#!/bin/bash
# backup.sh

# 备份配置文件
cp -r config/ backup/config_$(date +%Y%m%d)

# 备份日志
tar -czf backup/logs_$(date +%Y%m%d).tar.gz logs/

# 备份交易记录
cp logs/trades.json backup/trades_$(date +%Y%m%d).json

# 删除 30 天前的备份
find backup/ -mtime +30 -delete
```

---

## 安全检查清单

### 上线前检查

- [ ] 策略经过充分回测 (至少 3 年数据)
- [ ] 模拟盘运行至少 1 个月
- [ ] 风控参数设置合理
- [ ] 止损策略已配置
- [ ] 通知渠道已测试
- [ ] 日志记录完整
- [ ] 备份机制已配置
- [ ] 应急方案已准备

### 日常检查

- [ ] 账户资金正常
- [ ] 持仓符合预期
- [ ] 当日盈亏正常
- [ ] 系统无报错
- [ ] 数据更新正常
- [ ] 通知接收正常

### 定期检查

- [ ] 每周审查策略表现
- [ ] 每月审查风险指标
- [ ] 每季度审查策略逻辑
- [ ] 每半年审查系统架构

---

## 总结

### 核心原则

1. **风险控制第一**: 永远把风控放在首位
2. **简单优于复杂**: 简单的策略更可靠
3. **测试充分**: 回测 + 模拟 + 小资金实盘
4. **持续监控**: 实时监控 + 定期检查
5. **文档完整**: 代码注释 + 使用文档

### 常见错误

1. 过度拟合历史数据
2. 忽略交易成本
3. 没有设置止损
4. 仓位过重
5. 缺乏监控

### 成功要素

1. 稳健的策略逻辑
2. 严格的风险管理
3. 充分的测试验证
4. 持续的优化改进
5. 良好的心态管理

---

**最后更新**: 2026-04-11  
**维护者**: BobQuant Team
