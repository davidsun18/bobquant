#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TWAP/VWAP 算法订单执行器 - QuantConnect/Lean 核心算法实现

功能:
- TWAP (时间加权平均价格) 执行
- VWAP (成交量加权平均价格) 执行
- 订单状态跟踪与报告

使用示例:
    python twap_executor.py --symbol 000001.SZ --side buy --qty 10000 --duration 10 --slices 5
"""

import argparse
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class OrderSide(Enum):
    BUY = 'buy'
    SELL = 'sell'


class OrderStatus(Enum):
    PENDING = 'pending'
    ACTIVE = 'active'
    PARTIALLY_FILLED = 'partially_filled'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


@dataclass
class TWAPOrder:
    """TWAP 订单配置"""
    symbol: str
    total_quantity: int
    duration_minutes: int
    num_slices: int
    side: OrderSide
    order_id: str = field(default_factory=lambda: f"TWAP_{datetime.now().strftime('%H%M%S_%f')}")


@dataclass
class VWAPOrder:
    """VWAP 订单配置"""
    symbol: str
    total_quantity: int
    side: OrderSide
    lookback_days: int = 20
    order_id: str = field(default_factory=lambda: f"VWAP_{datetime.now().strftime('%H%M%S_%f')}")


@dataclass
class SliceExecution:
    """单次切片执行记录"""
    slice_idx: int
    scheduled_time: datetime
    quantity: int
    executed: bool = False
    fill_price: float = 0.0
    fill_time: Optional[datetime] = None
    status: str = 'pending'


class MockBroker:
    """模拟经纪商 - 用于测试"""
    
    def __init__(self, base_price: float = 100.0, volatility: float = 0.01):
        self.base_price = base_price
        self.volatility = volatility
        self.current_price = base_price
        self.orders = []
    
    def get_price(self, symbol: str) -> float:
        """获取当前价格（带随机波动）"""
        import random
        change = random.gauss(0, self.volatility)
        self.current_price = self.base_price * (1 + change)
        return self.current_price
    
    def submit_limit_order(self, symbol: str, side: OrderSide, quantity: int, limit_price: float) -> Tuple[bool, float]:
        """
        提交限价单
        
        返回：(是否成交，成交价)
        """
        # 模拟成交：随机决定是否成交，成交价在限价附近
        import random
        
        # 买单：当前价 <= 限价时可能成交
        # 卖单：当前价 >= 限价时可能成交
        current = self.get_price(symbol)
        
        if side == OrderSide.BUY and current <= limit_price * 1.001:
            fill_price = limit_price * (0.999 + random.random() * 0.002)
            return True, fill_price
        elif side == OrderSide.SELL and current >= limit_price * 0.999:
            fill_price = limit_price * (0.999 + random.random() * 0.002)
            return True, fill_price
        
        return False, 0.0


class TWAPExecutor:
    """TWAP 执行器"""
    
    def __init__(self, broker):
        self.broker = broker
        self.active_orders: Dict[str, Dict] = {}
        self.completed_orders: Dict[str, Dict] = {}
    
    def submit_twap(self, order: TWAPOrder) -> str:
        """
        提交 TWAP 订单
        
        将大单按时间均匀拆分，在指定时间段内执行
        
        返回：order_id
        """
        # 计算每份数量和时间间隔
        slice_qty = order.total_quantity // order.num_slices
        remainder = order.total_quantity % order.num_slices
        
        interval = timedelta(minutes=order.duration_minutes / order.num_slices)
        
        # 生成执行计划
        schedule: List[SliceExecution] = []
        current_time = datetime.now()
        
        for i in range(order.num_slices):
            # 最后一份包含余数
            qty = slice_qty + (remainder if i == order.num_slices - 1 else 0)
            scheduled_time = current_time + i * interval
            
            schedule.append(SliceExecution(
                slice_idx=i,
                scheduled_time=scheduled_time,
                quantity=qty
            ))
        
        self.active_orders[order.order_id] = {
            'order': order,
            'schedule': schedule,
            'filled_qty': 0,
            'avg_price': 0.0,
            'total_value': 0.0,
            'status': OrderStatus.ACTIVE,
            'start_time': datetime.now(),
            'executions': []
        }
        
        print(f"✅ TWAP 订单已提交:")
        print(f"   订单 ID: {order.order_id}")
        print(f"   标的：{order.symbol}")
        print(f"   方向：{order.side.value}")
        print(f"   总量：{order.total_quantity}")
        print(f"   拆分：{order.num_slices} 份")
        print(f"   时长：{order.duration_minutes} 分钟")
        print(f"   每份：约 {slice_qty} 股")
        
        return order.order_id
    
    def check_and_execute(self) -> Dict[str, List]:
        """检查并执行到期的切片"""
        current_time = datetime.now()
        executions = []
        
        for order_id, order_data in list(self.active_orders.items()):
            if order_data['status'] not in [OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]:
                continue
            
            order = order_data['order']
            schedule = order_data['schedule']
            
            for slice_exec in schedule:
                if slice_exec.executed:
                    continue
                
                if current_time >= slice_exec.scheduled_time:
                    # 执行该切片
                    result = self._execute_slice(order_id, slice_exec)
                    if result:
                        executions.append(result)
            
            # 检查订单是否完成
            self._check_order_completion(order_id)
        
        return executions
    
    def _execute_slice(self, order_id: str, slice_exec: SliceExecution) -> Optional[Dict]:
        """执行单份订单"""
        if order_id not in self.active_orders:
            return None
        
        order_data = self.active_orders[order_id]
        order = order_data['order']
        
        # 获取当前价格
        current_price = self.broker.get_price(order.symbol)
        
        # 设置限价（买单略高于市价，卖单略低于市价）
        if order.side == OrderSide.BUY:
            limit_price = current_price * 1.001
        else:
            limit_price = current_price * 0.999
        
        # 提交订单
        filled, fill_price = self.broker.submit_limit_order(
            order.symbol, order.side, slice_exec.quantity, limit_price
        )
        
        # 更新执行记录
        slice_exec.executed = filled
        slice_exec.fill_time = datetime.now() if filled else None
        slice_exec.status = 'filled' if filled else 'pending'
        
        if filled:
            slice_exec.fill_price = fill_price
            
            # 更新订单统计
            prev_qty = order_data['filled_qty']
            prev_value = order_data['avg_price'] * prev_qty if prev_qty > 0 else 0
            
            new_qty = prev_qty + slice_exec.quantity
            new_value = prev_value + (fill_price * slice_exec.quantity)
            
            order_data['filled_qty'] = new_qty
            order_data['avg_price'] = new_value / new_qty if new_qty > 0 else 0
            order_data['total_value'] = new_value
            order_data['executions'].append({
                'slice_idx': slice_exec.slice_idx,
                'quantity': slice_exec.quantity,
                'price': fill_price,
                'time': slice_exec.fill_time.isoformat()
            })
            
            print(f"  ✓ 执行切片 {slice_exec.slice_idx + 1}/{len(order_data['schedule'])}: "
                  f"{slice_exec.quantity} @ {fill_price:.2f}")
            
            return {
                'order_id': order_id,
                'slice_idx': slice_exec.slice_idx,
                'quantity': slice_exec.quantity,
                'price': fill_price,
                'time': slice_exec.fill_time
            }
        else:
            print(f"  ✗ 切片 {slice_exec.slice_idx + 1} 未成交，等待重试")
        
        return None
    
    def _check_order_completion(self, order_id: str):
        """检查订单是否完成"""
        order_data = self.active_orders[order_id]
        schedule = order_data['schedule']
        
        all_executed = all(s.executed for s in schedule)
        
        if all_executed:
            order_data['status'] = OrderStatus.COMPLETED
            order_data['end_time'] = datetime.now()
            
            # 移到已完成订单
            self.completed_orders[order_id] = self.active_orders.pop(order_id)
            
            print(f"\n🎉 TWAP 订单完成: {order_id}")
            print(f"   总成交：{order_data['filled_qty']} 股")
            print(f"   平均价：{order_data['avg_price']:.2f}")
            print(f"   总金额：{order_data['total_value']:.2f}")
            print(f"   执行时长：{(order_data['end_time'] - order_data['start_time']).total_seconds():.1f} 秒")


class VWAPExecutor:
    """VWAP 执行器"""
    
    def __init__(self, broker, lookback_days: int = 20):
        self.broker = broker
        self.lookback_days = lookback_days
        self.active_orders: Dict[str, Dict] = {}
        self.volume_profiles: Dict[str, Dict] = {}
    
    def calculate_volume_profile(self, symbol: str) -> Dict[str, float]:
        """
        计算历史成交量分布
        
        返回：每个时间段的成交量占比（0-1）
        """
        if symbol in self.volume_profiles:
            return self.volume_profiles[symbol]
        
        # 模拟历史成交量数据（实际应从数据源获取）
        # A 股交易时段：9:30-11:30, 13:00-15:00 (共 4 小时 = 240 分钟)
        
        import random
        random.seed(42)  # 固定种子以便复现
        
        volume_profile = {}
        total_weight = 0
        
        # 早盘（开盘和收盘成交量较大）
        for minute in range(120):  # 9:30-11:30
            hour = 9 + (minute + 30) // 60
            min = (minute + 30) % 60
            time_key = f"{hour:02d}:{min:02d}"
            
            # 模拟成交量分布：开盘和收盘较大，中间较小
            if minute < 15 or minute > 105:
                weight = 2.0 + random.random()
            else:
                weight = 1.0 + random.random() * 0.5
            
            volume_profile[time_key] = weight
            total_weight += weight
        
        # 午盘
        for minute in range(120):  # 13:00-15:00
            hour = 13 + minute // 60
            min = minute % 60
            time_key = f"{hour:02d}:{min:02d}"
            
            # 午盘开盘和收盘较大
            if minute < 15 or minute > 105:
                weight = 2.0 + random.random()
            else:
                weight = 1.0 + random.random() * 0.5
            
            volume_profile[time_key] = weight
            total_weight += weight
        
        # 归一化为占比
        for key in volume_profile:
            volume_profile[key] /= total_weight
        
        self.volume_profiles[symbol] = volume_profile
        return volume_profile
    
    def submit_vwap(self, order: VWAPOrder) -> str:
        """
        提交 VWAP 订单
        
        根据历史成交量分布，在成交活跃时段多执行，清淡时段少执行
        """
        # 获取成交量分布
        volume_profile = self.calculate_volume_profile(order.symbol)
        
        # 根据分布分配订单量（只取交易时段的 profile）
        schedule: List[SliceExecution] = []
        remaining_qty = order.total_quantity
        
        sorted_times = sorted(volume_profile.keys())
        
        for i, time_key in enumerate(sorted_times):
            vol_ratio = volume_profile[time_key]
            
            # 计算该时段应执行的数量
            qty = int(order.total_quantity * vol_ratio)
            if remaining_qty < qty:
                qty = remaining_qty
            
            # 转换为今天的 datetime
            today = datetime.now().date()
            hour, minute = map(int, time_key.split(':'))
            scheduled_time = datetime(today.year, today.month, today.day, hour, minute)
            
            # 如果时间已过，跳过
            if scheduled_time < datetime.now():
                continue
            
            schedule.append(SliceExecution(
                slice_idx=i,
                scheduled_time=scheduled_time,
                quantity=qty
            ))
            remaining_qty -= qty
        
        # 处理余数（加到最后一份）
        if remaining_qty > 0 and schedule:
            schedule[-1].quantity += remaining_qty
        elif remaining_qty > 0:
            # 如果没有 schedule，创建一个立即执行的切片
            schedule.append(SliceExecution(
                slice_idx=0,
                scheduled_time=datetime.now(),
                quantity=remaining_qty
            ))
        
        self.active_orders[order.order_id] = {
            'order': order,
            'schedule': schedule,
            'filled_qty': 0,
            'avg_price': 0.0,
            'total_value': 0.0,
            'status': OrderStatus.ACTIVE,
            'start_time': datetime.now(),
            'executions': []
        }
        
        print(f"✅ VWAP 订单已提交:")
        print(f"   订单 ID: {order.order_id}")
        print(f"   标的：{order.symbol}")
        print(f"   方向：{order.side.value}")
        print(f"   总量：{order.total_quantity}")
        print(f"   拆分：{len(schedule)} 个时间段")
        
        return order.order_id
    
    def check_and_execute(self) -> Dict[str, List]:
        """检查并执行到期的切片"""
        # 实现与 TWAPExecutor 类似
        current_time = datetime.now()
        executions = []
        
        for order_id, order_data in list(self.active_orders.items()):
            if order_data['status'] not in [OrderStatus.ACTIVE, OrderStatus.PARTIALLY_FILLED]:
                continue
            
            order = order_data['order']
            schedule = order_data['schedule']
            
            for slice_exec in schedule:
                if slice_exec.executed:
                    continue
                
                if current_time >= slice_exec.scheduled_time:
                    # 执行逻辑与 TWAP 相同
                    result = self._execute_slice(order_id, slice_exec, order)
                    if result:
                        executions.append(result)
            
            self._check_order_completion(order_id)
        
        return executions
    
    def _execute_slice(self, order_id: str, slice_exec: SliceExecution, order: VWAPOrder) -> Optional[Dict]:
        """执行单份订单（与 TWAP 类似）"""
        if order_id not in self.active_orders:
            return None
        
        order_data = self.active_orders[order_id]
        
        current_price = self.broker.get_price(order.symbol)
        
        if order.side == OrderSide.BUY:
            limit_price = current_price * 1.001
        else:
            limit_price = current_price * 0.999
        
        filled, fill_price = self.broker.submit_limit_order(
            order.symbol, order.side, slice_exec.quantity, limit_price
        )
        
        slice_exec.executed = filled
        slice_exec.fill_time = datetime.now() if filled else None
        slice_exec.status = 'filled' if filled else 'pending'
        
        if filled:
            slice_exec.fill_price = fill_price
            
            prev_qty = order_data['filled_qty']
            prev_value = order_data['avg_price'] * prev_qty if prev_qty > 0 else 0
            
            new_qty = prev_qty + slice_exec.quantity
            new_value = prev_value + (fill_price * slice_exec.quantity)
            
            order_data['filled_qty'] = new_qty
            order_data['avg_price'] = new_value / new_qty if new_qty > 0 else 0
            order_data['total_value'] = new_value
            
            print(f"  ✓ VWAP 执行：{slice_exec.quantity} @ {fill_price:.2f}")
            
            return {
                'order_id': order_id,
                'quantity': slice_exec.quantity,
                'price': fill_price,
                'time': slice_exec.fill_time
            }
        
        return None
    
    def _check_order_completion(self, order_id: str):
        """检查订单是否完成"""
        order_data = self.active_orders[order_id]
        schedule = order_data['schedule']
        
        all_executed = all(s.executed for s in schedule)
        
        if all_executed:
            order_data['status'] = OrderStatus.COMPLETED
            order_data['end_time'] = datetime.now()
            
            self.active_orders.pop(order_id)
            
            print(f"\n🎉 VWAP 订单完成：{order_id}")
            print(f"   总成交：{order_data['filled_qty']} 股")
            print(f"   平均价：{order_data['avg_price']:.2f}")


def run_demo():
    """运行演示"""
    print("=" * 60)
    print("TWAP/VWAP算法订单执行器演示")
    print("=" * 60)
    
    # 创建模拟经纪商
    broker = MockBroker(base_price=10.5, volatility=0.005)
    
    # 创建执行器
    twap_exec = TWAPExecutor(broker)
    
    # 提交 TWAP 订单
    twap_order = TWAPOrder(
        symbol='000001.SZ',
        total_quantity=10000,
        duration_minutes=5,  # 演示用较短时间
        num_slices=5,
        side=OrderSide.BUY
    )
    
    order_id = twap_exec.submit_twap(twap_order)
    
    # 模拟执行循环
    print("\n⏳ 开始执行...")
    for i in range(10):
        time.sleep(1)  # 每秒检查一次
        twap_exec.check_and_execute()
        
        if order_id not in twap_exec.active_orders:
            break
    
    print("\n✅ 演示完成!")


def main():
    parser = argparse.ArgumentParser(
        description='TWAP/VWAP 算法订单执行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # TWAP 订单演示
  python twap_executor.py --demo
  
  # TWAP 订单
  python twap_executor.py --type twap --symbol 000001.SZ --side buy --qty 10000 --duration 10 --slices 5
  
  # VWAP 订单
  python twap_executor.py --type vwap --symbol 000001.SZ --side sell --qty 5000
        """
    )
    
    parser.add_argument('--demo', action='store_true', help='运行演示')
    parser.add_argument('--type', choices=['twap', 'vwap'], default='twap', help='订单类型')
    parser.add_argument('--symbol', type=str, default='000001.SZ', help='股票代码')
    parser.add_argument('--side', choices=['buy', 'sell'], default='buy', help='买卖方向')
    parser.add_argument('--qty', type=int, default=10000, help='总数量')
    parser.add_argument('--duration', type=int, default=10, help='执行时长（分钟，仅 TWAP）')
    parser.add_argument('--slices', type=int, default=5, help='拆分份数（仅 TWAP）')
    
    args = parser.parse_args()
    
    if args.demo:
        run_demo()
        return
    
    # 创建模拟经纪商
    broker = MockBroker(base_price=10.5, volatility=0.005)
    
    if args.type == 'twap':
        executor = TWAPExecutor(broker)
        order = TWAPOrder(
            symbol=args.symbol,
            total_quantity=args.qty,
            duration_minutes=args.duration,
            num_slices=args.slices,
            side=OrderSide(args.side)
        )
    else:
        executor = VWAPExecutor(broker)
        order = VWAPOrder(
            symbol=args.symbol,
            total_quantity=args.qty,
            side=OrderSide(args.side)
        )
    
    order_id = executor.submit_twap(order) if args.type == 'twap' else executor.submit_vwap(order)
    
    # 执行循环
    print("\n⏳ 开始执行...")
    for i in range(30):
        time.sleep(1)
        executor.check_and_execute()
        
        if order_id not in executor.active_orders:
            break


if __name__ == '__main__':
    main()
