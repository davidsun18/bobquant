# BobQuant 混合架构集成指南

**版本**: v1.0  
**创建日期**: 2026-04-10  
**状态**: 原型阶段

---

## 📋 概述

本文档介绍如何将事件驱动架构集成到现有的 bobquant 轮询系统中，实现混合架构。

### 什么是混合架构？

混合架构 = 保留现有轮询主循环 + 引入事件机制处理特定场景

```
┌─────────────────────────────────────────────────────────────┐
│                    轮询主循环 (保留)                         │
│  while True:                                                │
│    if trading_hours:                                        │
│      run_check()  # 常规交易检查                            │
│    sleep(10s)                                               │
└─────────────────────────────────────────────────────────────┘
                           +
┌─────────────────────────────────────────────────────────────┐
│                  事件引擎 (新增)                             │
│  EventEngine.start()                                        │
│  - 处理紧急风控事件                                         │
│  - 异步发送通知                                             │
│  - 记录日志                                                 │
└─────────────────────────────────────────────────────────────┘
```

### 优势

- ✅ **低风险**: 保留现有稳定逻辑
- ✅ **即时响应**: 紧急事件不等待轮询周期
- ✅ **渐进式**: 可逐步增加事件驱动组件
- ✅ **易回滚**: 问题时可快速回到纯轮询模式

---

## 🚀 快速开始

### 1. 导入事件模块

```python
# 在 main.py 顶部添加
from bobquant.event import (
    EventEngine,
    EVENT_RISK_TRIGGERED,
    EVENT_NOTIFY,
    trigger_risk_event,
    trigger_notify_event,
)
from bobquant.event.handlers import RiskHandler, NotifyHandler
```

### 2. 初始化事件引擎

```python
def main_loop():
    s = get_settings()
    
    # ============ 初始化事件引擎 ============
    engine = EventEngine(interval=1)  # 1 秒定时器
    
    # 创建处理器
    data = get_provider(s.get('data.primary', 'tencent'))
    account = Account(s.positions_file, s.initial_capital).load()
    executor = Executor(...)
    
    risk_handler = RiskHandler(executor, account, data)
    notify_handler = NotifyHandler(s.get('notify.feishu.user_id', ''))
    
    # 注册处理器
    engine.register(EVENT_RISK_TRIGGERED, risk_handler.handle)
    engine.register(EVENT_NOTIFY, notify_handler.handle)
    
    # 启动引擎
    engine.start()
    _log("✅ 事件引擎已启动")
    
    # ============ 原有轮询逻辑 ============
    while True:
        if s.is_trading_hours():
            try:
                run_check(engine)  # 传入 engine 支持事件触发
                portfolio_summary()
            except Exception as e:
                _log(f"❌ 错误：{e}")
                # 触发错误通知事件
                trigger_notify_event(engine, "BobQuant 错误", f"交易检查出错：{e}")
        else:
            _log("⏸️ 非交易时段，等待...")
        
        time.sleep(s.check_interval)
```

### 3. 在 run_check 中触发事件

```python
def run_check(event_engine=None):
    """执行一次三阶段信号检查"""
    s = get_settings()
    
    # ... 原有初始化代码 ...
    
    # ============ Phase 1: 网格做 T ============
    for code, pos in list(account.positions.items()):
        # ... 原有做 T 逻辑 ...
        
        # 新增：如果触发止盈/止损，发送事件
        result = risk.check(code, pos, quote['current'])
        if result['action'] in ('stop_loss', 'take_profit'):
            # 触发风控事件 (立即执行，不等待)
            if event_engine and event_engine.is_active():
                trigger_risk_event(
                    event_engine,
                    code=code,
                    action=result['action'],
                    reason=result['reason'],
                    shares=result['shares']
                )
            else:
                # 降级：使用原有同步执行
                t = executor.sell(...)
    
    # ... 后续逻辑 ...
```

---

## 📦 事件类型说明

### EVENT_RISK_TRIGGERED (风控事件)

**用途**: 紧急风控操作 (止损、止盈、移动止损)

**数据结构**:
```python
{
    'code': 'SH.600000',      # 股票代码
    'action': 'stop_loss',     # 动作：stop_loss/take_profit/trailing_stop
    'reason': '跌幅超过 5%',    # 触发原因
    'shares': 100,             # 股数
    'timestamp': datetime.now()  # 时间戳 (自动设置)
}
```

**触发场景**:
- 盘中紧急止损
- 止盈触发
- 移动止损触发

**处理器**: `RiskHandler`

---

### EVENT_NOTIFY (通知事件)

**用途**: 异步发送飞书通知

**数据结构**:
```python
{
    'title': 'BobQuant 通知',   # 通知标题
    'message': '内容...',       # 通知内容
    'timestamp': datetime.now()  # 时间戳 (自动设置)
}
```

**触发场景**:
- 交易执行通知
- 错误告警
- 系统状态通知

**处理器**: `NotifyHandler`

---

### EVENT_SIGNAL_GENERATED (信号事件)

**用途**: 记录交易信号生成

**数据结构**:
```python
{
    'code': 'SH.600000',      # 股票代码
    'name': '浦发银行',        # 股票名称
    'signal': 'buy',           # 信号：buy/sell
    'reason': 'MACD 金叉',      # 信号原因
    'strength': 'strong',      # 强度：normal/strong/weak
    'timestamp': datetime.now()  # 时间戳 (自动设置)
}
```

**触发场景**:
- 策略生成买入信号
- 策略生成卖出信号
- ML 预测信号

**处理器**: `SignalHandler`

---

## 🔧 处理器实现

### RiskHandler (风控处理器)

```python
from bobquant.event.handlers import RiskHandler

# 创建处理器
risk_handler = RiskHandler(
    executor=executor,      # 交易执行器
    account=account,        # 账户对象
    data_provider=data      # 数据提供者 (用于获取实时价格)
)

# 注册到事件引擎
engine.register(EVENT_RISK_TRIGGERED, risk_handler.handle)
```

**功能**:
- ✅ 立即执行风控卖出
- ✅ 获取实时价格
- ✅ 更新账户状态
- ✅ 记录执行日志

---

### NotifyHandler (通知处理器)

```python
from bobquant.event.handlers import NotifyHandler

# 创建处理器
notify_handler = NotifyHandler(
    user_id=s.get('notify.feishu.user_id', '')  # 飞书用户 ID
)

# 注册到事件引擎
engine.register(EVENT_NOTIFY, notify_handler.handle)
```

**功能**:
- ✅ 异步发送飞书通知
- ✅ 不阻塞主循环
- ✅ 支持批量通知

---

### SignalHandler (信号处理器)

```python
from bobquant.event.handlers import SignalHandler

# 创建处理器
signal_handler = SignalHandler(
    strategy_engine=strategy_engine,  # 策略引擎 (可选)
    executor=executor,                 # 交易执行器 (可选)
    account=account,                   # 账户对象 (可选)
    auto_execute=False                 # 是否自动执行 (默认 False)
)

# 注册到事件引擎
engine.register(EVENT_SIGNAL_GENERATED, signal_handler.handle)
```

**功能**:
- ✅ 记录信号到策略引擎
- ✅ 可选自动执行信号
- ✅ 信号日志记录

---

## 📊 集成示例

### 完整示例代码

```python
# -*- coding: utf-8 -*-
"""
BobQuant 混合架构示例

展示如何将事件引擎集成到现有轮询系统
"""
import time
from datetime import datetime

from bobquant.event import (
    EventEngine,
    EVENT_RISK_TRIGGERED,
    EVENT_NOTIFY,
    trigger_risk_event,
    trigger_notify_event,
)
from bobquant.event.handlers import RiskHandler, NotifyHandler

from config import get_settings
from core.account import Account
from core.executor import Executor
from data.provider import get_provider
from strategy.engine import GridTStrategy, RiskManager


def _log(message):
    """日志函数"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")


def main():
    """主函数"""
    s = get_settings()
    
    # ============ 初始化组件 ============
    _log("初始化组件...")
    data = get_provider(s.get('data.primary', 'tencent'))
    account = Account(s.positions_file, s.initial_capital).load()
    executor = Executor(account, s.commission_rate, s.trade_log_file, _log, None)
    grid_t = GridTStrategy(s.get('day_trading', {}))
    risk = RiskManager(s.get('day_trading', {}))
    
    # ============ 初始化事件引擎 ============
    _log("初始化事件引擎...")
    engine = EventEngine(interval=1)
    
    # 创建处理器
    risk_handler = RiskHandler(executor, account, data)
    notify_handler = NotifyHandler(s.get('notify.feishu.user_id', ''))
    
    # 注册处理器
    engine.register(EVENT_RISK_TRIGGERED, risk_handler.handle)
    engine.register(EVENT_NOTIFY, notify_handler.handle)
    
    # 启动引擎
    engine.start()
    _log("✅ 事件引擎已启动")
    _log(f"   统计：{engine.get_stats()}")
    
    # ============ 主循环 ============
    _log("进入主循环...")
    
    try:
        while True:
            if s.is_trading_hours():
                try:
                    # 执行交易检查 (支持事件触发)
                    run_check_with_events(engine, data, account, executor, grid_t, risk, s)
                    
                    # 定期输出统计
                    stats = engine.get_stats()
                    if stats['event_count'] % 10 == 0:
                        _log(f"📊 事件引擎统计：{stats}")
                    
                except Exception as e:
                    _log(f"❌ 错误：{e}")
                    # 触发错误通知
                    trigger_notify_event(engine, "BobQuant 错误", f"交易检查出错：{e}")
            else:
                _log("⏸️ 非交易时段，等待...")
            
            time.sleep(s.check_interval)
    
    except KeyboardInterrupt:
        _log("\n⏹️ 收到停止信号...")
    finally:
        # 停止事件引擎
        engine.stop()
        _log("✅ 事件引擎已停止")
        _log(f"   最终统计：{engine.get_stats()}")


def run_check_with_events(engine, data, account, executor, grid_t, risk, s):
    """
    执行交易检查 (支持事件触发)
    
    与原有 run_check 的区别:
    - 支持通过事件触发紧急风控
    - 支持异步通知
    """
    _log("📊 检查交易信号...")
    
    # 获取所有持仓股价格
    codes = list(account.positions.keys())
    quotes = data.get_quotes(codes)
    
    # ============ 风控检查 ============
    for code, pos in list(account.positions.items()):
        quote = quotes.get(code)
        if not quote or quote['current'] <= 0:
            continue
        
        result = risk.check(code, pos, quote['current'])
        if result['action']:
            # 触发风控事件 (立即执行)
            trigger_risk_event(
                engine,
                code=code,
                action=result['action'],
                reason=result['reason'],
                shares=result['shares']
            )
            _log(f"  ⚡ 触发风控事件：{code} {result['action']}")
    
    # ============ 做 T 检查 ============
    # (保持原有逻辑，不通过事件)
    for code, pos in list(account.positions.items()):
        # ... 原有做 T 逻辑 ...
        pass
    
    # ============ 策略信号 ============
    # (保持原有逻辑，不通过事件)
    for stock in s.stock_pool:
        # ... 原有策略逻辑 ...
        pass
    
    _log(f"  ✅ 检查完成")


if __name__ == '__main__':
    main()
```

---

## 🎯 最佳实践

### 1. 何时使用事件？

**推荐使用事件**:
- ✅ 紧急风控 (止损、止盈)
- ✅ 异步通知 (不阻塞主循环)
- ✅ 日志记录
- ✅ 跨模块通信

**不推荐使用事件**:
- ❌ 常规交易检查 (保持轮询)
- ❌ 高频数据刷新 (轮询更高效)
- ❌ 简单同步逻辑 (增加复杂度)

---

### 2. 事件处理器设计

**原则**:
- ✅ 处理器应该快速执行 (避免阻塞事件队列)
- ✅ 异常处理要完善 (避免影响其他处理器)
- ✅ 记录详细日志 (便于调试)
- ✅ 避免循环依赖 (处理器不应触发相同事件)

**示例**:
```python
def handle(self, event: Event) -> None:
    try:
        # 快速处理
        result = self._process(event.data)
        
        # 记录日志
        logging.info(f"处理成功：{result}")
        
    except Exception as e:
        # 完善异常处理
        logging.error(f"处理失败：{e}")
        # 不要重新触发相同事件，避免死循环
```

---

### 3. 调试技巧

**启用详细日志**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

engine = EventEngine(interval=1, log_enabled=True)
```

**查看引擎统计**:
```python
stats = engine.get_stats()
print(f"事件数：{stats['event_count']}")
print(f"错误数：{stats['error_count']}")
print(f"队列大小：{stats['queue_size']}")
```

**测试事件**:
```python
# 手动触发测试事件
from bobquant.event import create_event

engine.put(create_event(EVENT_NOTIFY, {
    'title': '测试',
    'message': '这是一条测试通知'
}))
```

---

## ⚠️ 注意事项

### 1. 线程安全

事件引擎使用线程安全队列，但处理器中访问共享资源时仍需注意:

```python
# ❌ 错误：直接访问共享资源
def handle(self, event):
    account.cash -= 100  # 可能有竞态条件

# ✅ 正确：使用锁保护
def handle(self, event):
    with account.lock:
        account.cash -= 100
```

---

### 2. 异常处理

处理器中的异常不应影响事件引擎:

```python
# ✅ 事件引擎已内置异常处理
def _process(self, event: Event) -> None:
    for handler in handlers:
        try:
            handler(event)
        except Exception as e:
            self._error_count += 1
            self._log_error(f"处理器执行失败：{e}")
```

---

### 3. 资源清理

确保停止引擎时清理资源:

```python
try:
    engine.start()
    # ... 运行 ...
finally:
    engine.stop()  # 确保停止
```

---

## 📈 性能监控

### 监控指标

| 指标 | 说明 | 正常范围 |
|------|------|----------|
| event_count | 处理事件总数 | 持续增长 |
| error_count | 错误数 | < 1% of event_count |
| queue_size | 队列积压 | < 100 |
| handler_count | 注册处理器数 | 根据需求 |

### 告警阈值

```python
stats = engine.get_stats()

if stats['error_count'] > stats['event_count'] * 0.01:
    _log("⚠️ 错误率超过 1%")

if stats['queue_size'] > 100:
    _log("⚠️ 事件队列积压")
```

---

## 🔮 未来演进

### 阶段 1: 基础集成 (当前)

- ✅ 事件引擎核心
- ✅ 风控/通知处理器
- ✅ 混合架构示例

### 阶段 2: 增强功能

- [ ] 更多事件类型 (订单、成交等)
- [ ] 事件持久化 (记录到数据库)
- [ ] 事件回放 (用于回测)

### 阶段 3: 完全事件驱动

- [ ] 轮询→事件迁移
- [ ] 实时数据推送
- [ ] 分布式事件处理

---

## 📚 参考资料

- [vn.py 事件引擎源码](https://github.com/vnpy/vnpy/blob/master/vnpy/event/engine.py)
- [架构分析报告](./vnpy_architecture_analysis.md)
- [EventEngine API 文档](../event/engine.py)

---

_文档版本：v1.0_  
_最后更新：2026-04-10_
