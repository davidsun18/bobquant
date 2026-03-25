# -*- coding: utf-8 -*-
"""
BobQuant 账户与持仓管理
"""
import json
import os
from datetime import datetime
from pathlib import Path


class Account:
    """交易账户"""

    def __init__(self, filepath, initial_capital=1000000):
        self.filepath = Path(filepath)
        self.initial_capital = initial_capital
        self._data = None

    def load(self):
        if self.filepath.exists() and self.filepath.stat().st_size > 0:
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
                return self
            except (json.JSONDecodeError, ValueError):
                pass
        # 新建或文件损坏
        self._data = {
            'cash': self.initial_capital,
            'initial_capital': self.initial_capital,
            'positions': {},
            'trade_history': [],
            'start_date': datetime.now().strftime('%Y-%m-%d'),
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        return self

    def save(self):
        self._data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @property
    def cash(self):
        return self._data.get('cash', 0)

    @cash.setter
    def cash(self, value):
        self._data['cash'] = value

    @property
    def positions(self):
        return self._data.get('positions', {})

    @property
    def trade_history(self):
        return self._data.get('trade_history', [])

    def has_position(self, code):
        return code in self.positions and self.positions[code].get('shares', 0) > 0

    def get_position(self, code):
        return self.positions.get(code)

    def set_position(self, code, pos_dict):
        self._data['positions'][code] = pos_dict

    def remove_position(self, code):
        if code in self._data['positions']:
            del self._data['positions'][code]

    def add_trade(self, trade):
        self._data['trade_history'].append(trade)

    def migrate_positions(self):
        """兼容旧数据：给持仓添加 buy_lots / add_level / profit_taken"""
        for code, pos in self.positions.items():
            if 'buy_lots' not in pos:
                pos['buy_lots'] = [{
                    'shares': pos['shares'],
                    'price': pos.get('buy_price', pos['avg_price']),
                    'date': pos.get('buy_date', '2026-03-24'),
                    'time': pos.get('buy_time', ''),
                }]
            if 'add_level' not in pos:
                pos['add_level'] = 1
            if 'profit_taken' not in pos:
                pos['profit_taken'] = 0


def get_sellable_shares(pos):
    """计算 T+1 可卖股数（通过 buy_lots 逐笔判断）"""
    today = datetime.now().strftime('%Y-%m-%d')
    lots = pos.get('buy_lots', [])
    if not lots:
        if pos.get('buy_date', '') == today:
            return 0
        return pos.get('shares', 0)
    sellable = sum(lot['shares'] for lot in lots if lot['date'] != today)
    return min(sellable, pos.get('shares', 0))
