# -*- coding: utf-8 -*-
"""
BobQuant Tushare 数据源
支持 A 股实时行情、历史 K 线、财务数据、股票基本信息

Tushare 是专业的财经数据接口库，需要注册获取 token
官网：https://tushare.pro

使用示例:
    from data.provider import get_provider
    
    # 使用 Tushare 数据源 (需要设置 token)
    provider = get_provider('tushare', token='your_token', retry=3)
    
    # 获取实时行情
    quote = provider.get_quote('600519.SH')
    
    # 获取历史数据
    df = provider.get_history('600519.SH', days=60)
    
    # 批量获取
    quotes = provider.get_quotes(['600519.SH', '000001.SZ', '601318.SH'])
"""
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import os

# Support both module import and standalone execution
try:
    from .provider import DataProvider
except ImportError:
    from provider import DataProvider


class TushareProvider(DataProvider):
    """Tushare 数据源 (专业财经数据接口)"""

    def __init__(self, token: str = None, retry=3, timeout=30, delay=1.0):
        """
        初始化 Tushare 数据源
        
        Args:
            token: Tushare API token (可从 https://tushare.pro 获取)
                   如果不传，尝试从环境变量 TUSHARE_TOKEN 读取
            retry: 重试次数
            timeout: 请求超时时间 (秒)
            delay: 请求间隔时间 (秒)
        """
        self.token = token or os.environ.get('TUSHARE_TOKEN', '')
        self.retry = retry
        self.timeout = timeout
        self.delay = delay
        
        if self.token:
            ts.set_token(self.token)
            try:
                self.pro = ts.pro_api()
            except Exception as e:
                print(f"[警告] Tushare API 初始化失败：{e}")
                print("请检查 token 是否正确，或访问 https://tushare.pro 获取有效 token")
                self.pro = None
        else:
            print("[警告] Tushare token 未设置，请通过 token 参数或环境变量 TUSHARE_TOKEN 设置")
            print("请在 https://tushare.pro 注册并获取 token")
            self.pro = None

    def _normalize_code(self, code: str) -> str:
        """
        标准化股票代码格式为 Tushare 格式
        
        Args:
            code: 原始股票代码 (如 sh600519, sz000001, 600519.SH)
            
        Returns:
            标准化代码 (Tushare 格式：600519.SH, 000001.SZ)
        """
        code = code.upper().strip()
        
        # 如果已经是 Tushare 格式，直接返回
        if '.SH' in code or '.SZ' in code:
            return code
        
        # 处理带前缀的代码
        if code.startswith('SH') or code.startswith('SZ'):
            code = code[2:]
        
        # 根据代码规则添加后缀
        if code.startswith('6'):
            return f"{code}.SH"
        elif code.startswith('0') or code.startswith('3'):
            return f"{code}.SZ"
        
        return code

    def _code_to_ts(self, code: str) -> str:
        """
        将 Tushare 格式代码转换为 ts_code 用于 API 调用
        
        Args:
            code: Tushare 格式代码 (600519.SH)
            
        Returns:
            ts_code (600519.SH)
        """
        return self._normalize_code(code)

    def get_quote(self, code: str) -> Optional[Dict]:
        """
        获取 A 股实时行情 (使用 Tushare 实时行情接口)
        
        Args:
            code: 股票代码 (如 600519.SH, 000001.SZ)
            
        Returns:
            dict: {name, current, open, pre_close, high, low, change, volume}
        """
        if not self.pro:
            print("[错误] Tushare 未初始化，请设置有效的 token")
            return None
        
        ts_code = self._normalize_code(code)
        
        for i in range(self.retry):
            try:
                # 使用 Tushare 实时行情接口
                df = ts.realtime_quote(ts_code=ts_code)
                
                if df is None or df.empty:
                    if i < self.retry - 1:
                        time.sleep(self.delay)
                        continue
                    return None
                
                row = df.iloc[0]
                
                current = float(row.get('price', 0))
                pre_close = float(row.get('pre_close', current))
                open_price = float(row.get('open', current))
                high = float(row.get('high', current))
                low = float(row.get('low', current))
                volume = float(row.get('vol', 0))
                
                # 计算涨跌幅
                change = ((current - pre_close) / pre_close * 100) if pre_close > 0 else 0
                
                return {
                    'name': row.get('name', ''),
                    'current': current,
                    'open': open_price,
                    'pre_close': pre_close,
                    'high': high,
                    'low': low,
                    'change': change,
                    'volume': volume,
                }
                
            except Exception as e:
                print(f"[Tushare 错误] {code}: {e}")
                if i < self.retry - 1:
                    time.sleep(self.delay * (i + 1))
        
        return None

    def get_history(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取历史 K 线数据 (使用 Tushare 日线数据接口)
        
        Args:
            code: 股票代码
            days: 获取天数
            
        Returns:
            DataFrame: date, open, high, low, close, volume
        """
        if not self.pro:
            print("[错误] Tushare 未初始化，请设置有效的 token")
            return None
        
        ts_code = self._normalize_code(code)
        
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 使用 Tushare 日线数据接口
            df = ts.daily(
                ts_code=ts_code,
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d')
            )
            
            if df is None or df.empty:
                return None
            
            # 重命名列以匹配接口
            df.rename(columns={
                'trade_date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'vol': 'volume'
            }, inplace=True)
            
            # 选择需要的列
            columns_to_keep = ['date', 'open', 'high', 'low', 'close', 'volume']
            df = df[[col for col in columns_to_keep if col in df.columns]]
            
            # 转换日期列
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
            df.set_index('date', inplace=True)
            
            # 转换类型
            df = df.astype({
                'open': float, 'high': float, 'low': float,
                'close': float, 'volume': float
            })
            
            # 按日期升序排序
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            print(f"[Tushare 历史数据错误] {code}: {e}")
            return None

    def get_financial_data(self, code: str) -> Optional[Dict]:
        """
        获取财务数据
        
        Args:
            code: 股票代码
            
        Returns:
            dict: 财务指标数据 {pe, pb, eps, roe, total_assets, total_liabilities, net_profit}
        """
        ts_code = self._normalize_code(code)
        
        try:
            # 获取公司基本信息
            info_df = ts.stock_company(ts_code=ts_code)
            
            # 获取财务指标
            financial_df = ts.fina_indicator(ts_code=ts_code)
            
            # 获取实时行情获取市盈率、市净率
            quote_df = ts.realtime_quote(ts_code=ts_code)
            
            if quote_df is None or quote_df.empty:
                return None
            
            row = quote_df.iloc[0]
            pe = float(row.get('pe', 0)) if pd.notna(row.get('pe')) else None
            pb = float(row.get('pb', 0)) if pd.notna(row.get('pb')) else None
            
            # 从财务指标获取其他数据
            roe = eps = total_assets = total_liabilities = net_profit = None
            
            if financial_df is not None and not financial_df.empty:
                latest = financial_df.iloc[0]
                roe = float(latest.get('roe', 0)) if pd.notna(latest.get('roe')) else None
                eps = float(latest.get('basic_eps', 0)) if pd.notna(latest.get('basic_eps')) else None
                
                # 获取资产负债表数据
                try:
                    bs_df = ts.balancesheet(ts_code=ts_code)
                    if bs_df is not None and not bs_df.empty:
                        latest_bs = bs_df.iloc[0]
                        total_assets = float(latest_bs.get('total_assets', 0)) if pd.notna(latest_bs.get('total_assets')) else None
                        total_liabilities = float(latest_bs.get('total_liab', 0)) if pd.notna(latest_bs.get('total_liab')) else None
                except:
                    pass
                
                # 获取利润表数据
                try:
                    income_df = ts.income(ts_code=ts_code)
                    if income_df is not None and not income_df.empty:
                        latest_income = income_df.iloc[0]
                        net_profit = float(latest_income.get('net_profit', 0)) if pd.notna(latest_income.get('net_profit')) else None
                except:
                    pass
            
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
            print(f"[Tushare 财务数据错误] {code}: {e}")
            return None

    def get_stock_info(self, code: str) -> Optional[Dict]:
        """
        获取股票基本信息
        
        Args:
            code: 股票代码
            
        Returns:
            dict: {name, area, industry, market, list_date, total_shares, float_shares}
        """
        ts_code = self._normalize_code(code)
        
        try:
            # 获取股票基本信息
            info_df = ts.stock_company(ts_code=ts_code)
            
            if info_df is None or info_df.empty:
                # 尝试从 stock_basic 获取
                basic_df = ts.stock_basic()
                if basic_df is not None and not basic_df.empty:
                    stock_row = basic_df[basic_df['ts_code'] == ts_code]
                    if not stock_row.empty:
                        row = stock_row.iloc[0]
                        return {
                            'name': row.get('name', ''),
                            'area': row.get('area', ''),
                            'industry': row.get('industry', ''),
                            'market': row.get('market', ''),
                            'list_date': row.get('list_date', ''),
                            'total_shares': float(row.get('total_shares', 0)) if pd.notna(row.get('total_shares')) else None,
                            'float_shares': float(row.get('float_shares', 0)) if pd.notna(row.get('float_shares')) else None,
                        }
                return None
            
            row = info_df.iloc[0]
            
            return {
                'name': row.get('name', ''),
                'area': row.get('area', ''),
                'industry': row.get('industry', ''),
                'market': row.get('market', ''),
                'list_date': row.get('list_date', ''),
                'total_shares': float(row.get('total_shares', 0)) if pd.notna(row.get('total_shares')) else None,
                'float_shares': float(row.get('float_shares', 0)) if pd.notna(row.get('float_shares')) else None,
            }
            
        except Exception as e:
            print(f"[Tushare 股票信息错误] {code}: {e}")
            return None

    def get_quotes(self, codes: List[str]) -> Dict[str, dict]:
        """
        批量获取多只股票行情
        
        Args:
            codes: 股票代码列表
            
        Returns:
            dict: {code: quote} 行情字典
        """
        results = {}
        
        try:
            # 转换为 Tushare 格式代码列表
            ts_codes = [self._normalize_code(code) for code in codes]
            ts_codes_str = ','.join(ts_codes)
            
            # 使用 Tushare 批量实时行情接口
            df = ts.realtime_quote(ts_code=ts_codes_str)
            
            if df is None or df.empty:
                return results
            
            for _, row in df.iterrows():
                ts_code = row.get('ts_code', '')
                
                # 找到原始代码
                original_code = None
                for code in codes:
                    if self._normalize_code(code) == ts_code:
                        original_code = code
                        break
                
                if not original_code:
                    continue
                
                current = float(row.get('price', 0))
                pre_close = float(row.get('pre_close', current))
                open_price = float(row.get('open', current))
                high = float(row.get('high', current))
                low = float(row.get('low', current))
                volume = float(row.get('vol', 0))
                
                change = ((current - pre_close) / pre_close * 100) if pre_close > 0 else 0
                
                results[original_code] = {
                    'name': row.get('name', ''),
                    'current': current,
                    'open': open_price,
                    'pre_close': pre_close,
                    'high': high,
                    'low': low,
                    'change': change,
                    'volume': volume,
                }
                
        except Exception as e:
            print(f"[Tushare 批量获取错误]: {e}")
        
        return results


# 测试函数
def test_tushare_provider():
    """测试 Tushare 数据源"""
    print("=" * 60)
    print("Tushare 数据源测试")
    print("=" * 60)
    
    # 从环境变量获取 token 或使用测试 token
    token = os.environ.get('TUSHARE_TOKEN', '')
    provider = TushareProvider(token=token, retry=2, delay=1.0)
    
    # 测试股票列表 (A 股，Tushare 格式)
    test_stocks = [
        ('600519.SH', '贵州茅台'),
        ('000001.SZ', '平安银行'),
        ('601318.SH', '中国平安'),
        ('000002.SZ', '万科 A'),
        ('600036.SH', '招商银行'),
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
    
    print("\n\n4. 测试股票基本信息 (get_stock_info)")
    print("-" * 60)
    for code, name in test_stocks[:2]:
        print(f"\n获取 {name} ({code}) 基本信息...")
        info = provider.get_stock_info(code)
        if info:
            print(f"  ✓ 名称：{info['name']}")
            print(f"  ✓ 地区：{info['area']}")
            print(f"  ✓ 行业：{info['industry']}")
        else:
            print(f"  ✗ 获取失败")
        time.sleep(0.5)
    
    print("\n\n5. 测试财务数据 (get_financial_data)")
    print("-" * 60)
    for code, name in test_stocks[:2]:
        print(f"\n获取 {name} ({code}) 财务数据...")
        financial = provider.get_financial_data(code)
        if financial:
            print(f"  ✓ 市盈率 (PE): {financial['pe']}")
            print(f"  ✓ 市净率 (PB): {financial['pb']}")
            print(f"  ✓ 净资产收益率 (ROE): {financial['roe']}")
        else:
            print(f"  ✗ 获取失败")
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    
    # 输出总结
    print(f"\n【测试结果】")
    print(f"  实时行情：{sum(1 for _, q in quotes.items() if q)}/{len(codes)} 成功")


if __name__ == '__main__':
    test_tushare_provider()
