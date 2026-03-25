# -*- coding: utf-8 -*-
"""
BobQuant 券商接口层
可插拔设计：模拟盘 / easytrader / miniQMT 切换只需改 settings.yaml
"""
from abc import ABC, abstractmethod
from datetime import datetime


class BaseBroker(ABC):
    """券商抽象基类 — 所有券商实现这个接口"""

    @abstractmethod
    def buy(self, code, price, shares):
        """
        下买单
        返回: {'success': bool, 'order_id': str, 'filled_price': float, 'filled_shares': int, 'msg': str}
        """
        pass

    @abstractmethod
    def sell(self, code, price, shares):
        """
        下卖单
        返回: 同 buy
        """
        pass

    @abstractmethod
    def get_positions(self):
        """
        查询持仓
        返回: {code: {'shares': int, 'avg_price': float, 'market_value': float}}
        """
        pass

    @abstractmethod
    def get_balance(self):
        """
        查询资金
        返回: {'cash': float, 'total_assets': float, 'frozen': float}
        """
        pass

    @abstractmethod
    def cancel(self, order_id):
        """撤单"""
        pass


class SimulatorBroker(BaseBroker):
    """
    模拟券商 — 假设所有订单都以指定价格成交
    当前系统使用这个，未来切实盘只需换实现类
    """

    def __init__(self, account):
        """account: bobquant.core.account.Account 实例"""
        self.account = account
        self._order_counter = 0

    def buy(self, code, price, shares):
        self._order_counter += 1
        order_id = f"SIM-B-{self._order_counter:06d}"
        return {
            'success': True,
            'order_id': order_id,
            'filled_price': price,
            'filled_shares': shares,
            'msg': '模拟成交',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    def sell(self, code, price, shares):
        self._order_counter += 1
        order_id = f"SIM-S-{self._order_counter:06d}"
        return {
            'success': True,
            'order_id': order_id,
            'filled_price': price,
            'filled_shares': shares,
            'msg': '模拟成交',
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    def get_positions(self):
        result = {}
        for code, pos in self.account.positions.items():
            result[code] = {
                'shares': pos.get('shares', 0),
                'avg_price': pos.get('avg_price', 0),
                'market_value': 0,  # 需要行情数据，这里先留0
            }
        return result

    def get_balance(self):
        return {
            'cash': self.account.cash,
            'total_assets': 0,  # 需要行情数据
            'frozen': 0,
        }

    def cancel(self, order_id):
        return {'success': True, 'msg': '模拟撤单'}


class EasytraderBroker(BaseBroker):
    """
    easytrader 实盘券商（预留，第五步实现）
    支持同花顺客户端 / miniQMT
    """

    def __init__(self, client_type='ths', **kwargs):
        self.client_type = client_type
        self._client = None
        # 未来: import easytrader; self._client = easytrader.use(client_type)

    def _ensure_connected(self):
        if self._client is None:
            raise RuntimeError("EasytraderBroker 未初始化，请先配置券商连接")

    def buy(self, code, price, shares):
        self._ensure_connected()
        # 未来: return self._client.buy(code, price=price, amount=shares)
        raise NotImplementedError("实盘买入待实现")

    def sell(self, code, price, shares):
        self._ensure_connected()
        raise NotImplementedError("实盘卖出待实现")

    def get_positions(self):
        self._ensure_connected()
        raise NotImplementedError("实盘持仓查询待实现")

    def get_balance(self):
        self._ensure_connected()
        raise NotImplementedError("实盘资金查询待实现")

    def cancel(self, order_id):
        self._ensure_connected()
        raise NotImplementedError("实盘撤单待实现")


# ==================== 券商工厂 ====================
def get_broker(mode='simulator', account=None, **kwargs):
    """获取券商实例"""
    if mode == 'simulator':
        if account is None:
            raise ValueError("SimulatorBroker 需要 account 参数")
        return SimulatorBroker(account)
    elif mode == 'easytrader':
        return EasytraderBroker(**kwargs)
    else:
        raise ValueError(f"未知券商模式: {mode}")
