"""
CCXT 交易所接口模块
提供统一的交易所 API 封装，支持币安、OKX 等主流交易所
"""

import ccxt
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CCXTExchange:
    """
    CCXT 交易所封装类
    支持多个交易所的统一接口
    """
    
    # 支持的交易所列表
    SUPPORTED_EXCHANGES = {
        'binance': '币安 (Binance)',
        'okx': 'OKX',
        'huobi': '火币 (Huobi)',
        'kucoin': 'KuCoin',
        'bybit': 'Bybit',
        'gateio': 'Gate.io',
    }
    
    # 默认交易所
    DEFAULT_EXCHANGE = 'binance'
    
    # 主流交易对
    MAJOR_PAIRS = [
        'BTC/USDT',
        'ETH/USDT',
        'BNB/USDT',
        'XRP/USDT',
        'SOL/USDT',
        'ADA/USDT',
        'DOGE/USDT',
        'DOT/USDT',
        'MATIC/USDT',
        'LINK/USDT',
    ]
    
    def __init__(
        self,
        exchange_id: str = DEFAULT_EXCHANGE,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
        password: Optional[str] = None,
        sandbox: bool = True,
        rate_limit: bool = True,
        timeout: int = 30000,
    ):
        """
        初始化交易所连接
        
        Args:
            exchange_id: 交易所 ID (binance, okx, huobi 等)
            api_key: API Key
            secret: API Secret
            password: API Password (OKX 需要)
            sandbox: 是否使用测试网络
            rate_limit: 是否启用速率限制
            timeout: 请求超时时间 (毫秒)
        """
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.secret = secret
        self.password = password
        self.sandbox = sandbox
        self.rate_limit = rate_limit
        self.timeout = timeout
        
        # 初始化交易所实例
        self.exchange = self._init_exchange()
        
        logger.info(f"已初始化交易所：{exchange_id} (沙箱模式：{sandbox})")
    
    def _init_exchange(self) -> ccxt.Exchange:
        """
        初始化交易所实例
        
        Returns:
            ccxt.Exchange: 交易所实例
        """
        if self.exchange_id not in ccxt.exchanges:
            raise ValueError(f"不支持的交易所：{self.exchange_id}")
        
        # 获取交易所类
        exchange_class = getattr(ccxt, self.exchange_id)
        
        # 配置参数
        config = {
            'enableRateLimit': self.rate_limit,
            'timeout': self.timeout,
            'options': {
                'defaultType': 'spot',  # 默认现货交易
            }
        }
        
        # 沙箱模式
        if self.sandbox and hasattr(exchange_class, 'sandbox'):
            config['sandbox'] = True
        
        # API 密钥
        if self.api_key and self.secret:
            config['apiKey'] = self.api_key
            config['secret'] = self.secret
            if self.password:
                config['password'] = self.password
        
        # 创建交易所实例
        exchange = exchange_class(config)
        
        # 加载交易市场
        try:
            exchange.load_markets()
            logger.info(f"成功加载 {len(exchange.symbols)} 个交易对")
        except Exception as e:
            logger.warning(f"加载交易市场失败：{e}")
        
        return exchange
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        获取实时行情
        
        Args:
            symbol: 交易对 (如 'BTC/USDT')
            
        Returns:
            Dict: 行情数据
                - last: 最新价
                - bid: 买一价
                - ask: 卖一价
                - high: 24 小时最高
                - low: 24 小时最低
                - volume: 24 小时成交量
                - change: 24 小时涨跌幅
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'last': ticker.get('last'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
                'high': ticker.get('high', 24),
                'low': ticker.get('low', 24),
                'volume': ticker.get('baseVolume'),
                'quote_volume': ticker.get('quoteVolume'),
                'change': ticker.get('percentage'),
                'timestamp': ticker.get('timestamp'),
                'datetime': ticker.get('datetime'),
            }
        except Exception as e:
            logger.error(f"获取行情失败 {symbol}: {e}")
            return {}
    
    def get_tickers(self, symbols: Optional[List[str]] = None) -> Dict[str, Dict]:
        """
        批量获取多个交易对的行情
        
        Args:
            symbols: 交易对列表，None 则获取所有
            
        Returns:
            Dict[str, Dict]: 各交易对的行情数据
        """
        try:
            tickers = self.exchange.fetch_tickers(symbols)
            result = {}
            for symbol, ticker in tickers.items():
                result[symbol] = {
                    'symbol': symbol,
                    'last': ticker.get('last'),
                    'bid': ticker.get('bid'),
                    'ask': ticker.get('ask'),
                    'high': ticker.get('high', 24),
                    'low': ticker.get('low', 24),
                    'volume': ticker.get('baseVolume'),
                    'change': ticker.get('percentage'),
                    'timestamp': ticker.get('timestamp'),
                }
            return result
        except Exception as e:
            logger.error(f"批量获取行情失败：{e}")
            return {}
    
    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100,
        since: Optional[int] = None,
    ) -> List[List]:
        """
        获取 K 线数据
        
        Args:
            symbol: 交易对 (如 'BTC/USDT')
            timeframe: K 线周期
                - '1m': 1 分钟
                - '5m': 5 分钟
                - '15m': 15 分钟
                - '30m': 30 分钟
                - '1h': 1 小时
                - '4h': 4 小时
                - '1d': 1 天
                - '1w': 1 周
                - '1M': 1 月
            limit: 获取数量
            since: 起始时间戳 (毫秒)
            
        Returns:
            List[List]: K 线数据
                每条 K 线：[timestamp, open, high, low, close, volume]
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit, since=since)
            return ohlcv
        except Exception as e:
            logger.error(f"获取 K 线失败 {symbol} {timeframe}: {e}")
            return []
    
    def get_ohlcv_df(self, symbol: str, timeframe: str = '1h', limit: int = 100):
        """
        获取 K 线数据并转换为 DataFrame
        
        Args:
            symbol: 交易对
            timeframe: K 线周期
            limit: 获取数量
            
        Returns:
            pd.DataFrame: K 线数据
                columns: timestamp, open, high, low, close, volume
        """
        try:
            import pandas as pd
            ohlcv = self.get_ohlcv(symbol, timeframe, limit)
            if not ohlcv:
                return pd.DataFrame()
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except ImportError:
            logger.error("需要安装 pandas: pip install pandas")
            return None
        except Exception as e:
            logger.error(f"转换 K 线 DataFrame 失败：{e}")
            return None
    
    def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """
        获取订单簿
        
        Args:
            symbol: 交易对
            limit: 深度 (5, 10, 20, 50, 100)
            
        Returns:
            Dict: 订单簿
                - bids: 买单列表 [[price, amount], ...]
                - asks: 卖单列表 [[price, amount], ...]
        """
        try:
            order_book = self.exchange.fetch_order_book(symbol, limit=limit)
            return {
                'symbol': symbol,
                'bids': order_book.get('bids', [])[:limit],
                'asks': order_book.get('asks', [])[:limit],
                'timestamp': order_book.get('timestamp'),
            }
        except Exception as e:
            logger.error(f"获取订单簿失败 {symbol}: {e}")
            return {'bids': [], 'asks': []}
    
    def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None,
    ) -> Dict:
        """
        创建市价单
        
        Args:
            symbol: 交易对
            side: 方向 ('buy' 或 'sell')
            amount: 数量
            params: 额外参数
            
        Returns:
            Dict: 订单信息
        """
        try:
            order = self.exchange.create_market_order(symbol, side, amount, params=params)
            logger.info(f"市价单已创建：{side} {amount} {symbol}")
            return self._parse_order(order)
        except Exception as e:
            logger.error(f"创建市价单失败：{e}")
            return {'error': str(e)}
    
    def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: Optional[Dict] = None,
    ) -> Dict:
        """
        创建限价单
        
        Args:
            symbol: 交易对
            side: 方向 ('buy' 或 'sell')
            amount: 数量
            price: 价格
            params: 额外参数
            
        Returns:
            Dict: 订单信息
        """
        try:
            order = self.exchange.create_limit_order(symbol, side, amount, price, params=params)
            logger.info(f"限价单已创建：{side} {amount} {symbol} @ {price}")
            return self._parse_order(order)
        except Exception as e:
            logger.error(f"创建限价单失败：{e}")
            return {'error': str(e)}
    
    def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """
        取消订单
        
        Args:
            order_id: 订单 ID
            symbol: 交易对
            
        Returns:
            Dict: 取消结果
        """
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            logger.info(f"订单已取消：{order_id}")
            return {'success': True, 'order_id': order_id}
        except Exception as e:
            logger.error(f"取消订单失败：{e}")
            return {'error': str(e)}
    
    def get_order(self, order_id: str, symbol: str) -> Dict:
        """
        查询订单状态
        
        Args:
            order_id: 订单 ID
            symbol: 交易对
            
        Returns:
            Dict: 订单信息
        """
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return self._parse_order(order)
        except Exception as e:
            logger.error(f"查询订单失败：{e}")
            return {'error': str(e)}
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        获取未成交订单
        
        Args:
            symbol: 交易对，None 则获取所有
            
        Returns:
            List[Dict]: 订单列表
        """
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return [self._parse_order(order) for order in orders]
        except Exception as e:
            logger.error(f"获取未成交订单失败：{e}")
            return []
    
    def get_balance(self) -> Dict:
        """
        获取账户余额
        
        Returns:
            Dict: 余额信息
                - free: 可用余额
                - used: 冻结余额
                - total: 总余额
        """
        try:
            balance = self.exchange.fetch_balance()
            return {
                'free': balance.get('free', {}),
                'used': balance.get('used', {}),
                'total': balance.get('total', {}),
            }
        except Exception as e:
            logger.error(f"获取余额失败：{e}")
            return {}
    
    def _parse_order(self, order: Dict) -> Dict:
        """
        解析订单数据
        
        Args:
            order: 原始订单数据
            
        Returns:
            Dict: 解析后的订单信息
        """
        return {
            'id': order.get('id'),
            'symbol': order.get('symbol'),
            'type': order.get('type'),
            'side': order.get('side'),
            'price': order.get('price'),
            'amount': order.get('amount'),
            'filled': order.get('filled'),
            'remaining': order.get('remaining'),
            'status': order.get('status'),
            'cost': order.get('cost'),
            'fee': order.get('fee'),
            'timestamp': order.get('timestamp'),
            'datetime': order.get('datetime'),
        }
    
    def get_supported_timeframes(self) -> List[str]:
        """
        获取支持的 K 线周期
        
        Returns:
            List[str]: 周期列表
        """
        return list(self.exchange.timeframes.keys()) if self.exchange.timeframes else []
    
    def get_markets(self) -> Dict:
        """
        获取所有交易市场信息
        
        Returns:
            Dict: 市场信息
        """
        return self.exchange.markets
    
    def close(self):
        """关闭交易所连接"""
        if self.exchange:
            self.exchange.close()
            logger.info("交易所连接已关闭")


# 便捷函数
def create_exchange(
    exchange_id: str = 'binance',
    sandbox: bool = True,
) -> CCXTExchange:
    """
    快速创建交易所实例
    
    Args:
        exchange_id: 交易所 ID
        sandbox: 是否沙箱模式
        
    Returns:
        CCXTExchange: 交易所实例
    """
    return CCXTExchange(exchange_id=exchange_id, sandbox=sandbox)


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("CCXT 交易所接口测试")
    print("=" * 60)
    
    # 创建交易所实例 (沙箱模式)
    exchange = CCXTExchange(exchange_id='binance', sandbox=True)
    
    # 测试获取 BTC/USDT 行情
    print("\n1. 获取 BTC/USDT 实时行情:")
    ticker = exchange.get_ticker('BTC/USDT')
    if ticker:
        print(f"   最新价：${ticker['last']}")
        print(f"   24h 涨跌：{ticker['change']}%")
        print(f"   24h 最高：${ticker['high']}")
        print(f"   24h 最低：${ticker['low']}")
        print(f"   24h 成交量：{ticker['volume']} BTC")
    
    # 测试获取 K 线数据
    print("\n2. 获取 BTC/USDT 1 小时 K 线 (最近 5 条):")
    ohlcv = exchange.get_ohlcv('BTC/USDT', timeframe='1h', limit=5)
    for k in ohlcv:
        dt = datetime.fromtimestamp(k[0] / 1000)
        print(f"   {dt.strftime('%Y-%m-%d %H:%M')} O:{k[1]} H:{k[2]} L:{k[3]} C:{k[4]} V:{k[5]}")
    
    # 测试获取 ETH/USDT 行情
    print("\n3. 获取 ETH/USDT 实时行情:")
    ticker = exchange.get_ticker('ETH/USDT')
    if ticker:
        print(f"   最新价：${ticker['last']}")
        print(f"   24h 涨跌：{ticker['change']}%")
    
    # 获取支持的交易所
    print("\n4. 支持的交易所列表:")
    for ex_id, ex_name in CCXTExchange.SUPPORTED_EXCHANGES.items():
        print(f"   - {ex_id}: {ex_name}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
