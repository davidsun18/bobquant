#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Execution Bot - 交易执行机器人
负责模拟交易执行，遵守 A 股交易规则 (T+1, 涨跌停，交易时间等)
"""

import sys
import logging
import json
from datetime import datetime, time
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加框架路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.agent_base import AgentBase, Message
from framework.trading_rules import TradingRules, TradingConfig, get_trading_rules
from framework.message_queue import get_queue

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/openclaw/.openclaw/workspace/logs/execution_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ExecutionBot")


class Position:
    """持仓类"""
    
    def __init__(self, stock_code: str, stock_name: str = ""):
        self.stock_code = stock_code
        self.stock_name = stock_name
        self.quantity = 0  # 总持仓
        self.available = 0  # 可用持仓 (T+1 后可卖)
        self.cost_price = 0.0  # 成本价
        self.frozen = 0  # 冻结数量 (挂单中)
        
        # 买入记录 (用于 T+1)
        self.buy_records: List[Dict] = []
    
    def add_buy(self, price: float, quantity: int, date: str = None):
        """记录买入"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 计算新的成本价 (加权平均)
        total_cost = self.cost_price * self.quantity + price * quantity
        self.quantity += quantity
        self.cost_price = total_cost / self.quantity if self.quantity > 0 else 0
        
        # 记录买入 (T+1 锁定)
        self.buy_records.append({
            'date': date,
            'price': price,
            'quantity': quantity
        })
        
        logger.info(f"买入记录：{self.stock_code} {quantity}股 @ {price:.2f} ({date})")
    
    def update_available(self):
        """更新可用数量 (处理 T+1)"""
        from datetime import timedelta
        
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 计算可用数量 (昨天及之前买入的可以卖)
        self.available = 0
        for record in self.buy_records:
            if record['date'] < today:  # 今天买入的不可卖
                self.available += record['quantity']
        
        # 清理过期记录 (保留最近 3 天)
        cutoff = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        self.buy_records = [r for r in self.buy_records if r['date'] >= cutoff]
        
        logger.debug(f"{self.stock_code} 可用数量更新：{self.available}/{self.quantity}")
    
    def can_sell(self, quantity: int) -> bool:
        """检查是否可卖"""
        self.update_available()
        return quantity <= (self.available - self.frozen)
    
    def to_dict(self) -> Dict:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'quantity': self.quantity,
            'available': self.available,
            'cost_price': round(self.cost_price, 2),
            'frozen': self.frozen,
            'buy_records': self.buy_records
        }


class OrderBook:
    """订单簿"""
    
    def __init__(self):
        self.orders: Dict[str, Dict] = {}
        self.order_counter = 0
    
    def create_order(self, stock_code: str, action: str, price: float, 
                     quantity: int) -> str:
        """创建订单"""
        self.order_counter += 1
        order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{self.order_counter:03d}"
        
        self.orders[order_id] = {
            'order_id': order_id,
            'stock_code': stock_code,
            'action': action,
            'price': price,
            'quantity': quantity,
            'filled_quantity': 0,
            'status': 'pending',  # pending, partial, filled, cancelled, rejected
            'create_time': datetime.now().isoformat(),
            'fill_time': None,
            'reject_reason': None
        }
        
        return order_id
    
    def update_order(self, order_id: str, **kwargs):
        """更新订单"""
        if order_id in self.orders:
            self.orders[order_id].update(kwargs)
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """获取订单"""
        return self.orders.get(order_id)
    
    def get_recent_orders(self, limit: int = 50) -> List[Dict]:
        """获取最近订单"""
        orders = sorted(
            self.orders.values(),
            key=lambda x: x['create_time'],
            reverse=True
        )
        return orders[:limit]


class ExecutionBot(AgentBase):
    """交易执行机器人"""
    
    def __init__(self):
        super().__init__("execution_bot")
        
        self.rules = get_trading_rules()
        self.positions: Dict[str, Position] = {}
        self.order_book = OrderBook()
        self.cash = 1000000.0  # 初始资金 100 万
        self.starting_cash = 1000000.0
        
        logger.info(f"Execution Bot 初始化完成，初始资金：¥{self.cash:,.2f}")
    
    def on_start(self):
        """启动时调用"""
        logger.info("Execution Bot 启动")
        self.publish_event("agent_status", {
            "agent": "execution_bot",
            "status": "running",
            "cash": self.cash
        })
    
    def on_message(self, message: Message):
        """处理收到的消息"""
        logger.info(f"收到消息：{message.msg_type} from {message.from_agent}")
        
        try:
            if message.msg_type == "trade_order":
                self.handle_trade_order(message)
            elif message.msg_type == "query_position":
                self.handle_query_position(message)
            elif message.msg_type == "query_order":
                self.handle_query_order(message)
            elif message.msg_type == "cancel_order":
                self.handle_cancel_order(message)
            else:
                logger.warning(f"未知消息类型：{message.msg_type}")
        except Exception as e:
            logger.error(f"处理消息失败：{e}")
            self.queue.fail(message.id, "execution_bot", str(e), retry=False)
    
    def handle_trade_order(self, message: Message):
        """处理交易订单"""
        content = message.content
        stock_code = content.get('stock_code')
        action = content.get('action', 'buy').lower()
        price = float(content.get('price', 0))
        quantity = int(content.get('quantity', 0))
        stock_name = content.get('stock_name', '')
        
        logger.info(f"交易请求：{action.upper()} {stock_code} {quantity}股 @ ¥{price:.2f}")
        
        # 验证订单
        valid, error = self.validate_order(stock_code, action, price, quantity)
        if not valid:
            logger.warning(f"订单验证失败：{error}")
            self.send_message(
                message.from_agent,
                "order_rejected",
                {
                    "reason": error,
                    "stock_code": stock_code,
                    "action": action,
                    "quantity": quantity
                }
            )
            return
        
        # 创建订单
        order_id = self.order_book.create_order(stock_code, action, price, quantity)
        
        # 模拟撮合 (假设立即成交)
        self.execute_order(order_id, stock_code, stock_name, action, price, quantity)
        
        # 发送成交回报
        order = self.order_book.get_order(order_id)
        self.send_message(
            message.from_agent,
            "order_filled",
            order
        )
        
        # 发布事件
        self.publish_event("trade_executed", {
            "order_id": order_id,
            "stock_code": stock_code,
            "action": action,
            "price": price,
            "quantity": quantity,
            "amount": price * quantity
        })
    
    def validate_order(self, stock_code: str, action: str, 
                       price: float, quantity: int) -> tuple:
        """验证订单"""
        # 检查交易时间
        can_trade, reason = self.rules.time_controller.can_trade()
        if not can_trade:
            return False, f"禁止交易：{reason}"
        
        # 检查数量
        if quantity < 100 or quantity % 100 != 0:
            return False, "数量必须是 100 的整数倍"
        
        # 检查价格
        if price <= 0:
            return False, "价格必须大于 0"
        
        # 买入时检查资金
        if action == "buy":
            cost = price * quantity
            fees = self.rules.calculate_cost(price, quantity, is_buy=True)
            total = cost + fees['total_cost']
            if total > self.cash:
                return False, f"资金不足 (需要¥{total:,.2f}, 可用¥{self.cash:,.2f})"
        
        # 卖出时检查持仓
        elif action == "sell":
            if stock_code not in self.positions:
                return False, "无持仓"
            
            position = self.positions[stock_code]
            if not position.can_sell(quantity):
                return False, f"可卖数量不足 (可用：{position.available})"
        
        return True, "验证通过"
    
    def execute_order(self, order_id: str, stock_code: str, stock_name: str,
                      action: str, price: float, quantity: int):
        """执行订单 (模拟成交)"""
        # 计算费用
        fees = self.rules.calculate_cost(price, quantity, is_buy=(action == "buy"))
        
        if action == "buy":
            # 扣除资金
            total_cost = price * quantity + fees['total_cost']
            self.cash -= total_cost
            
            # 更新持仓
            if stock_code not in self.positions:
                self.positions[stock_code] = Position(stock_code, stock_name)
            
            self.positions[stock_code].add_buy(price, quantity)
            
            logger.info(f"买入成交：{stock_code} {quantity}股 @ ¥{price:.2f}, "
                       f"费用¥{fees['total_cost']:.2f}, 剩余资金¥{self.cash:,.2f}")
        
        elif action == "sell":
            # 增加资金
            total_proceeds = price * quantity - fees['total_cost']
            self.cash += total_proceeds
            
            # 更新持仓
            if stock_code in self.positions:
                position = self.positions[stock_code]
                position.quantity -= quantity
                position.available -= quantity
                
                if position.quantity <= 0:
                    del self.positions[stock_code]
            
            logger.info(f"卖出成交：{stock_code} {quantity}股 @ ¥{price:.2f}, "
                       f"费用¥{fees['total_cost']:.2f}, 剩余资金¥{self.cash:,.2f}")
        
        # 更新订单状态
        self.order_book.update_order(
            order_id,
            status="filled",
            filled_quantity=quantity,
            fill_time=datetime.now().isoformat()
        )
    
    def handle_query_position(self, message: Message):
        """处理持仓查询"""
        stock_code = message.content.get('stock_code')
        
        if stock_code:
            # 查询单只股票
            if stock_code in self.positions:
                position = self.positions[stock_code]
                position.update_available()
                self.send_message(
                    message.from_agent,
                    "position_info",
                    position.to_dict()
                )
            else:
                self.send_message(
                    message.from_agent,
                    "position_info",
                    {"stock_code": stock_code, "quantity": 0, "available": 0}
                )
        else:
            # 查询所有持仓
            all_positions = {
                code: pos.to_dict() for code, pos in self.positions.items()
            }
            self.send_message(
                message.from_agent,
                "position_list",
                {
                    "positions": all_positions,
                    "cash": self.cash,
                    "total_value": self.calculate_total_value()
                }
            )
    
    def handle_query_order(self, message: Message):
        """处理订单查询"""
        order_id = message.content.get('order_id')
        
        if order_id:
            order = self.order_book.get_order(order_id)
            self.send_message(
                message.from_agent,
                "order_info",
                order or {"error": "订单不存在"}
            )
        else:
            orders = self.order_book.get_recent_orders()
            self.send_message(
                message.from_agent,
                "order_list",
                {"orders": orders}
            )
    
    def handle_cancel_order(self, message: Message):
        """处理撤单"""
        order_id = message.content.get('order_id')
        order = self.order_book.get_order(order_id)
        
        if not order:
            self.send_message(
                message.from_agent,
                "cancel_result",
                {"success": False, "reason": "订单不存在"}
            )
            return
        
        if order['status'] in ['filled', 'cancelled']:
            self.send_message(
                message.from_agent,
                "cancel_result",
                {"success": False, "reason": f"订单状态不允许撤单：{order['status']}"}
            )
            return
        
        # 撤单
        self.order_book.update_order(order_id, status='cancelled')
        self.send_message(
            message.from_agent,
            "cancel_result",
            {"success": True, "order_id": order_id}
        )
    
    def calculate_total_value(self) -> float:
        """计算总资产"""
        position_value = sum(
            pos.quantity * pos.cost_price 
            for pos in self.positions.values()
        )
        return self.cash + position_value
    
    def get_pnl(self) -> float:
        """计算盈亏"""
        total_value = self.calculate_total_value()
        return total_value - self.starting_cash
    
    def on_tick(self):
        """定期调用"""
        # 更新持仓可用数量 (T+1)
        for position in self.positions.values():
            position.update_available()
        
        # 发布状态
        self.publish_event("execution_status", {
            "cash": round(self.cash, 2),
            "positions": len(self.positions),
            "total_value": round(self.calculate_total_value(), 2),
            "pnl": round(self.get_pnl(), 2),
            "pnl_pct": round(self.get_pnl() / self.starting_cash * 100, 2)
        })
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "agent": "execution_bot",
            "running": self.running,
            "cash": round(self.cash, 2),
            "positions": {code: pos.to_dict() for code, pos in self.positions.items()},
            "recent_orders": self.order_book.get_recent_orders(10),
            "total_value": round(self.calculate_total_value(), 2),
            "pnl": round(self.get_pnl(), 2)
        }


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Execution Bot 启动")
    logger.info("=" * 60)
    
    bot = ExecutionBot()
    bot.start(tick_interval=10.0)  # 每 10 秒更新一次
    
    # 保持运行
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号")
        bot.stop()


if __name__ == "__main__":
    main()
