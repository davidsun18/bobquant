#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 通信演示脚本
展示 Boss Bot 和 Execution Bot 之间的消息交互
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime

# 添加框架路径
sys.path.insert(0, str(Path(__file__).parent))

from framework.message_queue import MessageQueue, Message, get_queue
from framework.event_bus import EventBus, get_event_bus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Demo")


def demo_message_queue():
    """演示消息队列"""
    print("\n" + "=" * 60)
    print("消息队列演示")
    print("=" * 60)
    
    queue = get_queue()
    
    # 模拟 Boss Bot 发送交易指令
    print("\n📤 Boss Bot 发送交易指令...")
    msg_id = queue.send(
        from_agent="boss_bot",
        to_agent="execution_bot",
        msg_type="trade_order",
        content={
            "action": "buy",
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "price": 1400.00,
            "quantity": 100,
            "reason": "策略信号：突破 20 日均线"
        },
        priority=8
    )
    print(f"   消息 ID: {msg_id}")
    
    # 模拟 Execution Bot 接收并处理
    print("\n📥 Execution Bot 接收消息...")
    messages = queue.poll("execution_bot")
    
    for msg in messages:
        print(f"   收到：{msg.msg_type} from {msg.from_agent}")
        print(f"   内容：{msg.content}")
        
        # 模拟处理
        print("\n   ⚡ 执行交易中...")
        time.sleep(0.5)
        
        # 发送成交回报
        queue.send(
            from_agent="execution_bot",
            to_agent="boss_bot",
            msg_type="order_filled",
            content={
                "order_id": "ORD20260418001",
                "stock_code": msg.content['stock_code'],
                "action": msg.content['action'],
                "price": msg.content['price'],
                "quantity": msg.content['quantity'],
                "status": "filled",
                "fill_time": datetime.now().isoformat(),
                "commission": 7.00  # 万五手续费
            }
        )
        
        # 确认消息
        queue.ack(msg.id, "execution_bot")
    
    # Boss Bot 接收成交回报
    print("\n📥 Boss Bot 接收成交回报...")
    messages = queue.poll("boss_bot")
    for msg in messages:
        print(f"   收到：{msg.msg_type}")
        print(f"   订单号：{msg.content.get('order_id')}")
        print(f"   状态：{msg.content.get('status')}")
        queue.ack(msg.id, "boss_bot")
    
    # 显示队列统计
    print("\n📊 队列统计:")
    stats = queue.get_stats()
    print(f"   待处理：{stats['pending']}")
    print(f"   已投递：{stats['delivered']}")
    print(f"   失败：{stats['failed']}")


def demo_event_bus():
    """演示事件总线"""
    print("\n" + "=" * 60)
    print("事件总线演示")
    print("=" * 60)
    
    event_bus = get_event_bus()
    
    # 订阅事件
    def on_trade_event(event):
        print(f"\n   📢 收到事件：{event.event_type}")
        print(f"      来源：{event.source}")
        print(f"      数据：{event.data}")
    
    event_bus.subscribe("trade_executed", on_trade_event)
    event_bus.subscribe("*", lambda e: None)  # 通配符订阅
    
    # 发布事件
    print("\n📤 发布交易执行事件...")
    event_id = event_bus.publish(
        event_type="trade_executed",
        source="execution_bot",
        data={
            "order_id": "ORD20260418001",
            "stock_code": "600519",
            "action": "buy",
            "price": 1400.00,
            "quantity": 100,
            "amount": 140000.00,
            "commission": 70.00
        }
    )
    print(f"   事件 ID: {event_id}")
    
    # 发布系统状态事件
    print("\n📤 发布系统状态事件...")
    event_bus.publish(
        event_type="system_status",
        source="dashboard",
        data={
            "uptime": "1h 23m",
            "agents_online": 7,
            "messages_processed": 156
        }
    )
    
    # 显示事件历史
    print("\n📊 事件历史:")
    events = event_bus.get_history(limit=5)
    for event in events:
        print(f"   - {event.event_type} @ {event.source}")
    
    # 显示统计
    print("\n📊 事件总线统计:")
    stats = event_bus.get_stats()
    print(f"   订阅者：{stats['subscribers']}")
    print(f"   WebSocket 客户端：{stats['websocket_clients']}")
    print(f"   历史事件：{stats['history_size']}")


def demo_trading_rules():
    """演示交易规则"""
    print("\n" + "=" * 60)
    print("交易规则演示")
    print("=" * 60)
    
    from framework.trading_rules import TradingRules, TradingConfig
    
    rules = TradingRules(TradingConfig(
        commission_rate=0.0005,
        stamp_duty=0.001
    ))
    
    # 检查交易时间
    print("\n🕐 交易时间检查:")
    can_trade, reason = rules.time_controller.can_trade()
    print(f"   可否交易：{can_trade}")
    print(f"   原因：{reason}")
    
    # 计算交易成本
    print("\n💰 交易成本计算:")
    
    print("\n   买入 100 股 @ ¥1400.00:")
    buy_cost = rules.calculate_cost(1400.00, 100, is_buy=True)
    for key, value in buy_cost.items():
        print(f"      {key}: ¥{value:.2f}")
    
    print("\n   卖出 100 股 @ ¥1450.00:")
    sell_cost = rules.calculate_cost(1450.00, 100, is_buy=False)
    for key, value in sell_cost.items():
        print(f"      {key}: ¥{value:.2f}")
    
    # T+1 规则演示
    print("\n📅 T+1 规则演示:")
    rules.record_buy("600519", 100)
    available = rules.get_available_quantity("600519", 100)
    print(f"   买入 100 股贵州茅台")
    print(f"   总持仓：100 股")
    print(f"   可卖数量：{available} 股 (T+1 锁定)")
    
    # 验证订单
    print("\n✅ 订单验证:")
    valid, error = rules.validate_order(
        stock_code="600519",
        action="buy",
        price=1400.00,
        quantity=100
    )
    print(f"   验证结果：{'通过' if valid else f'失败 - {error}'}")


def main():
    """主函数"""
    print("\n" + "🚀" * 30)
    print("BobQuant Agent 通信演示")
    print("🚀" * 30)
    
    try:
        # 演示消息队列
        demo_message_queue()
        
        # 演示事件总线
        demo_event_bus()
        
        # 演示交易规则
        demo_trading_rules()
        
        print("\n" + "=" * 60)
        print("演示完成!")
        print("=" * 60)
        print("\n下一步:")
        print("  1. 启动 Dashboard: cd dashboard && python3 main.py")
        print("  2. 访问：http://localhost:8500/dashboard")
        print("  3. 启动 Execution Bot: cd agents/execution_bot && python3 main.py")
        print("\n")
        
    except Exception as e:
        logger.error(f"演示失败：{e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
