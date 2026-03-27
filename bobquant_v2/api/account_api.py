"""
账户API - 统一账户数据访问
"""

from typing import Optional, Dict, List
from .base_api import BaseAPI


class AccountAPI(BaseAPI):
    """账户数据API"""
    
    def __init__(self, account_file: str = None):
        super().__init__()
        self.account_file = account_file or '/home/openclaw/.openclaw/workspace/quant_strategies/sim_trading/account_ideal.json'
    
    def get(self, **kwargs) -> Optional[Dict]:
        """
        获取账户数据
        
        Returns:
            {
                'cash': float,
                'market_value': float,
                'total_assets': float,
                'position_profit': float,
                'today_profit': float,
                'positions': List[Position]
            }
        """
        cache_key = 'account'
        cached = self._get_from_cache(cache_key, max_age=3)  # 3秒缓存
        if cached:
            return cached
        
        data = self._load_json(self.account_file)
        if not data:
            return None
        
        # 标准化输出
        result = {
            'cash': data.get('cash', 0),
            'market_value': self._calc_market_value(data.get('positions', {})),
            'total_assets': data.get('cash', 0) + self._calc_market_value(data.get('positions', {})),
            'position_profit': data.get('position_profit', 0),
            'today_profit': data.get('profit_today', 0),
            'positions': self._format_positions(data.get('positions', {})),
            'timestamp': data.get('last_update', '')
        }
        
        self._set_cache(cache_key, result)
        return result
    
    def _calc_market_value(self, positions: Dict) -> float:
        """计算持仓市值"""
        total = 0
        for code, pos in positions.items():
            shares = pos.get('shares', 0)
            price = pos.get('current_price', pos.get('avg_price', 0))
            total += shares * price
        return total
    
    def _format_positions(self, positions: Dict) -> List[Dict]:
        """格式化持仓数据"""
        result = []
        for code, pos in positions.items():
            shares = pos.get('shares', 0)
            avg_price = pos.get('avg_price', 0)
            current_price = pos.get('current_price', avg_price)
            market_value = shares * current_price
            cost = shares * avg_price
            profit = market_value - cost
            profit_pct = (profit / cost) if cost > 0 else 0
            
            result.append({
                'code': code,
                'name': pos.get('name', code),
                'shares': shares,
                'avg_price': avg_price,
                'current_price': current_price,
                'market_value': market_value,
                'profit': profit,
                'profit_pct': profit_pct,
                'today_bought': pos.get('today_bought', 0)
            })
        
        # 按盈亏排序
        result.sort(key=lambda x: x['profit'], reverse=True)
        return result
    
    def get_position(self, code: str) -> Optional[Dict]:
        """获取单个持仓"""
        account = self.get()
        if not account:
            return None
        
        for pos in account.get('positions', []):
            if pos['code'] == code:
                return pos
        return None
