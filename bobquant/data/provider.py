# -*- coding: utf-8 -*-
"""
BobQuant 数据源层 v1.1
可插拔设计：实现 get_quote / get_history 接口即可接入新数据源
支持并行刷新，提升数据获取速度
"""
import requests
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional


class DataProvider(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def get_quote(self, code):
        """获取实时行情，返回 dict: {name, current, open, pre_close, high, low, change, volume}"""
        pass

    @abstractmethod
    def get_history(self, code, days=60):
        """获取历史 K 线，返回 DataFrame: date, open, high, low, close, volume"""
        pass
    
    def get_quotes(self, codes: List[str]) -> Dict[str, dict]:
        """批量获取多只股票行情 (默认串行，子类可重写为并行)"""
        results = {}
        for code in codes:
            quote = self.get_quote(code)
            if quote:
                results[code] = quote
        return results


class TencentProvider(DataProvider):
    """腾讯财经数据源 (支持并行刷新)"""

    def __init__(self, retry=2, timeout=3, max_workers=10):
        self.retry = retry
        self.timeout = timeout
        self.max_workers = max_workers  # 并行线程数
        self._headers = {
            'Referer': 'http://stockapp.finance.qq.com',
            'User-Agent': 'Mozilla/5.0'
        }
        # 创建线程池
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='tencent')

    def get_quote(self, code):
        """获取单只股票实时行情"""
        symbol = code.replace('.', '')
        url = f"http://qt.gtimg.cn/q={symbol}"

        for i in range(self.retry):
            try:
                resp = requests.get(url, headers=self._headers, timeout=self.timeout)
                resp.encoding = 'gbk'
                if resp.status_code == 200:
                    data = resp.text.strip()
                    if '=' in data and '"' in data:
                        parts = data.split('=')[1].strip('"').split('~')
                        if len(parts) >= 32:
                            pre_close = float(parts[4])
                            current = float(parts[3])
                            volume = float(parts[6]) if len(parts) > 6 else 0
                            return {
                                'name': parts[1],
                                'current': current,
                                'open': float(parts[5]),
                                'pre_close': pre_close,
                                'high': float(parts[33]) if len(parts) > 33 else current,
                                'low': float(parts[34]) if len(parts) > 34 else current,
                                'change': ((current - pre_close) / pre_close * 100) if pre_close > 0 else 0,
                                'volume': volume,
                            }
            except Exception:
                if i < self.retry - 1:
                    time.sleep(0.5)
        return None

    def get_history(self, code, days=60):
        """通过 baostock 获取历史数据"""
        try:
            import baostock as bs
            import pandas as pd
            from datetime import datetime, timedelta

            lg = bs.login()
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            rs = bs.query_history_k_data_plus(
                code, "date,open,high,low,close,volume",
                start_date=start_date, end_date=end_date, frequency="d"
            )

            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())
            
            bs.logout()
            
            if data_list:
                df = pd.DataFrame(data_list, columns=rs.fields)
                df['date'] = pd.to_datetime(df['date'])
                df = df.astype({
                    'open': float, 'high': float, 'low': float,
                    'close': float, 'volume': float
                })
                df.set_index('date', inplace=True)
                return df
        except Exception as e:
            print(f"[数据错误] {code}: {e}")
        return None
    
    def get_quotes(self, codes: List[str]) -> Dict[str, dict]:
        """
        批量获取多只股票行情 (并行刷新)
        
        Args:
            codes: 股票代码列表
            
        Returns:
            dict: {code: quote} 行情字典
        """
        def fetch_with_retry(code):
            """带重试的单个获取"""
            for i in range(self.retry):
                try:
                    quote = self.get_quote(code)
                    return code, quote
                except Exception as e:
                    if i < self.retry - 1:
                        time.sleep(0.3)
            return code, None
        
        # 并行获取
        results = {}
        futures = {self._executor.submit(fetch_with_retry, code): code for code in codes}
        
        for future in as_completed(futures):
            try:
                code, quote = future.result(timeout=self.timeout * 2)
                if quote:
                    results[code] = quote
            except Exception as e:
                print(f"[并行获取失败] {futures[future]}: {e}")
        
        return results


def get_provider(name='tencent', **kwargs):
    """获取数据源实例（带缓存）"""
    if name not in _providers:
        if name == 'tencent':
            _providers[name] = TencentProvider(**kwargs)
        else:
            raise ValueError(f"未知数据源：{name}")
    return _providers[name]


_providers = {}
