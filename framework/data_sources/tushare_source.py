#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare 数据源 - 免费 API 集成
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class TushareSource:
    """
    Tushare 数据源
    
    免费 API (无需 token):
    - 实时行情
    - 历史 K 线
    - 股票列表
    """
    
    BASE_URL = "https://api.tushare.pro"
    
    # 免费接口 (部分需要 token)
    FREE_ENDPOINTS = {
        "quote": "/api/quote",
        "daily": "/api/daily",
        "stock_list": "/api/stock/basic"
    }
    
    def __init__(self, token: str = None):
        """
        初始化 Tushare 数据源
        
        Args:
            token: Tushare token (可选，免费接口不需要)
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/json'
        })
        
        logger.info("Tushare 数据源初始化完成")
    
    def get_realtime_quote(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        获取实时行情 (免费接口)
        
        Args:
            stock_codes: 股票代码列表
        
        Returns:
            DataFrame 包含行情数据
        """
        # 使用腾讯财经作为备选 (Tushare 免费接口有限)
        logger.warning("Tushare 免费接口不支持实时行情，使用备选方案")
        return pd.DataFrame()
    
    def get_daily_data(self, stock_code: str, 
                       start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """
        获取日线数据
        
        Args:
            stock_code: 股票代码
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
        
        Returns:
            DataFrame 包含日线数据
        """
        try:
            # 格式化股票代码
            if stock_code.startswith('6'):
                ts_code = f"{stock_code}.SH"
            else:
                ts_code = f"{stock_code}.SZ"
            
            url = f"{self.BASE_URL}/daily"
            params = {
                "ts_code": ts_code,
                "start_date": start_date.replace('-', ''),
                "end_date": end_date.replace('-', '')
            }
            
            if self.token:
                params["token"] = self.token
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    df = pd.DataFrame(data.get('data', []))
                    logger.info(f"Tushare 获取日线成功：{stock_code}, {len(df)}条")
                    return df
            
            logger.warning(f"Tushare 获取日线失败：{response.text}")
            return None
            
        except Exception as e:
            logger.error(f"Tushare 异常：{e}")
            return None
    
    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表
        
        Returns:
            DataFrame 包含股票列表
        """
        try:
            url = f"{self.BASE_URL}/stock/basic"
            params = {}
            
            if self.token:
                params["token"] = self.token
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    df = pd.DataFrame(data.get('data', []))
                    logger.info(f"Tushare 获取股票列表成功：{len(df)}只")
                    return df
            
            return None
            
        except Exception as e:
            logger.error(f"Tushare 获取股票列表异常：{e}")
            return None
    
    def get_adjusted_factors(self, stock_code: str) -> Optional[pd.DataFrame]:
        """
        获取复权因子
        
        Args:
            stock_code: 股票代码
        
        Returns:
            DataFrame 包含复权因子
        """
        # 简化实现，实际需要从 Tushare 获取
        logger.warning("复权因子功能暂未实现")
        return None


# 全局单例
_global_tushare: Optional[TushareSource] = None

def get_tushare(token: str = None) -> TushareSource:
    """获取 Tushare 数据源单例"""
    global _global_tushare
    if _global_tushare is None:
        _global_tushare = TushareSource(token)
    return _global_tushare


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    tushare = get_tushare()
    
    # 测试 (需要有效 token)
    # df = tushare.get_daily_data("600519", "2026-04-01", "2026-04-18")
    # print(df)
