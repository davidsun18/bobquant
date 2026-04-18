#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Bot - 数据采集脚本
========================
负责从腾讯财经采集实时行情数据，从 BaoStock 采集历史数据

功能：
- 实时行情数据采集（腾讯财经）
- 历史数据采集（BaoStock）
- 数据清洗与验证
- 数据存储与归档

作者：Data Bot
版本：1.0.0
创建日期：2026-04-18
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

import requests
import pandas as pd
import baostock as bs

# ============== 配置 ==============

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = BASE_DIR / "agents" / "data-bot" / "config.json"
LOG_DIR = BASE_DIR / "logs"
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
DATA_BACKUP_DIR = BASE_DIR / "backup" / "data"

# 确保目录存在
for dir_path in [LOG_DIR, DATA_RAW_DIR, DATA_PROCESSED_DIR, DATA_BACKUP_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / f"data_bot_{datetime.now().strftime('%Y-%m-%d')}.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DataBot")

# 腾讯财经 API 配置
TENCENT_BASE_URL = "https://qt.gtimg.cn"
TENCENT_TIMEOUT = 1.0  # 1 秒 (网络波动时需要更长时间)
TENCENT_RETRY_COUNT = 3

# A 股股票代码前缀
SH_PREFIX = "sh"  # 上海证券交易所
SZ_PREFIX = "sz"  # 深圳证券交易所


# ============== 腾讯财经数据采集团 ==============

class TencentDataCollector:
    """腾讯财经实时行情数据采集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://stockapp.finance.qq.com/'
        })
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取单只股票实时行情
        
        参数:
            stock_code: 股票代码 (如 '600519' 或 '000001')
        
        返回:
            包含行情数据的字典，失败返回 None
        """
        # 自动添加市场前缀
        if not stock_code.startswith((SH_PREFIX, SZ_PREFIX)):
            if stock_code.startswith('6'):
                stock_code = f"{SH_PREFIX}{stock_code}"
            else:
                stock_code = f"{SZ_PREFIX}{stock_code}"
        
        url = f"{TENCENT_BASE_URL}/q={stock_code}"
        
        for attempt in range(TENCENT_RETRY_COUNT):
            try:
                response = self.session.get(url, timeout=TENCENT_TIMEOUT)
                response.raise_for_status()
                
                # 腾讯返回格式：v_sh600519="51~贵州茅台~600519~338.50~..."
                content = response.content.decode('gbk')
                if content.startswith('v_') and '~' in content:
                    return self._parse_tencent_response(content, stock_code)
                else:
                    logger.warning(f"腾讯返回数据格式异常：{content[:100]}")
                    
            except requests.Timeout:
                logger.warning(f"请求超时 (尝试 {attempt + 1}/{TENCENT_RETRY_COUNT}): {stock_code}")
            except requests.RequestException as e:
                logger.error(f"请求失败 (尝试 {attempt + 1}/{TENCENT_RETRY_COUNT}): {stock_code} - {e}")
            
            if attempt < TENCENT_RETRY_COUNT - 1:
                time.sleep(0.05)  # 50ms 后重试
        
        return None
    
    def get_batch_quotes(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        批量获取股票行情
        
        参数:
            stock_codes: 股票代码列表
        
        返回:
            DataFrame 包含所有股票的行情数据
        """
        # 添加市场前缀
        formatted_codes = []
        for code in stock_codes:
            if not code.startswith((SH_PREFIX, SZ_PREFIX)):
                if code.startswith('6'):
                    formatted_codes.append(f"{SH_PREFIX}{code}")
                else:
                    formatted_codes.append(f"{SZ_PREFIX}{code}")
            else:
                formatted_codes.append(code)
        
        # 腾讯财经不支持真正的批量查询，需要逐个获取
        # 但可以快速连续请求
        all_quotes = []
        
        for code in formatted_codes:
            url = f"{TENCENT_BASE_URL}/q={code}"
            
            try:
                response = self.session.get(url, timeout=TENCENT_TIMEOUT * 3)
                response.raise_for_status()
                
                content = response.content.decode('gbk')
                quote = self._parse_tencent_response(content, code)
                if quote:
                    all_quotes.append(quote)
                
            except Exception as e:
                logger.warning(f"获取 {code} 失败：{e}")
            
            # 避免请求过快，每 10 只股票延迟 50ms
            if len(all_quotes) % 10 == 0:
                time.sleep(0.05)
        
        return pd.DataFrame(all_quotes)
    
    def _safe_int(self, value: str, default: int = 0) -> int:
        """安全转换为整数"""
        try:
            return int(float(value)) if value else default
        except (ValueError, TypeError):
            return default
    
    def _safe_float(self, value: str, default: float = 0.0) -> float:
        """安全转换为浮点数"""
        try:
            return float(value) if value else default
        except (ValueError, TypeError):
            return default
    
    def _parse_tencent_response(self, content: str, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        解析腾讯财经返回的数据
        
        腾讯返回格式示例:
        v_sh600519="51~贵州茅台~600519~338.50~340.00~338.00~339.00~337.00~338.50~338.49~33900~34000~..."
        
        字段说明 (按~分隔):
        0:  51 (未知)
        1:  股票名称
        2:  股票代码
        3:  当前价格
        4:  昨收
        5:  今开
        6:  最高
        7:  最低
        8:  买一价
        9:  买一量
        10: 卖一价
        11: 卖一量
        ...
        """
        try:
            # 提取引号内的数据
            start = content.find('"') + 1
            end = content.rfind('"')
            if start <= 0 or end <= start:
                return None
            
            data_str = content[start:end]
            fields = data_str.split('~')
            
            if len(fields) < 8:
                return None
            
            current_price = self._safe_float(fields[3])
            prev_close = self._safe_float(fields[4])
            open_price = self._safe_float(fields[5])
            high = self._safe_float(fields[6])
            low = self._safe_float(fields[7])
            
            # 计算涨跌幅
            change = current_price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0
            
            return {
                'stock_code': fields[2] or stock_code,
                'stock_name': fields[1],
                'current_price': current_price,
                'prev_close': prev_close,
                'open_price': open_price,
                'high_price': high,
                'low_price': low,
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'buy1_price': self._safe_float(fields[8]),
                'buy1_volume': self._safe_int(fields[9]),
                'sell1_price': self._safe_float(fields[10]) if len(fields) > 10 else 0,
                'sell1_volume': self._safe_int(fields[11]) if len(fields) > 11 else 0,
                'volume': self._safe_int(fields[12]) if len(fields) > 12 else 0,  # 成交量 (手)
                'turnover': self._safe_float(fields[13]) if len(fields) > 13 else 0,  # 成交额 (元)
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'tencent'
            }
            
        except Exception as e:
            logger.error(f"解析腾讯数据失败：{e}, content: {content[:100]}")
            return None


# ============== BaoStock 历史数据采集团 ==============

class BaoStockCollector:
    """BaoStock 历史数据采集器"""
    
    def __init__(self):
        self.login_done = False
    
    def login(self):
        """登录 BaoStock"""
        if not self.login_done:
            lg = bs.login()
            if lg.error_code == '0':
                self.login_done = True
                logger.info("BaoStock 登录成功")
            else:
                logger.error(f"BaoStock 登录失败：{lg.error_msg}")
    
    def logout(self):
        """登出 BaoStock"""
        if self.login_done:
            bs.logout()
            self.login_done = False
            logger.info("BaoStock 已登出")
    
    def get_history_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        frequency: str = "d"
    ) -> Optional[pd.DataFrame]:
        """
        获取历史行情数据
        
        参数:
            stock_code: 股票代码 (如 'sh.600519' 或 'sz.000001')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            frequency: 频率 d=日，w=周，m=月
        
        返回:
            DataFrame 包含历史行情
        """
        self.login()
        
        # 格式化股票代码
        if '.' not in stock_code:
            if stock_code.startswith('6'):
                stock_code = f"sh.{stock_code}"
            else:
                stock_code = f"sz.{stock_code}"
        
        try:
            # 查询历史行情 (日线数据不需要 time 字段)
            rs = bs.query_history_k_data_plus(
                code=stock_code,
                fields="date,open,high,low,close,volume,amount,adjustflag",
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                adjustflag="3"  # 不复权
            )
            
            if rs.error_code != '0':
                logger.error(f"BaoStock 查询失败：{rs.error_msg}")
                return None
            
            data_list = []
            while (rs.error_code == '0') and rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                logger.warning(f"未获取到数据：{stock_code} ({start_date} ~ {end_date}) - 可能是非交易日")
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            df['stock_code'] = stock_code
            df['source'] = 'baostock'
            
            # 类型转换
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"BaoStock 获取成功：{stock_code}, {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"BaoStock 获取异常：{e}")
            return None
    
    def get_stock_list(self, date: str = None) -> Optional[pd.DataFrame]:
        """
        获取 A 股股票列表
        
        参数:
            date: 查询日期 (YYYY-MM-DD)，默认今天
        
        返回:
            DataFrame 包含股票列表
        """
        self.login()
        
        try:
            rs = bs.query_all_stock(day=date)
            if rs.error_code != '0':
                logger.error(f"获取股票列表失败：{rs.error_msg}")
                return None
            
            data_list = []
            while rs.next():
                data_list.append(rs.get_row_data())
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            logger.info(f"获取股票列表成功：{len(df)} 只股票")
            return df
            
        except Exception as e:
            logger.error(f"获取股票列表异常：{e}")
            return None


# ============== 数据验证与存储 ==============

class DataValidator:
    """数据质量验证器"""
    
    @staticmethod
    def validate_quote_data(df: pd.DataFrame) -> Dict[str, Any]:
        """
        验证行情数据质量
        
        返回:
            验证结果字典
        """
        if df.empty:
            return {'valid': False, 'reason': '数据为空'}
        
        issues = []
        
        # 检查必填字段
        required_cols = ['stock_code', 'current_price', 'timestamp']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            issues.append(f"缺少字段：{missing_cols}")
        
        # 检查价格有效性
        if 'current_price' in df.columns:
            invalid_prices = df[df['current_price'] <= 0]
            if len(invalid_prices) > 0:
                issues.append(f"{len(invalid_prices)} 条记录价格无效")
        
        # 检查涨跌幅合理性
        if 'change_pct' in df.columns:
            extreme_change = df[abs(df['change_pct']) > 20]  # A 股涨跌停限制
            if len(extreme_change) > 0:
                issues.append(f"{len(extreme_change)} 条记录涨跌幅异常")
        
        # 检查时间戳
        if 'timestamp' in df.columns:
            null_timestamps = df['timestamp'].isna().sum()
            if null_timestamps > 0:
                issues.append(f"{null_timestamps} 条记录缺少时间戳")
        
        return {
            'valid': len(issues) == 0,
            'record_count': len(df),
            'issues': issues
        }


class DataStorage:
    """数据存储管理器"""
    
    def __init__(self):
        self.raw_dir = DATA_RAW_DIR
        self.processed_dir = DATA_PROCESSED_DIR
        self.backup_dir = DATA_BACKUP_DIR
    
    def save_raw_data(self, df: pd.DataFrame, data_type: str = "quote") -> Optional[str]:
        """
        保存原始数据
        
        参数:
            df: 数据 DataFrame
            data_type: 数据类型 (quote/history)
        
        返回:
            保存的文件路径
        """
        if df.empty:
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{data_type}_{timestamp}.parquet"
        filepath = self.raw_dir / filename
        
        try:
            df.to_parquet(filepath, index=False)
            logger.info(f"原始数据已保存：{filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"保存原始数据失败：{e}")
            return None
    
    def save_processed_data(
        self,
        df: pd.DataFrame,
        data_type: str = "quote",
        date: str = None
    ) -> Optional[str]:
        """
        保存处理后的数据
        
        参数:
            df: 数据 DataFrame
            data_type: 数据类型
            date: 数据日期 (用于分区存储)
        
        返回:
            保存的文件路径
        """
        if df.empty:
            return None
        
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # 按日期分区存储
        date_dir = self.processed_dir / data_type / date
        date_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"{data_type}_{date}_{timestamp}.parquet"
        filepath = date_dir / filename
        
        try:
            df.to_parquet(filepath, index=False)
            logger.info(f"处理数据已保存：{filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"保存处理数据失败：{e}")
            return None
    
    def backup_file(self, filepath: str) -> Optional[str]:
        """
        备份文件
        
        参数:
            filepath: 原文件路径
        
        返回:
            备份文件路径
        """
        try:
            src = Path(filepath)
            if not src.exists():
                return None
            
            date_dir = self.backup_dir / datetime.now().strftime('%Y-%m-%d')
            date_dir.mkdir(parents=True, exist_ok=True)
            
            dst = date_dir / src.name
            import shutil
            shutil.copy2(src, dst)
            logger.info(f"文件已备份：{dst}")
            return str(dst)
        except Exception as e:
            logger.error(f"备份文件失败：{e}")
            return None


# ============== 主程序 ==============

def load_stock_list() -> List[str]:
    """
    加载股票列表
    
    实际使用时可从配置文件或数据库加载
    这里使用示例股票列表
    """
    # 示例：沪深 300 成分股 (部分)
    sample_stocks = [
        '600519',  # 贵州茅台
        '000858',  # 五粮液
        '601318',  # 中国平安
        '600036',  # 招商银行
        '000333',  # 美的集团
        '601888',  # 中国中免
        '002415',  # 海康威视
        '600276',  # 恒瑞医药
        '000651',  # 格力电器
        '601398',  # 工商银行
        # 可添加更多股票...
    ]
    return sample_stocks


def collect_realtime_data():
    """采集实时行情数据"""
    logger.info("=" * 50)
    logger.info("开始采集实时行情数据")
    logger.info("=" * 50)
    
    collector = TencentDataCollector()
    storage = DataStorage()
    validator = DataValidator()
    
    # 加载股票列表
    stock_list = load_stock_list()
    logger.info(f"待采集股票数量：{len(stock_list)}")
    
    # 批量采集
    df = collector.get_batch_quotes(stock_list)
    
    if not df.empty:
        # 数据验证
        validation_result = validator.validate_quote_data(df)
        logger.info(f"数据验证结果：{validation_result}")
        
        if validation_result['valid']:
            # 保存数据
            raw_path = storage.save_raw_data(df, "quote")
            processed_path = storage.save_processed_data(df, "quote")
            
            logger.info(f"采集完成：{len(df)} 只股票")
            logger.info(f"原始数据：{raw_path}")
            logger.info(f"处理数据：{processed_path}")
        else:
            logger.warning(f"数据验证失败，但仍保存：{validation_result['issues']}")
            storage.save_raw_data(df, "quote_error")
    else:
        logger.error("未采集到任何数据")
    
    return df


def collect_history_data(
    start_date: str = None,
    end_date: str = None
):
    """采集历史数据"""
    logger.info("=" * 50)
    logger.info("开始采集历史数据")
    logger.info("=" * 50)
    
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    collector = BaoStockCollector()
    storage = DataStorage()
    
    stock_list = load_stock_list()
    logger.info(f"待采集股票数量：{len(stock_list)}")
    logger.info(f"日期范围：{start_date} ~ {end_date}")
    
    all_dfs = []
    for i, stock in enumerate(stock_list, 1):
        logger.info(f"采集进度：{i}/{len(stock_list)} - {stock}")
        df = collector.get_history_data(stock, start_date, end_date)
        if df is not None and not df.empty:
            all_dfs.append(df)
        
        # 避免请求过快
        if i % 10 == 0:
            time.sleep(0.5)
    
    collector.logout()
    
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        storage.save_raw_data(combined_df, "history")
        storage.save_processed_data(combined_df, "history", end_date)
        logger.info(f"历史数据采集完成：{len(combined_df)} 条记录")
    else:
        logger.warning("未采集到历史数据")


def main():
    """主函数"""
    logger.info("Data Bot 数据采集启动")
    logger.info(f"工作目录：{BASE_DIR}")
    
    try:
        # 采集实时数据
        collect_realtime_data()
        
        # 采集历史数据 (可选，首次运行或定期执行)
        # collect_history_data()
        
        logger.info("=" * 50)
        logger.info("Data Bot 数据采集完成")
        logger.info("=" * 50)
        
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"采集异常：{e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
