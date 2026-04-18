#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant Dashboard - FastAPI 后端
提供 REST API 和 WebSocket 实时推送
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 添加框架路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.message_queue import MessageQueue, get_queue
from framework.event_bus import EventBus, get_event_bus
from framework.trading_rules import get_trading_rules

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Dashboard")

# 创建 FastAPI 应用
app = FastAPI(
    title="BobQuant Dashboard",
    description="量化交易系统监控面板",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局实例
queue = get_queue()
event_bus = get_event_bus()
trading_rules = get_trading_rules()

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        event_bus.register_websocket(websocket)
        logger.info(f"WebSocket 连接，当前连接数：{len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        event_bus.unregister_websocket(websocket)
        logger.info(f"WebSocket 断开，当前连接数：{len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"广播失败：{e}")
    
    async def send_personal(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送失败：{e}")

manager = ConnectionManager()


# ============== API 路由 ==============

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "BobQuant Dashboard",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    return {
        "timestamp": datetime.now().isoformat(),
        "message_queue": queue.get_stats(),
        "event_bus": event_bus.get_stats(),
        "trading_rules": trading_rules.get_status()
    }


@app.get("/api/messages")
async def get_messages(agent: str = None, limit: int = 50):
    """获取消息历史"""
    # 从归档目录读取历史消息
    archive_dir = Path("/home/openclaw/.openclaw/workspace/message_queue/archive")
    messages = []
    
    # 读取最近的归档文件
    today = datetime.now().strftime('%Y-%m-%d')
    today_dir = archive_dir / today
    
    if today_dir.exists():
        for filepath in sorted(today_dir.glob("*.json"), reverse=True)[:limit]:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    msg = json.load(f)
                messages.append(msg)
            except Exception as e:
                logger.error(f"读取消息失败：{e}")
    
    # 也读取待处理和已投递的消息
    for dir_name in ['pending', 'delivered']:
        dir_path = queue.queue_dir / dir_name
        if dir_path.exists():
            for filepath in sorted(dir_path.glob("*.json"), reverse=True)[:limit//3]:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        msg = json.load(f)
                    messages.append(msg)
                except Exception as e:
                    pass
    
    # 按时间戳排序
    messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    if agent:
        messages = [m for m in messages if m.get('to_agent') == agent or m.get('from_agent') == agent]
    
    return {"messages": messages[:limit], "total": len(messages)}


@app.get("/api/events")
async def get_events(event_type: str = None, limit: int = 100):
    """获取事件历史"""
    events = event_bus.get_history(event_type, limit)
    return {
        "events": [e.to_dict() for e in events],
        "total": len(events)
    }


@app.get("/api/agents")
async def get_agents():
    """获取 Agent 列表"""
    # 从订阅者获取已知 Agent
    agents = list(queue.subscribers.keys())
    
    # 添加预定义 Agent
    predefined = [
        "boss_bot", "data_bot", "quant_research_bot",
        "execution_bot", "compliance_bot", "report_bot", "dev_bot"
    ]
    
    for agent in predefined:
        if agent not in agents:
            agents.append(agent)
    
    return {
        "agents": agents,
        "total": len(agents)
    }


@app.get("/api/positions")
async def get_positions():
    """获取持仓信息 (模拟)"""
    # 这里应该从数据库或 Execution Bot 获取真实持仓
    # 暂时返回模拟数据
    return {
        "positions": [
            {
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "quantity": 100,
                "available": 0,  # T+1 锁定
                "cost_price": 1450.00,
                "current_price": 1407.24,
                "market_value": 140724.00,
                "profit_loss": -4276.00,
                "profit_loss_pct": -2.95
            }
        ],
        "total_value": 140724.00,
        "total_profit_loss": -4276.00
    }


@app.get("/api/orders")
async def get_orders(status: str = None, limit: int = 50):
    """获取订单记录 (模拟)"""
    # 模拟订单数据
    orders = [
        {
            "order_id": "ORD20260418001",
            "stock_code": "600519",
            "action": "buy",
            "price": 1450.00,
            "quantity": 100,
            "status": "filled",
            "create_time": "2026-04-17T10:30:00",
            "fill_time": "2026-04-17T10:30:05"
        },
        {
            "order_id": "ORD20260418002",
            "stock_code": "000858",
            "action": "buy",
            "price": 103.00,
            "quantity": 200,
            "status": "pending",
            "create_time": "2026-04-18T09:35:00",
            "fill_time": None
        }
    ]
    
    if status:
        orders = [o for o in orders if o.get('status') == status]
    
    return {"orders": orders[:limit], "total": len(orders)}


@app.get("/api/trading-status")
async def get_trading_status():
    """获取交易状态"""
    can_trade, reason = trading_rules.time_controller.can_trade()
    return {
        "can_trade": can_trade,
        "reason": reason,
        "is_trading_day": trading_rules.time_controller.is_trading_day(),
        "trading_periods": trading_rules.time_controller.get_trading_periods(),
        "config": {
            "commission_rate": trading_rules.config.commission_rate,
            "stamp_duty": trading_rules.config.stamp_duty,
            "t1_enabled": True
        }
    }


@app.post("/api/send-message")
async def send_message(from_agent: str, to_agent: str, 
                       msg_type: str, content: Dict[str, Any]):
    """发送消息"""
    msg_id = queue.send(from_agent, to_agent, msg_type, content)
    
    # 广播新消息
    await manager.broadcast({
        "type": "new_message",
        "data": {
            "id": msg_id,
            "from": from_agent,
            "to": to_agent,
            "type": msg_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
    })
    
    return {"success": True, "message_id": msg_id}


# ============== WebSocket ==============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接"""
    await manager.connect(websocket)
    
    try:
        while True:
            # 接收客户端消息 (心跳等)
            data = await websocket.receive_text()
            
            # 可以处理客户端命令
            try:
                msg = json.loads(data)
                if msg.get('type') == 'ping':
                    await manager.send_personal(
                        {"type": "pong", "timestamp": datetime.now().isoformat()},
                        websocket
                    )
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 错误：{e}")
        manager.disconnect(websocket)


# ============== 静态文件 ==============

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Dashboard 页面"""
    html_file = Path(__file__).parent / "templates" / "index.html"
    
    if html_file.exists():
        with open(html_file, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>Dashboard 模板不存在</h1>", status_code=404)


# ============== 主程序 ==============

def main():
    """启动 Dashboard"""
    logger.info("启动 BobQuant Dashboard...")
    logger.info("API: http://localhost:8500")
    logger.info("Dashboard: http://localhost:8500/dashboard")
    logger.info("WebSocket: ws://localhost:8500/ws")
    
    # 启动消息队列后台任务
    queue.start_worker()
    
    # 启动 FastAPI
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8500,
        log_level="info"
    )


if __name__ == "__main__":
    main()
