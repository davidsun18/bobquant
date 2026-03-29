#!/usr/bin/env python3
"""
分钟线数据获取器

功能:
- 获取腾讯财经分钟线数据 (5/15/30 分钟)
- 自动缓存，避免频繁请求
- 数据格式标准化
"""

import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd


class MinuteDataFetcher:
    """分钟线数据获取器"""
    
    def __init__(self, cache_duration: int = 60):
        """
        Args:
            cache_duration: 缓存时间 (秒), 默认 60 秒
        """
        self.cache_duration = cache_duration
        self._cache: Dict[str, dict] = {}
        self._cache_time: Dict[str, float] = {}
    
    def get_minute_kline(
        self, 
        code: str, 
        period: int = 5,
        limit: int = 100,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        获取分钟 K 线数据
        
        Args:
            code: 股票代码 (sh.600519)
            period: K 线周期 (5/15/30 分钟)
            limit: 获取数量 (最多 1000)
            use_cache: 是否使用缓存
        
        Returns:
            DataFrame 包含 columns: [time, open, high, low, close, volume]
        """
        # 检查缓存
        cache_key = f"{code}_{period}_{limit}"
        if use_cache and cache_key in self._cache:
            cache_age = time.time() - self._cache_time.get(cache_key, 0)
            if cache_age < self.cache_duration:
                return self._cache[cache_key].copy()
        
        # 获取数据 (使用新浪 API)
        try:
            df = self._fetch_from_sina(code, period, limit)
            
            if df is not None and len(df) > 0:
                # 更新缓存
                self._cache[cache_key] = df
                self._cache_time[cache_key] = time.time()
                return df
            
        except Exception as e:
            print(f"⚠️ 获取分钟线失败 {code}: {e}")
        
        return None
    
    def _fetch_from_sina(
        self, 
        code: str, 
        period: int, 
        limit: int
    ) -> Optional[pd.DataFrame]:
        """从新浪财经获取分钟线"""
        try:
            # 转换股票代码格式
            # sh.600519 -> sh600519
            symbol = code.replace('.', '')
            
            # 新浪财经分钟线 API
            # period: 5=5 分钟，15=15 分钟，30=30 分钟，60=60 分钟
            url = f'http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale={period}&ma=no&datalen={limit}'
            
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if not data or len(data) == 0:
                    return None
                
                # 转换为 DataFrame
                # 新浪格式：[day, open, high, low, close, volume]
                df = pd.DataFrame(
                    data,
                    columns=['day', 'open', 'high', 'low', 'close', 'volume']
                )
                
                # 类型转换
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # 时间转换 (新浪格式：2026-03-29 10:30:00)
                df['day'] = pd.to_datetime(df['day'])
                df = df.set_index('day').sort_index()
                
                # 去除空值
                df = df.dropna()
                
                return df
            
        except Exception as e:
            print(f"  新浪 API 异常：{e}")
        
        return None
    
    def get_batch(
        self, 
        codes: List[str], 
        period: int = 5,
        limit: int = 100,
        use_cache: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取分钟线
        
        Args:
            codes: 股票代码列表
            period: K 线周期
            limit: 获取数量
            use_cache: 是否使用缓存
        
        Returns:
            字典 {code: DataFrame}
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_code = {
                executor.submit(
                    self.get_minute_kline, 
                    code, 
                    period, 
                    limit, 
                    use_cache
                ): code 
                for code in codes
            }
            
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    df = future.result()
                    if df is not None and len(df) > 0:
                        results[code] = df
                except Exception as e:
                    print(f"  批量获取失败 {code}: {e}")
        
        return results
    
    def get_latest_price(self, code: str, period: int = 5) -> Optional[float]:
        """获取最新价格"""
        df = self.get_minute_kline(code, period, limit=1, use_cache=True)
        if df is not None and len(df) > 0:
            return df['close'].iloc[-1]
        return None
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_time.clear()
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        return {
            'cached_items': len(self._cache),
            'cache_keys': list(self._cache.keys())
        }


# ========== 测试 ==========
if __name__ == '__main__':
    print("="*60)
    print("测试分钟线数据获取器")
    print("="*60)
    
    fetcher = MinuteDataFetcher(cache_duration=60)
    
    # 测试单只股票
    print("\n【1】测试单只股票")
    code = 'sh.600519'
    df = fetcher.get_minute_kline(code, period=5, limit=10)
    
    if df is not None:
        print(f"  ✅ {code} 获取成功")
        print(f"  数据量：{len(df)} 条")
        print(f"  最新价格：¥{df['close'].iloc[-1]:.2f}")
        print(f"  时间范围：{df.index[0]} - {df.index[-1]}")
    else:
        print(f"  ❌ {code} 获取失败")
    
    # 测试缓存
    print("\n【2】测试缓存机制")
    start = time.time()
    df1 = fetcher.get_minute_kline(code, period=5, limit=10)
    t1 = time.time() - start
    
    start = time.time()
    df2 = fetcher.get_minute_kline(code, period=5, limit=10, use_cache=True)
    t2 = time.time() - start
    
    print(f"  第 1 次：{t1*1000:.1f}ms")
    print(f"  第 2 次 (缓存): {t2*1000:.1f}ms")
    print(f"  加速比：{t1/t2:.1f}x" if t2 > 0 else "  加速比：N/A")
    
    # 测试批量获取
    print("\n【3】测试批量获取")
    codes = ['sh.600519', 'sz.300750', 'sh.601398']
    results = fetcher.get_batch(codes, period=5, limit=5)
    
    for code, df in results.items():
        print(f"  ✅ {code}: {len(df)}条，最新价¥{df['close'].iloc[-1]:.2f}")
    
    # 缓存统计
    print("\n【4】缓存统计")
    stats = fetcher.get_cache_stats()
    print(f"  缓存项数：{stats['cached_items']}")
    
    print("\n✅ 测试完成")
