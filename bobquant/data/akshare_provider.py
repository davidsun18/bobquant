# -*- coding: utf-8 -*-
"""
BobQuant AkShare 数据源
支持 A 股实时行情、历史 K 线、财务数据、资金流向

AkShare 是开源的 Python 财经数据接口库，数据来源于新浪财经、东方财富等

注意：
1. 优先使用新浪财经数据源 (更稳定)
2. 部分功能需要访问东方财富网，可能在某些网络环境下受限
3. 建议设置 delay >= 1 秒避免速率限制

使用示例:
    from data.provider import get_provider
    
    # 使用 AkShare 数据源
    provider = get_provider('akshare', retry=3, delay=1.0)
    
    # 获取实时行情
    quote = provider.get_quote('sh600519')
    
    # 获取历史数据
    df = provider.get_history('sh600519', days=60)
    
    # 批量获取
    quotes = provider.get_quotes(['sh600519', 'sz000001', 'sh601318'])
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import sys

# Support both module import and standalone execution
try:
    from .provider import DataProvider
except ImportError:
    from provider import DataProvider


class AkShareProvider(DataProvider):
    """AkShare 数据源 (专注 A 股市场)"""

    def __init__(self, retry=3, timeout=30, delay=1.0):
        """
        初始化 AkShare 数据源
        
        Args:
            retry: 重试次数
            timeout: 请求超时时间 (秒)
            delay: 请求间隔时间 (秒)
        """
        self.retry = retry
        self.timeout = timeout
        self.delay = delay

    def _normalize_code(self, code: str) -> str:
        """
        标准化股票代码格式
        
        Args:
            code: 原始股票代码 (如 sh600519, sz000001, 600519)
            
        Returns:
            标准化代码 (带市场前缀)
        """
        code = code.lower().strip()
        
        # 如果已经有前缀，直接返回
        if code.startswith('sh') or code.startswith('sz'):
            return code
        
        # 根据代码规则添加前缀
        if code.startswith('6'):
            return f"sh{code}"
        elif code.startswith('0') or code.startswith('3'):
            return f"sz{code}"
        
        return code

    def get_quote(self, code: str) -> Optional[Dict]:
        """
        获取 A 股实时行情 (使用新浪财经数据源)
        
        Args:
            code: 股票代码 (如 sh600519, sz000001)
            
        Returns:
            dict: {name, current, open, pre_close, high, low, change, volume}
        """
        code = self._normalize_code(code)
        
        for i in range(self.retry):
            try:
                # 使用 ak.stock_zh_a_spot (新浪财经数据源，更稳定)
                spot_df = ak.stock_zh_a_spot()
                
                if spot_df.empty:
                    if i < self.retry - 1:
                        time.sleep(self.delay)
                        continue
                    return None
                
                # 查找对应股票
                stock_row = spot_df[spot_df['代码'] == code]
                
                if stock_row.empty:
                    return None
                
                row = stock_row.iloc[0]
                
                current = float(row['最新价']) if pd.notna(row['最新价']) else 0
                pre_close = float(row['昨收']) if pd.notna(row['昨收']) else current
                open_price = float(row['今开']) if pd.notna(row['今开']) else current
                high = float(row['最高']) if pd.notna(row['最高']) else current
                low = float(row['最低']) if pd.notna(row['最低']) else current
                volume = float(row['成交量']) if pd.notna(row['成交量']) else 0
                
                # 计算涨跌幅
                change = ((current - pre_close) / pre_close * 100) if pre_close > 0 else 0
                
                return {
                    'name': row['名称'],
                    'current': current,
                    'open': open_price,
                    'pre_close': pre_close,
                    'high': high,
                    'low': low,
                    'change': change,
                    'volume': volume * 100,  # 手转股
                }
                
            except Exception as e:
                print(f"[AkShare 错误] {code}: {e}")
                if i < self.retry - 1:
                    time.sleep(self.delay * (i + 1))
        
        return None

    def get_history(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取历史 K 线数据 (使用新浪财经数据源)
        
        Args:
            code: 股票代码
            days: 获取天数
            
        Returns:
            DataFrame: date, open, high, low, close, volume
        """
        code = self._normalize_code(code)
        
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 使用 ak.stock_zh_a_daily (新浪财经数据源)
            df = ak.stock_zh_a_daily(
                symbol=code,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="qfq"  # 前复权
            )
            
            if df.empty:
                return None
            
            # 重命名列以匹配接口
            df.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True)
            
            # 选择需要的列
            columns_to_keep = ['date', 'open', 'high', 'low', 'close', 'volume']
            df = df[[col for col in columns_to_keep if col in df.columns]]
            
            # 转换日期列
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 转换类型
            df = df.astype({
                'open': float, 'high': float, 'low': float,
                'close': float, 'volume': float
            })
            
            return df
            
        except Exception as e:
            print(f"[AkShare 历史数据错误] {code}: {e}")
            return None

    def get_financial_data(self, code: str) -> Optional[Dict]:
        """
        获取财务数据
        
        Args:
            code: 股票代码
            
        Returns:
            dict: 财务指标数据 {pe, pb, eps, roe, total_assets, total_liabilities, net_profit}
        """
        code = self._normalize_code(code)
        
        try:
            # 使用 stock_zh_a_spot 获取基本财务指标
            spot_df = ak.stock_zh_a_spot()
            
            if spot_df.empty:
                return None
            
            stock_row = spot_df[spot_df['代码'] == code]
            
            if stock_row.empty:
                return None
            
            row = stock_row.iloc[0]
            
            # 获取市盈率、市净率等
            pe = float(row['市盈率 - 动态']) if pd.notna(row.get('市盈率 - 动态')) else None
            pb = float(row['市净率']) if pd.notna(row.get('市净率')) else None
            
            # 尝试获取更详细的财务数据
            try:
                # 使用 ak.stock_financial_analysis_indicator 获取财务指标
                symbol = code[2:]  # 去掉前缀
                financial_df = ak.stock_financial_analysis_indicator(symbol=symbol)
                
                if not financial_df.empty:
                    latest = financial_df.iloc[0]
                    roe = float(latest.get('净资产收益率 (%)', 0))
                    eps = float(latest.get('基本每股收益 (元)', 0))
                    total_assets = float(latest.get('总资产 (元)', 0))
                    total_liabilities = float(latest.get('总负债 (元)', 0))
                    net_profit = float(latest.get('净利润 (元)', 0))
                else:
                    roe = eps = total_assets = total_liabilities = net_profit = None
            except:
                roe = eps = total_assets = total_liabilities = net_profit = None
            
            return {
                'pe': pe,
                'pb': pb,
                'eps': eps,
                'roe': roe,
                'total_assets': total_assets,
                'total_liabilities': total_liabilities,
                'net_profit': net_profit,
            }
            
        except Exception as e:
            print(f"[AkShare 财务数据错误] {code}: {e}")
            return None

    def get_money_flow(self, code: str, days: int = 10) -> Optional[pd.DataFrame]:
        """
        获取资金流向数据
        
        Args:
            code: 股票代码
            days: 获取天数
            
        Returns:
            DataFrame: date, main_force_in, main_force_out, net_flow
        """
        code = self._normalize_code(code)
        symbol = code[2:]
        
        try:
            # 获取个股资金流向 (东方财富数据源)
            # 注意：此 API 可能需要访问东方财富网
            flow_df = ak.stock_main_fund_flow(symbol=symbol)
            
            if flow_df.empty:
                return None
            
            # 重命名列
            df = flow_df.copy()
            
            # 根据实际列名映射
            column_mapping = {}
            for col in df.columns:
                if '日期' in col or 'date' in col.lower():
                    column_mapping[col] = 'date'
                elif '主力净流入' in col:
                    column_mapping[col] = 'net_flow'
                elif '主力流入' in col and '净' not in col:
                    column_mapping[col] = 'main_force_in'
                elif '主力流出' in col:
                    column_mapping[col] = 'main_force_out'
            
            df.rename(columns=column_mapping, inplace=True)
            
            # 转换日期
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"[AkShare 资金流向错误] {code}: {e}")
            return None

    def get_quotes(self, codes: List[str]) -> Dict[str, dict]:
        """
        批量获取多只股票行情 (一次性获取所有数据，然后筛选)
        
        Args:
            codes: 股票代码列表
            
        Returns:
            dict: {code: quote} 行情字典
        """
        results = {}
        
        try:
            # 一次性获取所有股票的实时行情
            spot_df = ak.stock_zh_a_spot()
            
            if spot_df.empty:
                return results
            
            for code in codes:
                norm_code = self._normalize_code(code)
                
                stock_row = spot_df[spot_df['代码'] == norm_code]
                
                if stock_row.empty:
                    continue
                
                row = stock_row.iloc[0]
                
                current = float(row['最新价']) if pd.notna(row['最新价']) else 0
                pre_close = float(row['昨收']) if pd.notna(row['昨收']) else current
                open_price = float(row['今开']) if pd.notna(row['今开']) else current
                high = float(row['最高']) if pd.notna(row['最高']) else current
                low = float(row['最低']) if pd.notna(row['最低']) else current
                volume = float(row['成交量']) if pd.notna(row['成交量']) else 0
                
                change = ((current - pre_close) / pre_close * 100) if pre_close > 0 else 0
                
                results[code] = {
                    'name': row['名称'],
                    'current': current,
                    'open': open_price,
                    'pre_close': pre_close,
                    'high': high,
                    'low': low,
                    'change': change,
                    'volume': volume * 100,
                }
                
        except Exception as e:
            print(f"[AkShare 批量获取错误]: {e}")
        
        return results


# 测试函数
def test_akshare_provider():
    """测试 AkShare 数据源"""
    print("=" * 60)
    print("AkShare 数据源测试")
    print("=" * 60)
    
    provider = AkShareProvider(retry=2, delay=1.0)
    
    # 测试股票列表 (A 股)
    test_stocks = [
        ('sh600519', '贵州茅台'),
        ('sz000001', '平安银行'),
        ('sh601318', '中国平安'),
        ('sz000002', '万科 A'),
        ('sh600036', '招商银行'),
    ]
    
    print("\n1. 测试实时行情获取 (get_quote)")
    print("-" * 60)
    for code, name in test_stocks:
        print(f"\n获取 {name} ({code})...", end=" ")
        quote = provider.get_quote(code)
        if quote:
            print(f"✓")
            print(f"  名称：{quote['name']}")
            print(f"  当前价：{quote['current']:.2f}")
            print(f"  涨跌幅：{quote['change']:+.2f}%")
        else:
            print(f"✗ 获取失败")
        time.sleep(0.5)
    
    print("\n\n2. 测试历史数据获取 (get_history)")
    print("-" * 60)
    for code, name in test_stocks[:3]:
        print(f"\n获取 {name} ({code}) 历史数据 (10 天)...")
        df = provider.get_history(code, days=10)
        if df is not None and not df.empty:
            print(f"  ✓ 获取成功，共 {len(df)} 条记录")
            print(f"  ✓ 最新收盘价：{df['close'].iloc[-1]:.2f}")
        else:
            print(f"  ✗ 获取失败")
        time.sleep(0.5)
    
    print("\n\n3. 测试批量获取 (get_quotes)")
    print("-" * 60)
    codes = [code for code, _ in test_stocks]
    print(f"批量获取 {len(codes)} 只股票...")
    quotes = provider.get_quotes(codes)
    for code, quote in quotes.items():
        if quote:
            print(f"  ✓ {code}: {quote['current']:.2f} ({quote['change']:+.2f}%)")
        else:
            print(f"  ✗ {code}: 获取失败")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    # 输出总结
    print(f"\n【测试结果】")
    print(f"  实时行情：{sum(1 for _, q in quotes.items() if q)}/{len(codes)} 成功")


if __name__ == '__main__':
    test_akshare_provider()
