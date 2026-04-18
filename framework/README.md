# BobQuant 量化交易框架
======================

## 📦 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Dashboard (Web UI)                        │
│                    http://localhost:8501                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (FastAPI)                       │
│                    http://localhost:8500                         │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  Message Queue   │ │  Event Bus       │ │  Database        │
│  (Redis/File)    │ │  (WebSocket)     │ │  (SQLite)        │
└──────────────────┘ └──────────────────┘ └──────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Layer                              │
├─────────────┬─────────────┬─────────────┬─────────────────────┤
│   Boss Bot  │  Data Bot   │ Quant Bot   │  Execution Bot      │
│  (Coordinator)│ (Data)    │ (Strategy)  │  (Trading)          │
├─────────────┼─────────────┼─────────────┼─────────────────────┤
│ Compliance  │ Report Bot  │  Dev Bot    │                     │
│  (Risk)     │ (Report)    │ (Dev)       │                     │
└─────────────┴─────────────┴─────────────┴─────────────────────┘
```

## 📁 目录结构

```
bobquant/
├── framework/              # 核心框架
│   ├── __init__.py
│   ├── message_queue.py    # 消息队列
│   ├── event_bus.py        # 事件总线
│   ├── agent_base.py       # Agent 基类
│   └── trading_rules.py    # 交易规则
├── agents/                 # Agent 实现
│   ├── boss_bot/
│   ├── data_bot/
│   ├── quant_research_bot/
│   ├── execution_bot/
│   ├── compliance_bot/
│   ├── report_bot/
│   └── dev_bot/
├── dashboard/              # Web UI
│   ├── main.py            # FastAPI 后端
│   ├── static/            # 静态文件
│   └── templates/         # HTML 模板
├── message_queue/          # 消息队列数据
├── data/                   # 数据文件
├── logs/                   # 日志
└── config/                 # 配置文件
```

## 🚀 快速启动

### 1. 启动消息队列和 API

```bash
cd /home/openclaw/.openclaw/workspace
python3 dashboard/main.py
```

### 2. 访问 Dashboard

浏览器打开：http://localhost:8501

### 3. 启动 Agent

```bash
# 启动 Execution Bot (模拟交易)
python3 agents/execution_bot/main.py

# 启动 Data Bot (数据采集)
python3 agents/data_bot/scripts/collect_data.py
```

## 📊 功能特性

### 消息队列
- ✅ 基于文件系统 (无需 Redis)
- ✅ 支持发布/订阅模式
- ✅ 消息持久化
- ✅ 实时 WebSocket 推送

### 模拟交易
- ✅ 万五手续费 (0.05%)
- ✅ T+1 交易规则
- ✅ A 股交易时间控制
- ✅ 法定节假日识别
- ✅ 实时持仓管理

### Dashboard
- ✅ 实时消息流
- ✅ 持仓监控
- ✅ 交易记录
- ✅ 绩效图表
- ✅ Agent 状态

## 📋 交易规则

### A 股交易时间
- 早盘：09:30 - 11:30
- 午盘：13:00 - 15:00
- 集合竞价：09:15 - 09:25

### 交易限制
- T+1: 当日买入，次日才能卖出
- 涨跌停：±10% (ST ±5%)
- 最小单位：100 股 (1 手)
- 手续费：万分之五

### 节假日
- 周末不交易
- 国家法定节假日不交易
- 调休工作日交易

## 🔧 配置

### 数据源配置
```json
{
  "data_sources": {
    "tencent": {"enabled": true, "type": "realtime"},
    "tushare": {"enabled": true, "type": "historical", "token": "your_token"}
  }
}
```

### 交易配置
```json
{
  "trading": {
    "commission_rate": 0.0005,
    "stamp_duty": 0.001,
    "transfer_fee": 0.00002,
    "slippage": 0.001
  }
}
```

## 📝 消息格式

### Agent 通信消息
```json
{
  "id": "msg_001",
  "timestamp": "2026-04-18T09:30:00+08:00",
  "from": "boss_bot",
  "to": "execution_bot",
  "type": "trade_order",
  "content": {
    "action": "buy",
    "stock_code": "600519",
    "quantity": 100,
    "price": 1400.00
  }
}
```

## 🛠️ 开发指南

### 添加新 Agent
1. 在 `agents/` 目录创建 Agent 文件夹
2. 继承 `framework/agent_base.py`
3. 实现 `on_message()` 和 `run()` 方法
4. 在 Dashboard 注册

### 添加新数据源
1. 在 `framework/data_sources/` 创建适配器
2. 实现 `fetch()` 和 `validate()` 方法
3. 在配置中启用

---

**版本**: 1.0.0  
**创建日期**: 2026-04-18  
**维护者**: BobQuant Team
