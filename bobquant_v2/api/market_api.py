"""
行情API - 统一市场数据访问
"""

from typing import Optional, Dict, List
from .base_api import BaseAPI
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


class MarketAPI(BaseAPI):
    """市场行情API"""
    
    def __init__(self, max_workers: int = 10):
        super().__init__()
        self.max_workers = max_workers
        self._headers = {
            'Referer': 'http://stockapp.finance.qq.com',
            'User-Agent': 'Mozilla/5.0'
        }
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def get(self, code: str, **kwargs) -> Optional[Dict]:
        """
        获取单只股票行情
        
        Args:
            code: 股票代码 (如: sh.600519)
            
        Returns:
            {
                'code': str,
                'name': str,
                'current': float,
                'open': float,
                'pre_close': float,
                'high': float,
                'low': float,
                'change': float,  # 涨跌幅%
                'volume': float
            }
        """
        cache_key = f'quote_{code}'
        cached = self._get_from_cache(cache_key, max_age=3)  # 3秒缓存
        if cached:
            return cached
        
        quote = self._fetch_quote(code)
        if quote:
            self._set_cache(cache_key, quote)
        return quote
    
    def get_batch(self, codes: List[str]) -> Dict[str, Dict]:
        """
        批量获取行情
        
        Args:
            codes: 股票代码列表
            
        Returns:
            {code: quote}
        """
        # 先检查缓存
        result = {}
        need_fetch = []
        
        for code in codes:
            cache_key = f'quote_{code}'
            cached = self._get_from_cache(cache_key, max_age=3)
            if cached:
                result[code] = cached
            else:
                need_fetch.append(code)
        
        # 并行获取未缓存的
        if need_fetch:
            fetched = self._fetch_batch(need_fetch)
            result.update(fetched)
        
        return result
    
    def _fetch_quote(self, code: str) -> Optional[Dict]:
        """从腾讯财经获取单只股票行情"""
        try:
            symbol = code.replace('.', '')
            url = f"http://qt.gtimg.cn/q={symbol}"
            
            resp = requests.get(url, headers=self._headers, timeout=3)
            resp.encoding = 'gbk'
            
            if resp.status_code == 200:
                data = resp.text.strip()
                if '=' in data and '"' in data:
                    parts = data.split('=')[1].strip('"').split('~')
                    if len(parts) >= 32:
                        pre_close = float(parts[4])
                        current = float(parts[3])
                        
                        return {
                            'code': code,
                            'name': parts[1],
                            'current': current,
                            'open': float(parts[5]),
                            'pre_close': pre_close,
                            'high': float(parts[33]) if len(parts) > 33 else current,
                            'low': float(parts[34]) if len(parts) > 34 else current,
                            'change': ((current - pre_close) / pre_close * 100) if pre_close > 0 else 0,
                            'volume': float(parts[6]) if len(parts) > 6 else 0
                        }
        except Exception as e:
            print(f"[Error] 获取行情失败 {code}: {e}")
        
        return None
    
    def _fetch_batch(self, codes: List[str]) -> Dict[str, Dict]:
        """并行批量获取行情"""
        result = {}
        futures = {self._executor.submit(self._fetch_quote, code): code for code in codes}
        
        for future in as_completed(futures):
            code = futures[future]
            try:
                quote = future.result(timeout=5)
                if quote:
                    result[code] = quote
                    self._set_cache(f'quote_{code}', quote)
            except Exception as e:
                print(f"[Error] 批量获取失败 {code}: {e}")
        
        return result
    
    def is_trading_time(self) -> bool:
        """判断是否为交易时间"""
        from datetime import datetime
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        time = hour * 100 + minute
        
        # 早盘: 09:15 - 11:30, 午盘: 13:00 - 15:00
        return (915 <= time <= 1130) or (1300 <= time <= 1500)
