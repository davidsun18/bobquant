# BobQuant 快速启动指南

## 🚀 一键启动

### 1. 启动 Dashboard (Web UI)

```bash
cd /home/openclaw/.openclaw/workspace/dashboard
python3 main.py
```

访问：http://localhost:8500/dashboard

### 2. 启动 Execution Bot (模拟交易)

```bash
cd /home/openclaw/.openclaw/workspace/agents/execution_bot
python3 main.py
```

### 3. 测试数据采集

```bash
cd /home/openclaw/.openclaw/workspace/agents/data-bot/scripts
python3 test_api.py
python3 collect_data.py
```

---

## 📋 系统架构

```
┌─────────────────────────────────────────┐
│     Dashboard (Web UI) - 8500 端口       │
│  - 实时消息流                            │
│  - 持仓监控                              │
│  - 订单记录                              │
│  - 系统日志                              │
└─────────────────────────────────────────┘
              │ WebSocket
┌─────────────▼─────────────┐
│   FastAPI + Message Queue │
│   - REST API              │
│   - WebSocket 推送         │
│   - 消息队列              │
└───────────────────────────┘
              │
    ┌─────────┼─────────┐
    │                   │
┌───▼────┐      ┌──────▼──────┐
│Data Bot│      │Execution Bot│
│腾讯财经 │      │ 模拟交易     │
│Tushare │      │ T+1 规则     │
└────────┘      └─────────────┘
```

---

## 🔧 配置说明

### 数据源配置

编辑 `agents/data-bot/config.json`:

```json
{
  "data_sources": {
    "tencent": {
      "enabled": true,
      "timeout_ms": 1000
    },
    "tushare": {
      "enabled": true,
      "token": "your_token_here"
    }
  }
}
```

### 交易配置

编辑 `framework/trading_rules.py`:

```python
TradingConfig(
    commission_rate=0.0005,  # 万五手续费
    stamp_duty=0.001,        # 印花税
    min_commission=5.0       # 最低佣金
)
```

---

## 📊 API 接口

### REST API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 系统状态 |
| `/api/messages` | GET | 消息历史 |
| `/api/events` | GET | 事件历史 |
| `/api/agents` | GET | Agent 列表 |
| `/api/positions` | GET | 持仓信息 |
| `/api/orders` | GET | 订单记录 |
| `/api/trading-status` | GET | 交易状态 |
| `/api/send-message` | POST | 发送消息 |

### WebSocket

连接：`ws://localhost:8500/ws`

消息格式:
```json
{
  "type": "new_message",
  "data": {
    "from": "boss_bot",
    "to": "execution_bot",
    "type": "trade_order",
    "content": {...}
  }
}
```

---

## 💡 使用示例

### 发送交易指令

```bash
curl -X POST "http://localhost:8500/api/send-message" \
  -H "Content-Type: application/json" \
  -d '{
    "from_agent": "boss_bot",
    "to_agent": "execution_bot",
    "msg_type": "trade_order",
    "content": {
      "action": "buy",
      "stock_code": "600519",
      "stock_name": "贵州茅台",
      "price": 1400.00,
      "quantity": 100
    }
  }'
```

### 查询持仓

```bash
curl "http://localhost:8500/api/positions"
```

### 查看消息流

```bash
curl "http://localhost:8500/api/messages?limit=20"
```

---

## 🛠️ 故障排查

### Dashboard 无法启动

```bash
# 检查端口占用
lsof -i :8500

# 检查依赖
pip3 install fastapi uvicorn websockets
```

### 数据采集失败

```bash
# 测试网络连接
curl -I https://qt.gtimg.cn

# 检查日志
tail -f /home/openclaw/.openclaw/workspace/logs/data_bot.log
```

### WebSocket 断开

- 检查防火墙设置
- 确认 Dashboard 正在运行
- 查看浏览器控制台错误

---

## 📁 目录结构

```
bobquant/
├── framework/              # 核心框架
│   ├── message_queue.py    # 消息队列
│   ├── event_bus.py        # 事件总线
│   ├── agent_base.py       # Agent 基类
│   ├── trading_rules.py    # 交易规则
│   └── data_sources/       # 数据源
├── dashboard/              # Web UI
│   ├── main.py            # FastAPI 后端
│   ├── templates/         # HTML 模板
│   └── static/            # 静态文件
├── agents/                 # Agent 实现
│   ├── data_bot/          # 数据 Bot
│   ├── execution_bot/     # 执行 Bot
│   └── ...
├── data/                   # 数据文件
├── logs/                   # 日志
├── message_queue/          # 消息队列存储
└── config/                 # 配置文件
```

---

## 📝 交易规则

### A 股交易时间
- 集合竞价：09:15 - 09:25
- 早盘：09:30 - 11:30
- 午盘：13:00 - 15:00
- 周末及法定节假日不交易

### 交易限制
- **T+1**: 当日买入，次日才能卖出
- **涨跌停**: 主板±10%, ST±5%, 科创板/创业板±20%
- **最小单位**: 100 股 (1 手)
- **手续费**: 万五 (最低 5 元)
- **印花税**: 卖出收取 0.1%

---

## 🎯 下一步

1. ✅ 启动 Dashboard 查看实时消息流
2. ✅ 测试数据采集 (腾讯财经)
3. ✅ 发送模拟交易指令
4. ⏳ 配置更多 Agent (Quant Research, Compliance 等)
5. ⏳ 接入真实数据源 (Tushare Pro)
6. ⏳ 实现策略回测框架

---

**版本**: 1.0.0  
**更新日期**: 2026-04-18  
**文档**: /home/openclaw/.openclaw/workspace/framework/README.md
