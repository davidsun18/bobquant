# -*- coding: utf-8 -*-
"""
BobQuant 数据源层
可插拔设计：实现 get_quote / get_history 接口即可接入新数据源
"""
import requests
import time
from abc import ABC, abstractmethod


class DataProvider(ABC):
    """数据源抽象基类"""

    @abstractmethod
    def get_quote(self, code):
        """获取实时行情，返回 dict: {name, current, open, pre_close, high, low, change, volume}"""
        pass

    @abstractmethod
    def get_history(self, code, days=60):
        """获取历史K线，返回 DataFrame: date, open, high, low, close, volume"""
        pass


class TencentProvider(DataProvider):
    """腾讯财经数据源"""

    def __init__(self, retry=2, timeout=3):
        self.retry = retry
        self.timeout = timeout
        self._headers = {
            'Referer': 'http://stockapp.finance.qq.com',
            'User-Agent': 'Mozilla/5.0'
        }

    def get_quote(self, code):
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
            data = []
            while rs.next():
                data.append(rs.get_row_data())
            bs.logout()

            if data:
                df = pd.DataFrame(data, columns=rs.fields)
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                return df
        except Exception:
            pass
        return None


# ==================== 数据源工厂 ====================
_providers = {}


def get_provider(name='tencent', **kwargs):
    """获取数据源实例（带缓存）"""
    if name not in _providers:
        if name == 'tencent':
            _providers[name] = TencentProvider(**kwargs)
        else:
            raise ValueError(f"未知数据源: {name}")
    return _providers[name]
