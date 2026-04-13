"""
加密货币交易模块
提供高级交易功能：策略执行、风险控制、持仓管理等
"""

import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from enum import Enum

from .ccxt_exchange import CCXTExchange

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """订单方向"""
    BUY = 'buy'
    SELL = 'sell'


class OrderType(Enum):
    """订单类型"""
    MARKET = 'market'
    LIMIT = 'limit'
    STOP_LOSS = 'stop_loss'
    TAKE_PROFIT = 'take_profit'


class Position:
    """持仓类"""
    
    def __init__(
        self,
        symbol: str,
        side: str,
        amount: float,
        entry_price: float,
    ):
        """
        初始化持仓
        
        Args:
            symbol: 交易对
            side: 方向 (buy/sell)
            amount: 数量
            entry_price: 入场价格
        """
        self.symbol = symbol
        self.side = side
        self.amount = amount
        self.entry_price = entry_price
        self.current_price = entry_price
        self.unrealized_pnl = 0.0
        self.unrealized_pnl_percent = 0.0
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def update_price(self, price: float):
        """
        更新当前价格
        
        Args:
            price: 当前价格
        """
        self.current_price = price
        self.updated_at = datetime.now()
        
        # 计算未实现盈亏
        if self.side == 'buy':
            self.unrealized_pnl = (price - self.entry_price) * self.amount
            self.unrealized_pnl_percent = ((price - self.entry_price) / self.entry_price) * 100
        else:
            self.unrealized_pnl = (self.entry_price - price) * self.amount
            self.unrealized_pnl_percent = ((self.entry_price - price) / self.entry_price) * 100
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'amount': self.amount,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_percent': self.unrealized_pnl_percent,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class CryptoTrading:
    """
    加密货币交易类
    提供高级交易功能和策略执行
    """
    
    def __init__(
        self,
        exchange: CCXTExchange,
        initial_capital: float = 10000.0,
        max_position_size: float = 0.1,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.05,
    ):
        """
        初始化交易器
        
        Args:
            exchange: 交易所实例
            initial_capital: 初始资金 (USDT)
            max_position_size: 最大仓位比例 (0-1)
            stop_loss_pct: 止损比例 (0-1)
            take_profit_pct: 止盈比例 (0-1)
        """
        self.exchange = exchange
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.max_position_size = max_position_size
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # 持仓管理
        self.positions: Dict[str, Position] = {}
        
        # 订单历史
        self.order_history: List[Dict] = []
        
        # 交易统计
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
        }
        
        logger.info(f"交易器已初始化 - 初始资金：${initial_capital}")
    
    def get_market_data(self, symbol: str) -> Dict:
        """
        获取市场行情数据
        
        Args:
            symbol: 交易对
            
        Returns:
            Dict: 行情数据
        """
        ticker = self.exchange.get_ticker(symbol)
        return ticker
    
    def get_kline_data(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100,
    ) -> List[List]:
        """
        获取 K 线数据
        
        Args:
            symbol: 交易对
            timeframe: K 线周期
            limit: 获取数量
            
        Returns:
            List[List]: K 线数据
        """
        ohlcv = self.exchange.get_ohlcv(symbol, timeframe, limit)
        return ohlcv
    
    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        risk_pct: Optional[float] = None,
    ) -> float:
        """
        计算仓位大小
        
        Args:
            symbol: 交易对
            price: 当前价格
            risk_pct: 风险比例 (可选)
            
        Returns:
            float: 仓位数量
        """
        if risk_pct is None:
            risk_pct = self.max_position_size
        
        # 计算可用资金
        available_capital = self.capital * risk_pct
        
        # 计算仓位大小
        position_size = available_capital / price
        
        return position_size
    
    def open_position(
        self,
        symbol: str,
        side: str,
        amount: Optional[float] = None,
        price: Optional[float] = None,
        order_type: str = 'market',
    ) -> Optional[Position]:
        """
        开仓
        
        Args:
            symbol: 交易对
            side: 方向 (buy/sell)
            amount: 数量 (不传则自动计算)
            price: 价格 (限价单需要)
            order_type: 订单类型 (market/limit)
            
        Returns:
            Optional[Position]: 持仓对象
        """
        # 获取当前价格
        ticker = self.get_market_data(symbol)
        if not ticker or not ticker.get('last'):
            logger.error(f"无法获取 {symbol} 价格")
            return None
        
        current_price = ticker['last']
        
        # 计算仓位大小
        if amount is None:
            amount = self.calculate_position_size(symbol, current_price)
        
        # 检查资金是否充足
        required_capital = amount * current_price
        if required_capital > self.capital:
            logger.error(f"资金不足：需要 ${required_capital}, 可用 ${self.capital}")
            return None
        
        # 创建订单
        if order_type == 'market':
            order = self.exchange.create_market_order(symbol, side, amount)
        else:
            if price is None:
                price = current_price
            order = self.exchange.create_limit_order(symbol, side, amount, price)
        
        # 检查订单是否成功
        if 'error' in order:
            logger.error(f"开仓失败：{order['error']}")
            return None
        
        # 更新资金
        self.capital -= required_capital
        
        # 创建持仓
        position = Position(
            symbol=symbol,
            side=side,
            amount=amount,
            entry_price=current_price,
        )
        
        # 保存持仓
        self.positions[symbol] = position
        
        # 记录订单
        self.order_history.append({
            'type': 'open',
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': current_price,
            'timestamp': datetime.now().isoformat(),
            'order': order,
        })
        
        logger.info(f"开仓成功：{side.upper()} {amount} {symbol} @ ${current_price}")
        return position
    
    def close_position(
        self,
        symbol: str,
        amount: Optional[float] = None,
    ) -> Optional[Dict]:
        """
        平仓
        
        Args:
            symbol: 交易对
            amount: 数量 (不传则全部平仓)
            
        Returns:
            Optional[Dict]: 平仓结果
        """
        # 检查是否有持仓
        if symbol not in self.positions:
            logger.warning(f"没有 {symbol} 的持仓")
            return None
        
        position = self.positions[symbol]
        
        # 确定平仓数量
        if amount is None:
            amount = position.amount
        else:
            amount = min(amount, position.amount)
        
        # 获取当前价格
        ticker = self.get_market_data(symbol)
        if not ticker or not ticker.get('last'):
            logger.error(f"无法获取 {symbol} 价格")
            return None
        
        current_price = ticker['last']
        
        # 平仓方向 (与持仓相反)
        close_side = 'sell' if position.side == 'buy' else 'buy'
        
        # 创建平仓订单
        order = self.exchange.create_market_order(symbol, close_side, amount)
        
        # 检查订单是否成功
        if 'error' in order:
            logger.error(f"平仓失败：{order['error']}")
            return None
        
        # 计算盈亏
        if position.side == 'buy':
            pnl = (current_price - position.entry_price) * amount
        else:
            pnl = (position.entry_price - current_price) * amount
        
        pnl_percent = (pnl / (position.entry_price * amount)) * 100
        
        # 更新资金
        self.capital += amount * current_price
        
        # 更新持仓
        position.amount -= amount
        if position.amount <= 0:
            del self.positions[symbol]
        
        # 更新统计
        self.stats['total_trades'] += 1
        self.stats['total_pnl'] += pnl
        if pnl > 0:
            self.stats['winning_trades'] += 1
        else:
            self.stats['losing_trades'] += 1
        
        # 计算胜率
        if self.stats['total_trades'] > 0:
            self.stats['win_rate'] = (
                self.stats['winning_trades'] / self.stats['total_trades']
            ) * 100
        
        # 记录订单
        result = {
            'symbol': symbol,
            'side': close_side,
            'amount': amount,
            'price': current_price,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'timestamp': datetime.now().isoformat(),
        }
        
        self.order_history.append({
            'type': 'close',
            **result,
            'order': order,
        })
        
        logger.info(
            f"平仓成功：{close_side.upper()} {amount} {symbol} @ ${current_price} | "
            f"盈亏：${pnl:.2f} ({pnl_percent:.2f}%)"
        )
        
        return result
    
    def check_stop_loss(self, symbol: str) -> bool:
        """
        检查止损
        
        Args:
            symbol: 交易对
            
        Returns:
            bool: 是否触发止损
        """
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        ticker = self.get_market_data(symbol)
        
        if not ticker or not ticker.get('last'):
            return False
        
        current_price = ticker['last']
        position.update_price(current_price)
        
        # 检查止损
        if position.unrealized_pnl_percent <= -self.stop_loss_pct * 100:
            logger.warning(
                f"触发止损：{symbol} 亏损 {position.unrealized_pnl_percent:.2f}% "
                f"(阈值：-{self.stop_loss_pct * 100}%)"
            )
            self.close_position(symbol)
            return True
        
        return False
    
    def check_take_profit(self, symbol: str) -> bool:
        """
        检查止盈
        
        Args:
            symbol: 交易对
            
        Returns:
            bool: 是否触发止盈
        """
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        ticker = self.get_market_data(symbol)
        
        if not ticker or not ticker.get('last'):
            return False
        
        current_price = ticker['last']
        position.update_price(current_price)
        
        # 检查止盈
        if position.unrealized_pnl_percent >= self.take_profit_pct * 100:
            logger.info(
                f"触发止盈：{symbol} 盈利 {position.unrealized_pnl_percent:.2f}% "
                f"(阈值：{self.take_profit_pct * 100}%)"
            )
            self.close_position(symbol)
            return True
        
        return False
    
    def update_positions(self):
        """更新所有持仓的当前价格和盈亏"""
        for symbol, position in self.positions.items():
            ticker = self.get_market_data(symbol)
            if ticker and ticker.get('last'):
                position.update_price(ticker['last'])
    
    def get_portfolio_value(self) -> Dict:
        """
        获取投资组合总价值
        
        Returns:
            Dict: 投资组合信息
        """
        # 更新持仓价格
        self.update_positions()
        
        # 计算持仓总价值
        positions_value = 0.0
        for position in self.positions.values():
            positions_value += position.amount * position.current_price
        
        # 总价值
        total_value = self.capital + positions_value
        
        # 总盈亏
        total_pnl = total_value - self.initial_capital
        total_pnl_percent = (total_pnl / self.initial_capital) * 100
        
        return {
            'total_value': total_value,
            'available_capital': self.capital,
            'positions_value': positions_value,
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'initial_capital': self.initial_capital,
        }
    
    def get_positions(self) -> List[Dict]:
        """
        获取所有持仓
        
        Returns:
            List[Dict]: 持仓列表
        """
        self.update_positions()
        return [position.to_dict() for position in self.positions.values()]
    
    def get_stats(self) -> Dict:
        """
        获取交易统计
        
        Returns:
            Dict: 统计信息
        """
        return self.stats.copy()
    
    def get_order_history(self, limit: int = 100) -> List[Dict]:
        """
        获取订单历史
        
        Args:
            limit: 返回数量
            
        Returns:
            List[Dict]: 订单历史
        """
        return self.order_history[-limit:]


# 便捷函数
def create_trader(
    exchange_id: str = 'binance',
    initial_capital: float = 10000.0,
    sandbox: bool = True,
) -> CryptoTrading:
    """
    快速创建交易器
    
    Args:
        exchange_id: 交易所 ID
        initial_capital: 初始资金
        sandbox: 是否沙箱模式
        
    Returns:
        CryptoTrading: 交易器实例
    """
    exchange = CCXTExchange(exchange_id=exchange_id, sandbox=sandbox)
    return CryptoTrading(exchange=exchange, initial_capital=initial_capital)


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("加密货币交易模块测试")
    print("=" * 60)
    
    # 创建交易所实例
    from .ccxt_exchange import CCXTExchange
    exchange = CCXTExchange(exchange_id='binance', sandbox=True)
    
    # 创建交易器
    trader = CryptoTrading(
        exchange=exchange,
        initial_capital=10000.0,
        max_position_size=0.1,
        stop_loss_pct=0.02,
        take_profit_pct=0.05,
    )
    
    # 测试获取行情
    print("\n1. 获取 BTC/USDT 行情:")
    ticker = trader.get_market_data('BTC/USDT')
    if ticker:
        print(f"   最新价：${ticker['last']}")
        print(f"   24h 涨跌：{ticker['change']}%")
    
    # 测试获取 K 线
    print("\n2. 获取 BTC/USDT 1 小时 K 线 (最近 10 条):")
    ohlcv = trader.get_kline_data('BTC/USDT', timeframe='1h', limit=10)
    for k in ohlcv:
        dt = datetime.fromtimestamp(k[0] / 1000)
        print(f"   {dt.strftime('%Y-%m-%d %H:%M')} O:{k[1]:.2f} H:{k[2]:.2f} L:{k[3]:.2f} C:{k[4]:.2f}")
    
    # 测试获取 ETH 行情
    print("\n3. 获取 ETH/USDT 行情:")
    ticker = trader.get_market_data('ETH/USDT')
    if ticker:
        print(f"   最新价：${ticker['last']}")
        print(f"   24h 涨跌：{ticker['change']}%")
    
    # 测试投资组合
    print("\n4. 投资组合状态:")
    portfolio = trader.get_portfolio_value()
    print(f"   总价值：${portfolio['total_value']:.2f}")
    print(f"   可用资金：${portfolio['available_capital']:.2f}")
    print(f"   总盈亏：${portfolio['total_pnl']:.2f} ({portfolio['total_pnl_percent']:.2f}%)")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
