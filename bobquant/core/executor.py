# -*- coding: utf-8 -*-
"""
BobQuant 交易执行器 v2.2.13
统一的买入、卖出、交易记录同步
支持交易标识符管理 (A→B 标识符系统)
支持不同板块交易规则 (主板/创业板/科创板)
"""
import json
import os
from datetime import datetime
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


class Executor:
    """交易执行器"""

    def __init__(self, account, commission_rate=0.0005, trade_log_file='', logger=None, notifier=None):
        self.account = account
        self.commission_rate = commission_rate
        self.trade_log_file = trade_log_file
        self.log = logger or (lambda msg: print(msg))
        self.notify = notifier or (lambda title, msg: None)

    def buy(self, code, name, shares, price, reason, is_add=False):
        """买入（新建仓或加仓），返回交易记录 dict 或 None"""
        # v1.1.4 修复：根据板块规则规范化股数
        shares = normalize_shares(code, shares, 'buy')
        if shares <= 0:
            return None

        cost = shares * price
        commission = cost * self.commission_rate
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
            })
            action_label = "买入"

        self.log(f"  🟢 {action_label} {name}: {shares}股 @ ¥{price:.2f} (手续费¥{commission:.2f})")
        self.log(f"     原因：{reason}")
        self.notify(f"🟢 {action_label} - {name}",
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

    def sell(self, code, name, shares, price, reason, action_label='卖出'):
        """卖出（支持部分卖出），返回交易记录 dict 或 None"""
        if not self.account.has_position(code):
            return None
        pos = self.account.get_position(code)

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
        net_revenue = revenue - commission
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

        emoji = "🔄" if "做T" in action_label else "🔴"
        if pos['shares'] <= 0:
            self.account.remove_position(code)
            self.log(f"  {emoji} {action_label} {name}: {shares}股 @ ¥{price:.2f} (清仓)")
        else:
            self.log(f"  {emoji} {action_label} {name}: {shares}股 @ ¥{price:.2f} (剩余{pos['shares']}股)")

        self.log(f"     盈亏：¥{profit:,.2f} ({profit_pct:+.1f}%)")
        self.log(f"     原因：{reason}")

        self.notify(f"{emoji} {action_label} - {name}",
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
