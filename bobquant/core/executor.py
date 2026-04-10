# -*- coding: utf-8 -*-
"""
BobQuant 交易执行器 v2.3
统一的买入、卖出、交易记录同步
支持交易标识符管理 (A→B 标识符系统)
支持不同板块交易规则 (主板/创业板/科创板)
集成 TWAP 算法执行器（大单自动拆分）
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from .account import get_sellable_shares
from .trading_rules import get_min_shares, get_step_size, get_max_shares, normalize_shares, get_board_type
from .trade_id import get_next_trade_id, finalize_trade_id


def finalize_trade(trade):
    """
    将交易标识符从 A 转换为 B (标记为已成交)
    
    Args:
        trade: 交易记录 dict
        
    Returns:
        dict: 更新后的交易记录
    """
    if trade and 'trade_id' in trade:
        trade['trade_id'] = finalize_trade_id(trade['trade_id'])
        trade['status'] = 'completed'
    return trade


class TWAPExecutor:
    """
    TWAP (时间加权平均价格) 执行器
    将大单按时间均匀拆分，减少市场冲击
    """
    
    def __init__(self, executor, enabled=True, threshold=10000, num_slices=5, duration_minutes=10):
        """
        Args:
            executor: 基础 Executor 实例
            enabled: 是否启用 TWAP
            threshold: 触发 TWAP 的股数阈值（默认 10000 股）
            num_slices: 拆分份数
            duration_minutes: 执行时长（分钟）
        """
        self.executor = executor
        self.enabled = enabled
        self.threshold = threshold
        self.num_slices = num_slices
        self.duration_minutes = duration_minutes
        self.active_twap_orders: Dict[str, dict] = {}
    
    def should_use_twap(self, shares: int) -> bool:
        """判断是否应该使用 TWAP 执行"""
        return self.enabled and shares >= self.threshold
    
    def execute_buy_twap(self, code: str, name: str, shares: int, price: float, 
                         reason: str, is_add: bool = False) -> list:
        """
        使用 TWAP 执行买入订单（直接拆分，不再检查阈值）
        
        Returns:
            list: 交易记录列表
        """
        # 此方法已被调用，说明已经通过阈值检查或手动指定，直接执行拆分
        
        # 计算每份数量和时间间隔
        slice_qty = shares // self.num_slices
        remainder = shares % self.num_slices
        interval = timedelta(minutes=self.duration_minutes / self.num_slices)
        
        self.executor.log(f"  🔄 TWAP 买入 {name}: {shares}股 → 拆分为 {self.num_slices} 份")
        self.executor.log(f"     每份：约 {slice_qty} 股，间隔：{self.duration_minutes/self.num_slices:.1f} 分钟")
        
        trades = []
        current_time = datetime.now()
        
        for i in range(self.num_slices):
            # 最后一份包含余数
            qty = slice_qty + (remainder if i == self.num_slices - 1 else 0)
            scheduled_time = current_time + i * interval
            
            # 创建 TWAP 订单记录
            order_id = f"TWAP_{code}_{datetime.now().strftime('%H%M%S_%f')}"
            self.active_twap_orders[order_id] = {
                'code': code,
                'name': name,
                'total_shares': shares,
                'slice_idx': i,
                'slice_qty': qty,
                'scheduled_time': scheduled_time,
                'price': price,
                'reason': reason,
                'is_add': is_add,
                'status': 'pending'
            }
            
            # 立即执行（模拟环境）
            # 实盘环境下应该定时检查并执行到期的切片
            trade = self.executor.buy(code, name, qty, price, 
                                     f"{reason} [TWAP {i+1}/{self.num_slices}]", is_add)
            if trade:
                trade['twap_order_id'] = order_id
                trade['twap_slice'] = i + 1
                trade['twap_total_slices'] = self.num_slices
                trades.append(trade)
                self.active_twap_orders[order_id]['status'] = 'filled'
        
        return trades
    
    def execute_sell_twap(self, code: str, name: str, shares: int, price: float,
                          reason: str, action_label: str = '卖出') -> list:
        """
        使用 TWAP 执行卖出订单（直接拆分，不再检查阈值）
        
        Returns:
            list: 交易记录列表
        """
        # 此方法已被调用，说明已经通过阈值检查或手动指定，直接执行拆分
        
        # 计算每份数量和时间间隔
        slice_qty = shares // self.num_slices
        remainder = shares % self.num_slices
        interval = timedelta(minutes=self.duration_minutes / self.num_slices)
        
        self.executor.log(f"  🔄 TWAP 卖出 {name}: {shares}股 → 拆分为 {self.num_slices} 份")
        self.executor.log(f"     每份：约 {slice_qty} 股，间隔：{self.duration_minutes/self.num_slices:.1f} 分钟")
        
        trades = []
        current_time = datetime.now()
        
        for i in range(self.num_slices):
            qty = slice_qty + (remainder if i == self.num_slices - 1 else 0)
            scheduled_time = current_time + i * interval
            
            order_id = f"TWAP_{code}_{datetime.now().strftime('%H%M%S_%f')}"
            self.active_twap_orders[order_id] = {
                'code': code,
                'name': name,
                'total_shares': shares,
                'slice_idx': i,
                'slice_qty': qty,
                'scheduled_time': scheduled_time,
                'price': price,
                'reason': reason,
                'action_label': action_label,
                'status': 'pending'
            }
            
            # 立即执行（模拟环境）
            trade = self.executor.sell(code, name, qty, price,
                                      f"{reason} [TWAP {i+1}/{self.num_slices}]", action_label)
            if trade:
                trade['twap_order_id'] = order_id
                trade['twap_slice'] = i + 1
                trade['twap_total_slices'] = self.num_slices
                trades.append(trade)
                self.active_twap_orders[order_id]['status'] = 'filled'
        
        return trades
    
    def get_active_orders(self) -> dict:
        """获取活跃的 TWAP 订单"""
        return self.active_twap_orders
    
    def check_and_execute_pending(self):
        """检查并执行待处理的 TWAP 切片（实盘使用）"""
        current_time = datetime.now()
        executed = []
        
        for order_id, order_data in list(self.active_twap_orders.items()):
            if order_data['status'] != 'pending':
                continue
            
            if current_time >= order_data['scheduled_time']:
                code = order_data['code']
                name = order_data['name']
                qty = order_data['slice_qty']
                price = order_data['price']
                reason = order_data['reason']
                is_add = order_data.get('is_add', False)
                action_label = order_data.get('action_label', '卖出')
                
                if '买入' in action_label or is_add:
                    trade = self.executor.buy(code, name, qty, price,
                                             f"{reason} [TWAP {order_data['slice_idx']+1}/{self.num_slices}]", is_add)
                else:
                    trade = self.executor.sell(code, name, qty, price,
                                              f"{reason} [TWAP {order_data['slice_idx']+1}/{self.num_slices}]", action_label)
                
                if trade:
                    trade['twap_order_id'] = order_id
                    trade['twap_slice'] = order_data['slice_idx'] + 1
                    executed.append(trade)
                
                order_data['status'] = 'filled'
        
        return executed


class Executor:
    """交易执行器"""

    def __init__(self, account, commission_rate=0.0005, trade_log_file='', logger=None, notifier=None,
                 twap_enabled=False, twap_threshold=10000, twap_slices=5, twap_duration=10):
        """
        Args:
            account: 账户实例
            commission_rate: 手续费率
            trade_log_file: 交易日志文件路径
            logger: 日志函数
            notifier: 通知函数
            twap_enabled: 是否启用 TWAP 算法执行
            twap_threshold: 触发 TWAP 的股数阈值
            twap_slices: TWAP 拆分份数
            twap_duration: TWAP 执行时长（分钟）
        """
        self.account = account
        self.commission_rate = commission_rate
        self.trade_log_file = trade_log_file
        self.log = logger or (lambda msg: print(msg))
        self.notify = notifier or (lambda title, msg: None)
        
        # TWAP 执行器
        self.twap_executor = TWAPExecutor(
            self,
            enabled=twap_enabled,
            threshold=twap_threshold,
            num_slices=twap_slices,
            duration_minutes=twap_duration
        )

    def buy(self, code, name, shares, price, reason, is_add=False, use_twap=None):
        """
        买入（新建仓或加仓），返回交易记录 dict 或 None
        
        Args:
            code: 股票代码
            name: 股票名称
            shares: 股数
            price: 价格
            reason: 原因
            is_add: 是否加仓
            use_twap: 是否使用 TWAP（None 则自动判断）
        
        Returns:
            dict or list: 交易记录（单个 dict 或 TWAP 拆分后的 list）
        """
        # 如果明确指定使用 TWAP 或自动判断需要使用
        if use_twap is True or (use_twap is None and self.twap_executor.should_use_twap(shares)):
            # 临时启用 TWAP（即使用户设置了 enabled=False，use_twap=True 优先级更高）
            old_enabled = self.twap_executor.enabled
            if use_twap is True:
                self.twap_executor.enabled = True
            result = self.twap_executor.execute_buy_twap(code, name, shares, price, reason, is_add)
            self.twap_executor.enabled = old_enabled
            return result
        
        # v1.1.4 修复：根据板块规则规范化股数
        shares = normalize_shares(code, shares, 'buy')
        if shares <= 0:
            return None
        
        # 保存股票名称到持仓
        stock_name = name if name else code

        cost = shares * price
        commission = cost * self.commission_rate
        commission = max(commission, 5)  # 最低 5 元
        total_cost = cost + commission

        if total_cost > self.account.cash:
            self.log(f"  ⚠️ {name}: 资金不足 (需要¥{total_cost:,.0f}, 可用¥{self.account.cash:,.0f})")
            return None

        self.account.cash -= total_cost
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today_str = datetime.now().strftime('%Y-%m-%d')

        new_lot = {'shares': shares, 'price': price, 'date': today_str, 'time': now_str}

        if self.account.has_position(code):
            pos = self.account.get_position(code)
            old_shares = pos['shares']
            new_total = old_shares + shares
            pos['avg_price'] = (old_shares * pos['avg_price'] + shares * price) / new_total
            pos['shares'] = new_total
            pos['buy_lots'].append(new_lot)
            pos['add_level'] = pos.get('add_level', 1) + 1
            pos['commission'] = pos.get('commission', 0) + commission
            action_label = f"加仓L{pos['add_level']}" if is_add else "买入"
        else:
            self.account.set_position(code, {
                'shares': shares, 'avg_price': price, 'buy_price': price,
                'buy_date': today_str, 'buy_time': now_str, 'commission': commission,
                'buy_lots': [new_lot], 'add_level': 1, 'profit_taken': 0,
                'name': stock_name,  # 保存股票名称
            })
            action_label = "买入"

        self.log(f"  🔴 {action_label} {name}: {shares}股 @ ¥{price:.2f} (手续费¥{commission:.2f})")
        self.log(f"     原因：{reason}")
        self.notify(f"🔴 {action_label} - {name}",
                     f"股票：{code} {name}\n操作：{action_label}\n数量：{shares}股\n"
                     f"价格：¥{price:.2f}\n金额：¥{cost:,.2f}\n手续费：¥{commission:.2f}\n"
                     f"原因：{reason}\n时间：{datetime.now().strftime('%H:%M:%S')}")

        # 生成交易标识符 (A+9 位数字)
        trade_id = get_next_trade_id()
        
        trade = {
            'time': now_str, 'code': code, 'name': name, 'action': action_label,
            'shares': shares, 'price': price, 'amount': cost,
            'commission': round(commission, 2), 'reason': reason,
            'trade_id': trade_id,  # A 标识符 (待成交)
            'status': 'pending',    # 待成交状态
        }
        self.account.add_trade(trade)
        
        # 交易完成后，将 A 标识符转换为 B 标识符 (已成交)
        finalized_trade = finalize_trade(trade)
        
        return finalized_trade

    def sell(self, code, name, shares, price, reason, action_label='卖出', use_twap=None):
        """
        卖出（支持部分卖出），返回交易记录 dict 或 None
        
        Args:
            code: 股票代码
            name: 股票名称
            shares: 股数
            price: 价格
            reason: 原因
            action_label: 操作标签
            use_twap: 是否使用 TWAP（None 则自动判断）
        
        Returns:
            dict or list: 交易记录（单个 dict 或 TWAP 拆分后的 list）
        """
        # 如果明确指定使用 TWAP 或自动判断需要使用
        if use_twap is True or (use_twap is None and self.twap_executor.should_use_twap(shares)):
            # 临时启用 TWAP（即使用户设置了 enabled=False，use_twap=True 优先级更高）
            old_enabled = self.twap_executor.enabled
            if use_twap is True:
                self.twap_executor.enabled = True
            result = self.twap_executor.execute_sell_twap(code, name, shares, price, reason, action_label)
            self.twap_executor.enabled = old_enabled
            return result
        
        if not self.account.has_position(code):
            return None
        pos = self.account.get_position(code)
        
        # 如果 name 为空，尝试从持仓中获取
        if not name:
            name = pos.get('name', '')

        # v1.1.4 修复：根据板块规则和零股规则规范化股数
        sellable = get_sellable_shares(pos)
        
        # 零股处理：不足 100 股 (科创板 200 股) 必须一次性卖出
        min_shares = get_min_shares(code)
        if sellable < min_shares:
            shares = sellable  # 零股全部卖出
        else:
            shares = normalize_shares(code, min(shares, sellable), 'sell')
        
        if shares <= 0:
            return None

        revenue = shares * price
        commission = revenue * self.commission_rate
        commission = max(commission, 5)  # 最低 5 元
        stamp_duty = revenue * 0.001  # 印花税千一（卖出收）
        net_revenue = revenue - commission - stamp_duty
        cost_basis = shares * pos['avg_price']
        profit = net_revenue - cost_basis
        profit_pct = (profit / cost_basis * 100) if cost_basis > 0 else 0

        self.account.cash += net_revenue

        # FIFO 更新 buy_lots
        today = datetime.now().strftime('%Y-%m-%d')
        remaining = shares
        new_lots = []
        for lot in pos.get('buy_lots', []):
            if remaining <= 0 or lot['date'] == today:
                new_lots.append(lot)
                continue
            if lot['shares'] <= remaining:
                remaining -= lot['shares']
            else:
                lot['shares'] -= remaining
                remaining = 0
                new_lots.append(lot)
        pos['buy_lots'] = new_lots
        pos['shares'] -= shares

        # 如果 action_label 已包含 emoji（如"🟢 策略减仓"），则不再添加
        has_emoji = any(c in action_label for c in "🟢🔴🔄⚪")
        prefix_emoji = "" if has_emoji else ("🔄" if "做 T" in action_label else "🟢")
        if pos['shares'] <= 0:
            self.account.remove_position(code)
            self.log(f"  {prefix_emoji} {action_label} {name}: {shares}股 @ ¥{price:.2f} (清仓)")
        else:
            self.log(f"  {prefix_emoji} {action_label} {name}: {shares}股 @ ¥{price:.2f} (剩余{pos['shares']}股)")

        self.log(f"     盈亏：¥{profit:,.2f} ({profit_pct:+.1f}%)")
        self.log(f"     原因：{reason}")

        self.notify(f"{prefix_emoji} {action_label} - {name}",
                     f"股票：{code} {name}\n操作：{action_label}\n数量：{shares}股\n"
                     f"价格：¥{price:.2f}\n金额：¥{revenue:,.2f}\n手续费：¥{commission:.2f}\n"
                     f"盈亏：¥{profit:,.2f} ({profit_pct:+.1f}%)\n原因：{reason}\n"
                     f"时间：{datetime.now().strftime('%H:%M:%S')}")

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 生成交易标识符 (A+9 位数字)
        trade_id = get_next_trade_id()
        
        trade = {
            'time': now_str, 'code': code, 'name': name, 'action': action_label,
            'shares': shares, 'price': price, 'amount': revenue,
            'commission': round(commission, 2), 'profit': round(profit, 2),
            'profit_pct': round(profit_pct, 2), 'reason': reason,
            'trade_id': trade_id,  # A 标识符 (待成交)
            'status': 'pending',    # 待成交状态
        }
        self.account.add_trade(trade)
        
        # 交易完成后，将 A 标识符转换为 B 标识符 (已成交)
        finalized_trade = finalize_trade(trade)
        
        return finalized_trade

    def sync_trade_log(self, trades):
        """同步交易到独立的交易记录文件（Web UI 读取）"""
        if not trades or not self.trade_log_file:
            return
        try:
            existing = []
            if os.path.exists(self.trade_log_file):
                with open(self.trade_log_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            existing.extend(trades)
            with open(self.trade_log_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            self.log(f"  ✅ 交易记录已同步")
        except Exception as e:
            self.log(f"  ⚠️ 交易记录同步失败: {e}")
