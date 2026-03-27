"""
交易API - 统一交易数据访问
"""

from typing import Optional, Dict, List
from .base_api import BaseAPI


class TradeAPI(BaseAPI):
    """交易数据API"""
    
    def __init__(self, trade_file: str = None):
        super().__init__()
        self.trade_file = trade_file or '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/交易记录.json'
    
    def get(self, limit: int = 50, **kwargs) -> List[Dict]:
        """
        获取交易记录
        
        Args:
            limit: 返回条数
            
        Returns:
            List[{
                'time': str,
                'code': str,
                'name': str,
                'action': str,
                'shares': int,
                'price': float,
                'amount': float,
                'is_buy': bool
            }]
        """
        cache_key = f'trades_{limit}'
        cached = self._get_from_cache(cache_key, max_age=3)
        if cached:
            return cached
        
        data = self._load_json(self.trade_file)
        if not data or 'trades' not in data:
            return []
        
        trades = data['trades']
        
        # 格式化并排序（最新的在前）
        result = []
        for trade in reversed(trades[-limit:]):
            result.append({
                'time': trade.get('time', '--'),
                'code': trade.get('code', '--'),
                'name': trade.get('name', '--'),
                'action': trade.get('action', '--'),
                'shares': trade.get('shares', 0),
                'price': trade.get('price', 0),
                'amount': trade.get('shares', 0) * trade.get('price', 0),
                'is_buy': self._is_buy_action(trade.get('action', ''))
            })
        
        self._set_cache(cache_key, result)
        return result
    
    def _is_buy_action(self, action: str) -> bool:
        """判断是否为买入动作"""
        return '买入' in action or '加仓' in action
    
    def get_by_code(self, code: str, limit: int = 20) -> List[Dict]:
        """获取某只股票的交易记录"""
        all_trades = self.get(limit=1000)
        return [t for t in all_trades if t['code'] == code][:limit]
    
    def get_today_trades(self) -> List[Dict]:
        """获取今日交易"""
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        all_trades = self.get(limit=1000)
        return [t for t in all_trades if today in t['time']]
    
    def get_stats(self) -> Dict:
        """获取交易统计"""
        trades = self.get(limit=1000)
        
        if not trades:
            return {'total': 0, 'buy_count': 0, 'sell_count': 0}
        
        buy_count = sum(1 for t in trades if t['is_buy'])
        sell_count = len(trades) - buy_count
        
        return {
            'total': len(trades),
            'buy_count': buy_count,
            'sell_count': sell_count,
            'today_count': len(self.get_today_trades())
        }
