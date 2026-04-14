#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BobQuant 数据源层 v1.2
可插拔设计：实现 get_quote / get_history 接口即可接入新数据源
支持并行刷新，提升数据获取速度

v1.2 新增：
- 腾讯财经补充数据：成交额、换手率、总市值、流通市值、市盈率、市净率、振幅
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
        self.max_workers = max_workers
        self._headers = {
            'Referer': 'http://stockapp.finance.qq.com',
            'User-Agent': 'Mozilla/5.0'
        }
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
                            
                            result = {
                                'name': parts[1],
                                'current': current,
                                'open': float(parts[5]),
                                'pre_close': pre_close,
                                'high': float(parts[33]) if len(parts) > 33 else current,
                                'low': float(parts[34]) if len(parts) > 34 else current,
                                'change': ((current - pre_close) / pre_close * 100) if pre_close > 0 else 0,
                                'volume': volume,
                            }
                            
                            # 补充数据（添加空值检查）
                            def safe_float(val, default=None):
                                try:
                                    return float(val) if val and val.strip() else default
                                except (ValueError, AttributeError):
                                    return default
                            
                            if len(parts) > 37:
                                val = safe_float(parts[37])
                                if val is not None:
                                    result['turnover'] = val
                            if len(parts) > 38:
                                val = safe_float(parts[38])
                                if val is not None:
                                    result['turnover_rate'] = val
                            if len(parts) > 45:
                                val = safe_float(parts[45])
                                if val is not None:
                                    result['total_mv'] = val
                            if len(parts) > 46:
                                val = safe_float(parts[46])
                                if val is not None:
                                    result['float_mv'] = val
                            if len(parts) > 39:
                                val = safe_float(parts[39])
                                if val is not None:
                                    result['pe'] = val
                            if len(parts) > 40:
                                val = safe_float(parts[40])
                                if val is not None:
                                    result['pb'] = val
                            if len(parts) > 41:
                                val = safe_float(parts[41])
                                if val is not None:
                                    result['amplitude'] = val
                            
                            return result
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
        """批量获取多只股票行情 (并行刷新)"""
        def fetch_with_retry(code):
            for i in range(self.retry):
                try:
                    quote = self.get_quote(code)
                    if quote:
                        return code, quote
                except Exception:
                    if i < self.retry - 1:
                        time.sleep(0.5)
            return code, None
        
        results = {}
        try:
            futures = {self._executor.submit(fetch_with_retry, code): code for code in codes}
            for future in as_completed(futures):
                code, quote = future.result()
                if quote:
                    results[code] = quote
        except RuntimeError as e:
            # 线程池已关闭，降级为串行获取
            logger.warning(f"并行获取失败，降级为串行：{e}")
            for code in codes:
                quote = fetch_with_retry(code)
                if quote[1]:
                    results[quote[0]] = quote[1]
        return results


def get_provider(name='tencent', **kwargs):
    """工厂函数：获取数据源实例"""
    if name == 'tencent':
        return TencentProvider(**kwargs)
    return None


if __name__ == '__main__':
    # 测试
    provider = TencentProvider()
    data = provider.get_quote('sz.002263')
    print('=== 大东南 (sz.002263) ===')
    if data:
        for k, v in data.items():
            print(f'{k}: {v}')
    else:
        print('获取失败')
